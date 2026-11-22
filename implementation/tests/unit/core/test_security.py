"""Perfiles protegidos: contraseña, regla de los tres intentos y avisos de intrusión."""
from datetime import UTC, datetime, timedelta

import pytest

from jarvis_assistant.core.database import Database
from jarvis_assistant.core.repositories import ReminderRepository
from jarvis_assistant.core.security import (
    MAX_ATTEMPTS,
    AccessOrigin,
    AttemptOutcome,
    ProfileVault,
    hash_password,
    password_problem,
    verify_password,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LOGIN = AccessOrigin.LOGIN


class Moment:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def db():
    database = Database(":memory:")
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def clock():
    return Moment()


@pytest.fixture
def vault(db, clock):
    vault = ProfileVault(db, clock)
    vault.set_password_hash("secreto", hash_password("clave-1234"))
    return vault


def fail(vault, times, origin=LOGIN):
    return [vault.attempt("secreto", "mala", origin) for _ in range(times)]


# --- Hash ------------------------------------------------------------------------------------


def test_el_hash_no_contiene_la_contrasena_y_lleva_sal_nueva():
    first, second = hash_password("clave-1234"), hash_password("clave-1234")
    assert "clave-1234" not in first
    assert first.startswith("scrypt$")
    assert first != second
    assert verify_password("clave-1234", first)
    assert verify_password("clave-1234", second)


def test_una_contrasena_distinta_no_pasa():
    assert not verify_password("clave-1235", hash_password("clave-1234"))


@pytest.mark.parametrize("stored", ["", "texto", "md5$1$2$3$a$b", "scrypt$x$8$1$AA==$AA=="])
def test_un_hash_con_formato_desconocido_no_deja_pasar_a_nadie(stored):
    assert not verify_password("", stored)


def test_la_contrasena_tiene_al_menos_cuatro_caracteres():
    assert password_problem("abc") != ""
    assert password_problem("abcd") == ""


# --- Protección ------------------------------------------------------------------------------


def test_solo_el_perfil_con_contrasena_esta_protegido(vault):
    assert vault.is_protected("secreto")
    assert not vault.is_protected("casa")
    assert vault.protected_ids() == {"secreto"}


def test_un_perfil_sin_contrasena_siempre_concede(vault):
    assert vault.attempt("casa", "", LOGIN) is AttemptOutcome.GRANTED


def test_la_contrasena_correcta_concede(vault):
    assert vault.attempt("secreto", "clave-1234", LOGIN) is AttemptOutcome.GRANTED


def test_quitar_la_contrasena_es_borrado_logico_y_volver_a_ponerla_la_reactiva(vault, db):
    vault.clear_password("secreto")
    assert not vault.is_protected("secreto")
    assert db.conn.execute("SELECT is_deleted FROM profile_credentials").fetchone()[0] == 1
    vault.set_password_hash("secreto", hash_password("otra-clave"))
    assert vault.attempt("secreto", "otra-clave", LOGIN) is AttemptOutcome.GRANTED
    assert vault.attempt("secreto", "clave-1234", LOGIN) is AttemptOutcome.DENIED


# --- Tres intentos ---------------------------------------------------------------------------


def test_el_tercer_fallo_seguido_registra_un_aviso(vault, clock):
    assert fail(vault, MAX_ATTEMPTS) == [
        AttemptOutcome.DENIED, AttemptOutcome.DENIED, AttemptOutcome.LOCKED_OUT,
    ]  # fmt: skip
    (alert,) = vault.pending_alerts("secreto")
    assert (alert.at, alert.attempts, alert.origin) == (NOW, 3, LOGIN)


def test_los_fallos_se_acumulan_entre_intentos_separados(vault):
    """Cancelar la caja tras dos fallos no reinicia la cuenta: el siguiente es el tercero."""
    fail(vault, 2)
    assert vault.attempt("secreto", "mala", LOGIN) is AttemptOutcome.LOCKED_OUT


def test_los_fallos_de_la_configuracion_suman_a_los_del_inicio(vault):
    fail(vault, 2)
    assert vault.attempt("secreto", "mala", AccessOrigin.SETTINGS) is AttemptOutcome.LOCKED_OUT
    (alert,) = vault.pending_alerts("secreto")
    assert alert.origin is AccessOrigin.SETTINGS


def test_un_acierto_pone_la_cuenta_a_cero(vault):
    fail(vault, 2)
    vault.attempt("secreto", "clave-1234", LOGIN)
    assert fail(vault, 2) == [AttemptOutcome.DENIED, AttemptOutcome.DENIED]
    assert vault.pending_alerts("secreto") == []


def test_cada_tanda_de_tres_fallos_es_un_aviso(vault, clock):
    fail(vault, 3)
    clock.now = NOW + timedelta(hours=1)
    fail(vault, 3)
    alerts = vault.pending_alerts("secreto")
    assert [alert.at for alert in alerts] == [NOW, NOW + timedelta(hours=1)]


def test_confirmar_los_avisos_los_quita_de_pendientes(vault):
    fail(vault, 3)
    (alert,) = vault.pending_alerts("secreto")
    vault.acknowledge([alert.id])
    assert vault.pending_alerts("secreto") == []


def test_los_avisos_son_del_perfil_atacado(vault):
    vault.set_password_hash("otro", hash_password("otra-clave"))
    fail(vault, 3)
    assert vault.pending_alerts("otro") == []


# --- Retirar un perfil -----------------------------------------------------------------------


def test_retirar_un_perfil_elimina_sus_recordatorios_su_contrasena_y_sus_avisos(vault, db):
    mine = ReminderRepository(db, "secreto")
    theirs = ReminderRepository(db, "casa")
    mine.create("Mío", [NOW + timedelta(days=1)], None, NOW)
    theirs.create("Suyo", [NOW + timedelta(days=1)], None, NOW)
    fail(vault, 3)
    vault.retire("secreto")
    assert mine.listable() == []
    assert [r.content for r in theirs.listable()] == ["Suyo"]
    assert not vault.is_protected("secreto")
    assert vault.pending_alerts("secreto") == []


# --- Migración -------------------------------------------------------------------------------


def test_la_migracion_descarta_los_recordatorios_que_no_eran_de_ningun_perfil(tmp_path):
    from jarvis_assistant.core import database as database_module

    directory = tmp_path / "migrations"
    directory.mkdir()
    initial = database_module.MIGRATIONS_DIR / "0001_initial.sql"
    (directory / initial.name).write_text(initial.read_text(encoding="utf-8"), encoding="utf-8")
    path = tmp_path / "jarvis.db"
    old = Database(path, migrations_dir=directory)
    old.migrate()
    old.conn.execute(
        "INSERT INTO reminders (content, created_at)"
        " VALUES ('Antiguo', '2026-01-01T00:00:00+00:00')"
    )
    old.conn.commit()
    old.close()

    db = Database(path)
    db.migrate()
    row = db.conn.execute("SELECT status, profile_id FROM reminders").fetchone()
    assert (row["status"], row["profile_id"]) == ("eliminado", "")
    db.close()
