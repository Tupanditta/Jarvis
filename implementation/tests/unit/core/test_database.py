"""SQLite: conexión, migraciones, fechas, copia de seguridad y base dañada (T-0.7)."""
import logging
import re
import shutil
import sqlite3
import threading
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from jarvis_assistant.core import database
from jarvis_assistant.core.database import Database, from_db, to_db

NOW = datetime(2026, 11, 14, 17, 32, 5, tzinfo=UTC)
SRC = Path(database.__file__).resolve().parents[2]
INSERT_ACTIVITY = (
    "INSERT INTO session_activities (session_id, module_name, task_description, status,"
    " executed_at) VALUES (?, 'm', 'd', ?, 'x')"
)


@pytest.fixture
def db():
    database_ = Database(":memory:")
    database_.migrate()
    yield database_
    database_.close()


def tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {row[0] for row in rows if not row[0].startswith("sqlite_")}


def count_sessions(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT count(*) FROM sessions").fetchone()[0]


def insert_session(conn, name="sesión", opened_at=NOW):
    with conn:
        cursor = conn.execute(
            "INSERT INTO sessions (name, opened_at) VALUES (?, ?)", (name, to_db(opened_at))
        )
    return cursor.lastrowid


# --- Fechas (RES-35) -------------------------------------------------------------------------


def test_to_db_escribe_iso_8601_en_utc_con_desplazamiento():
    assert to_db(NOW) == "2026-11-14T17:32:05+00:00"


def test_to_db_normaliza_a_utc():
    madrid = timezone(timedelta(hours=1))
    assert to_db(datetime(2026, 11, 14, 18, 32, 5, tzinfo=madrid)) == "2026-11-14T17:32:05+00:00"


def test_to_db_rechaza_una_fecha_sin_zona_horaria():
    with pytest.raises(ValueError):
        to_db(datetime(2026, 11, 14, 17, 32, 5))


def test_from_db_devuelve_la_misma_fecha_en_utc():
    restored = from_db(to_db(NOW))
    assert restored == NOW
    assert restored.utcoffset() == timedelta(0)


def test_from_db_rechaza_un_texto_sin_zona_horaria():
    with pytest.raises(ValueError):
        from_db("2026-11-14T17:32:05")


def test_el_orden_alfabetico_coincide_con_el_cronologico():
    madrid = timezone(timedelta(hours=1))
    moments = [
        datetime(2026, 11, 14, 18, 0, tzinfo=madrid),  # 17:00 UTC
        datetime(2026, 11, 14, 17, 30, tzinfo=UTC),
        datetime(2026, 11, 14, 17, 30, 0, 500000, tzinfo=UTC),
        datetime(2026, 11, 14, 17, 30, 1, tzinfo=UTC),
    ]
    texts = [to_db(moment) for moment in moments]
    assert texts == sorted(texts)


# --- Conexión y esquema ----------------------------------------------------------------------


def test_migrate_crea_el_esquema_y_fija_la_version(db):
    assert tables(db.conn) == {"sessions", "session_activities", "reminders", "reminder_triggers"}
    assert db.schema_version == 1


def test_migrate_es_idempotente(db):
    insert_session(db.conn)
    db.migrate()
    assert count_sessions(db.conn) == 1


def test_pragmas_de_cada_conexion(tmp_path):
    db = Database(tmp_path / "jarvis.db")
    try:
        values = {
            name: db.conn.execute(f"PRAGMA {name}").fetchone()[0]
            for name in ("journal_mode", "foreign_keys", "synchronous", "busy_timeout")
        }
    finally:
        db.close()
    # synchronous = 1 es NORMAL.
    assert values == {
        "journal_mode": "wal", "foreign_keys": 1, "synchronous": 1, "busy_timeout": 2000,
    }  # fmt: skip


def test_crea_la_carpeta_de_datos_si_no_existe(tmp_path):
    db = Database(tmp_path / "local" / "data" / "jarvis.db")
    db.close()
    assert (tmp_path / "local" / "data" / "jarvis.db").is_file()


def test_los_datos_persisten_entre_ejecuciones(tmp_path):
    first = Database(tmp_path / "jarvis.db")
    first.migrate()
    insert_session(first.conn, "persistente")
    first.close()

    second = Database(tmp_path / "jarvis.db")
    second.migrate()
    assert second.conn.execute("SELECT name FROM sessions").fetchone()[0] == "persistente"
    second.close()


def test_las_filas_se_leen_por_nombre_de_columna(db):
    insert_session(db.conn, "con nombre")
    assert db.conn.execute("SELECT * FROM sessions").fetchone()["name"] == "con nombre"


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO sessions (name, opened_at) VALUES ('  ', 'x')",
        "INSERT INTO sessions (name, opened_at, is_important) VALUES ('a', 'x', 2)",
        "INSERT INTO sessions (name, opened_at, closed_at) VALUES ('a', 'x', 'y')",
        "INSERT INTO sessions (name, opened_at, closed_at, close_reason) VALUES ('a','x','y','z')",
        "INSERT INTO session_activities (session_id, module_name, task_description, status,"
        " executed_at) VALUES (999, 'm', 'd', 'pendiente', 'x')",
        "INSERT INTO reminders (content, created_at, status) VALUES ('a', 'x', 'otro')",
        "INSERT INTO reminder_triggers (reminder_id, trigger_at) VALUES (999, 'x')",
    ],
)
def test_el_esquema_rechaza_datos_incoherentes(db, sql):
    with pytest.raises(sqlite3.IntegrityError), db.conn:
        db.conn.execute(sql)


def test_el_estado_de_una_actividad_solo_admite_los_tres_valores(db):
    session_id = insert_session(db.conn)
    with db.conn:
        for status in ("pendiente", "error", "completado"):
            db.conn.execute(INSERT_ACTIVITY, (session_id, status))
    with pytest.raises(sqlite3.IntegrityError), db.conn:
        db.conn.execute(INSERT_ACTIVITY, (session_id, "en curso"))


def test_las_claves_ajenas_impiden_un_borrado_fisico_accidental(db):
    session_id = insert_session(db.conn)
    with db.conn:
        db.conn.execute(INSERT_ACTIVITY, (session_id, "pendiente"))
    with pytest.raises(sqlite3.IntegrityError), db.conn:
        db.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def test_la_conexion_solo_se_usa_en_el_hilo_que_la_creo(db):
    errors = []

    def use():
        try:
            db.conn.execute("SELECT 1")
        except sqlite3.ProgrammingError as error:
            errors.append(error)

    thread = threading.Thread(target=use)
    thread.start()
    thread.join()
    assert len(errors) == 1


def test_close_es_idempotente(db):
    db.close()
    db.close()


# --- Transacciones ---------------------------------------------------------------------------


def test_una_transaccion_que_falla_no_deja_nada(db):
    with pytest.raises(RuntimeError), db.transaction():
        db.conn.execute("INSERT INTO sessions (name, opened_at) VALUES ('a', 'x')")
        raise RuntimeError("fallo")
    assert count_sessions(db.conn) == 0


def test_las_transacciones_anidadas_son_una_sola(db):
    with pytest.raises(RuntimeError), db.transaction():
        with db.transaction():
            db.conn.execute("INSERT INTO sessions (name, opened_at) VALUES ('a', 'x')")
        assert db.conn.in_transaction  # la interior no confirma
        raise RuntimeError("fallo en la exterior")
    assert count_sessions(db.conn) == 0


def test_una_transaccion_correcta_se_confirma(db):
    with db.transaction(), db.transaction():
        db.conn.execute("INSERT INTO sessions (name, opened_at) VALUES ('a', 'x')")
    assert not db.conn.in_transaction
    assert count_sessions(db.conn) == 1


# --- Migraciones -----------------------------------------------------------------------------


def migrations_with(tmp_path: Path, extra: dict[str, str]) -> Path:
    directory = tmp_path / "migrations"
    shutil.copytree(database.MIGRATIONS_DIR, directory)
    for name, sql in extra.items():
        (directory / name).write_text(sql, encoding="utf-8")
    return directory


def test_las_migraciones_se_aplican_en_orden_segun_la_version(tmp_path):
    directory = migrations_with(
        tmp_path,
        {
            "0003_tercera.sql": "ALTER TABLE extra ADD COLUMN b TEXT;",
            "0002_segunda.sql": "CREATE TABLE extra (a TEXT);",
        },
    )
    db = Database(":memory:", migrations_dir=directory)
    db.migrate()
    assert db.schema_version == 3
    assert [row[1] for row in db.conn.execute("PRAGMA table_info(extra)")] == ["a", "b"]


def test_una_migracion_que_falla_se_deshace_entera_y_no_sube_la_version(tmp_path):
    broken = "CREATE TABLE extra (a TEXT);\nINSERT INTO no_existe VALUES (1);"
    directory = migrations_with(tmp_path, {"0002_rota.sql": broken})
    db = Database(":memory:", migrations_dir=directory)
    with pytest.raises(sqlite3.Error):
        db.migrate()
    assert db.schema_version == 1
    assert "extra" not in tables(db.conn)
    assert not db.conn.in_transaction


def test_una_migracion_ya_aplicada_no_se_repite(tmp_path):
    db = Database(tmp_path / "jarvis.db")
    db.migrate()
    db.close()
    directory = migrations_with(tmp_path, {"0002_segunda.sql": "CREATE TABLE extra (a TEXT);"})
    db = Database(tmp_path / "jarvis.db", migrations_dir=directory)
    db.migrate()  # 0001 fallaría si se repitiera: las tablas ya existen
    assert db.schema_version == 2
    db.close()


@pytest.mark.parametrize("name", ["0003_salto.sql", "segunda.sql", "0002-guion.sql"])
def test_una_migracion_mal_numerada_es_un_error(tmp_path, name):
    directory = migrations_with(tmp_path, {name: "SELECT 1;"})
    db = Database(":memory:", migrations_dir=directory)
    with pytest.raises(ValueError):
        db.migrate()


def test_una_base_mas_nueva_que_el_codigo_no_se_toca(tmp_path):
    db = Database(tmp_path / "jarvis.db")
    db.migrate()
    db.conn.execute("PRAGMA user_version = 7")
    db.close()
    db = Database(tmp_path / "jarvis.db")
    with pytest.raises(RuntimeError, match="más reciente"):
        db.migrate()
    db.close()


# --- Copia de seguridad ----------------------------------------------------------------------


def test_antes_de_cambiar_el_esquema_se_copia_la_base(tmp_path):
    path = tmp_path / "jarvis.db"
    db = Database(path)
    db.migrate()
    insert_session(db.conn, "anterior")
    db.close()

    directory = migrations_with(tmp_path, {"0002_segunda.sql": "CREATE TABLE extra (a TEXT);"})
    db = Database(path, migrations_dir=directory)
    db.migrate()
    db.close()

    backup = sqlite3.connect(tmp_path / "jarvis.db.bak")
    try:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 1
        assert backup.execute("SELECT name FROM sessions").fetchone()[0] == "anterior"
        assert "extra" not in tables(backup)
    finally:
        backup.close()


def test_sin_cambio_de_esquema_no_hay_copia(tmp_path):
    path = tmp_path / "jarvis.db"
    for _ in range(2):
        db = Database(path)
        db.migrate()
        db.close()
    assert not (tmp_path / "jarvis.db.bak").exists()


# --- Base dañada -----------------------------------------------------------------------------


def test_una_base_danada_se_aparta_y_se_crea_una_nueva(tmp_path, caplog):
    path = tmp_path / "jarvis.db"
    path.write_bytes(b"esto no es una base de datos SQLite" * 100)
    with caplog.at_level(logging.ERROR, logger="jarvis_assistant.core.database"):
        db = Database(path, now=lambda: NOW)
    db.migrate()
    insert_session(db.conn)
    db.close()

    corrupt = tmp_path / "jarvis.db.corrupt-20261114-173205"
    assert corrupt.read_bytes().startswith(b"esto no es")
    assert any("dañada" in record.getMessage() for record in caplog.records)


def test_una_base_sana_no_se_aparta(tmp_path):
    path = tmp_path / "jarvis.db"
    Database(path).close()
    Database(path).close()
    assert [p.name for p in tmp_path.iterdir() if "corrupt" in p.name] == []


# --- Borrado lógico (RES-34) -----------------------------------------------------------------


def test_el_codigo_no_contiene_ninguna_sentencia_delete():
    pattern = re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE)
    files = [*SRC.rglob("*.py"), *SRC.rglob("*.sql")]
    assert len(files) > 5
    offenders = [
        str(path.relative_to(SRC)) for path in files if pattern.search(path.read_text("utf-8"))
    ]
    assert offenders == []
