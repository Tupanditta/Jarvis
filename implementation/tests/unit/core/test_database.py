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


# Las migraciones de verdad: las de prueba van detrás.
LATEST = len(list(database.MIGRATIONS_DIR.glob("*.sql")))


def migration(offset: int, name: str) -> str:
    return f"{LATEST + offset:04d}_{name}.sql"


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
    assert tables(db.conn) == {
        "sessions", "session_activities", "reminders", "reminder_triggers",
        "profile_credentials", "intrusion_alerts", "profile_permissions", "admin_keys",
        "credential_escrow",
    }  # fmt: skip
    assert db.schema_version == LATEST


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
            migration(2, "tercera"): "ALTER TABLE extra ADD COLUMN b TEXT;",
            migration(1, "segunda"): "CREATE TABLE extra (a TEXT);",
        },
    )
    db = Database(":memory:", migrations_dir=directory)
    db.migrate()
    assert db.schema_version == LATEST + 2
    assert [row[1] for row in db.conn.execute("PRAGMA table_info(extra)")] == ["a", "b"]


def test_una_migracion_que_falla_se_deshace_entera_y_no_sube_la_version(tmp_path):
    broken = "CREATE TABLE extra (a TEXT);\nINSERT INTO no_existe VALUES (1);"
    directory = migrations_with(tmp_path, {migration(1, "rota"): broken})
    db = Database(":memory:", migrations_dir=directory)
    with pytest.raises(sqlite3.Error):
        db.migrate()
    assert db.schema_version == LATEST
    assert "extra" not in tables(db.conn)
    assert not db.conn.in_transaction


def test_una_migracion_ya_aplicada_no_se_repite(tmp_path):
    db = Database(tmp_path / "jarvis.db")
    db.migrate()
    db.close()
    directory = migrations_with(tmp_path, {migration(1, "segunda"): "CREATE TABLE extra (a TEXT);"})
    db = Database(tmp_path / "jarvis.db", migrations_dir=directory)
    db.migrate()  # 0001 fallaría si se repitiera: las tablas ya existen
    assert db.schema_version == LATEST + 1
    db.close()


@pytest.mark.parametrize(
    "name", [migration(2, "salto"), "segunda.sql", migration(1, "guion").replace("_", "-", 1)]
)
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

    directory = migrations_with(tmp_path, {migration(1, "segunda"): "CREATE TABLE extra (a TEXT);"})
    db = Database(path, migrations_dir=directory)
    db.migrate()
    db.close()

    backup = sqlite3.connect(tmp_path / "jarvis.db.bak")
    try:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == LATEST
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


def test_la_migracion_0004_borra_las_eliminadas_y_numera_las_sesiones_de_1_a_n(tmp_path):
    previous = tmp_path / "previas"
    previous.mkdir()
    for path in sorted(database.MIGRATIONS_DIR.glob("*.sql"))[:3]:
        shutil.copy(path, previous / path.name)
    db = Database(tmp_path / "jarvis.db", migrations_dir=previous)
    db.migrate()
    conn = db.conn
    for session_id, deleted in ((159, 0), (160, 1), (162, 0), (170, 0)):
        conn.execute(
            "INSERT INTO sessions (id, name, opened_at, is_deleted) VALUES (?, ?, 'x', ?)",
            (session_id, f"s{session_id}", deleted),
        )
    conn.execute(
        "UPDATE sessions SET displaced_by = 170, pending_purge_on_close = 1 WHERE id = 162"
    )
    for session_id in (159, 160, 170):
        conn.execute(INSERT_ACTIVITY, (session_id, "completado"))
    # Una subtarea de la eliminada: su madre (ON DELETE RESTRICT) se borra con ella.
    conn.execute(
        "INSERT INTO session_activities (session_id, parent_id, module_name, task_description,"
        " status, executed_at) SELECT 160, id, 'm', 'hija', 'completado', 'x'"
        " FROM session_activities WHERE session_id = 160"
    )
    conn.commit()
    db.close()

    db = Database(tmp_path / "jarvis.db")
    db.migrate()
    rows = db.conn.execute("SELECT id, name, displaced_by FROM sessions ORDER BY id").fetchall()
    assert [tuple(row) for row in rows] == [(1, "s159", None), (2, "s162", 3), (3, "s170", None)]
    activities = db.conn.execute("SELECT session_id FROM session_activities ORDER BY id")
    assert [row[0] for row in activities] == [1, 3]
    sequence = db.conn.execute("SELECT seq FROM sqlite_sequence WHERE name = 'sessions'")
    assert sequence.fetchone()[0] == 3
    assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    db.close()


# Única excepción: eliminar una sesión la borra del todo, con sus actividades, y renumera las
# demás (ids 1..N).
PHYSICAL_DELETE_TABLES = {"sessions", "session_activities"}


def test_el_codigo_solo_borra_fisicamente_sesiones_y_actividades():
    pattern = re.compile(r"\bDELETE\s+FROM\s+(\w+)", re.IGNORECASE)
    files = [*SRC.rglob("*.py"), *SRC.rglob("*.sql")]
    assert len(files) > 5
    offenders = [
        f"{path.relative_to(SRC)}: {table}"
        for path in files
        for table in pattern.findall(path.read_text("utf-8"))
        if table not in PHYSICAL_DELETE_TABLES
    ]
    assert offenders == []
