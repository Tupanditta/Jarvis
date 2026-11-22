"""Custodia de contraseñas para el Acedor: claves X25519, sellos y su ciclo de vida."""
from datetime import UTC, datetime

import pytest

from jarvis_assistant.config import ADMIN_PROFILE_ID
from jarvis_assistant.core.custody import (
    AdminKey,
    CredentialCustody,
    decrypt_private,
    generate_keys,
    rewrap_private,
    seal,
)
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.security import (
    AccessOrigin,
    AttemptOutcome,
    ProfileVault,
    hash_password,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
ADMIN_PASSWORD = "maestra-1234"


@pytest.fixture
def db():
    database = Database(":memory:")
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def vault(db):
    return ProfileVault(db, lambda: NOW)


def activate(vault: ProfileVault, password: str = ADMIN_PASSWORD) -> None:
    vault.install_admin(hash_password(password), *generate_keys(password))


# --- Primitivas ------------------------------------------------------------------------------


def test_la_clave_privada_solo_se_abre_con_la_contrasena_del_acedor():
    _public, private = generate_keys(ADMIN_PASSWORD)
    assert ADMIN_PASSWORD not in private
    assert decrypt_private(private, ADMIN_PASSWORD) is not None
    assert decrypt_private(private, "otra") is None
    assert decrypt_private("basura", ADMIN_PASSWORD) is None


def test_un_sello_solo_lo_abre_la_clave_privada_del_acedor(db):
    custody = CredentialCustody(db, lambda: NOW)
    public, private = generate_keys(ADMIN_PASSWORD)
    sealed = seal(public, "clave-del-perfil")
    assert "clave-del-perfil" not in sealed
    custody.install(public, private)
    key = custody.unlock(ADMIN_PASSWORD)
    assert key is not None
    assert key.open(sealed) == "clave-del-perfil"
    assert "clave" not in repr(key)
    _other_public, other_private = generate_keys("otra-maestra")
    custody.install(_other_public, other_private)
    other = custody.unlock("otra-maestra")
    assert other is not None and other.open(sealed) is None


def test_cambiar_la_contrasena_del_acedor_conserva_la_clave():
    public, private = generate_keys(ADMIN_PASSWORD)
    sealed = seal(public, "secreto")
    assert rewrap_private(private, "mala", "nueva-clave") is None
    rewrapped = rewrap_private(private, ADMIN_PASSWORD, "nueva-clave")
    assert rewrapped is not None
    assert decrypt_private(rewrapped, ADMIN_PASSWORD) is None
    key = decrypt_private(rewrapped, "nueva-clave")
    assert key is not None
    assert AdminKey(key).open(sealed) == "secreto"  # lo ya sellado se sigue abriendo


# --- El Acedor en la base de datos -----------------------------------------------------------


def test_el_acedor_esta_activo_con_contrasena_y_claves(vault):
    assert not vault.admin_active()
    activate(vault)
    assert vault.admin_active()
    assert vault.is_protected(ADMIN_PROFILE_ID)
    assert vault.attempt(ADMIN_PROFILE_ID, ADMIN_PASSWORD, AccessOrigin.LOGIN) is (
        AttemptOutcome.GRANTED
    )
    assert vault.open_admin(ADMIN_PASSWORD) is not None
    assert vault.open_admin("mala") is None


def test_una_contrasena_anterior_al_acedor_se_custodia_al_entrar_su_dueno(vault):
    vault.set_password_hash("trabajo", hash_password("clave-trabajo"))
    activate(vault)
    key = vault.open_admin(ADMIN_PASSWORD)
    assert vault.custody.reveal(key, ["trabajo"]) == {"trabajo": None}
    vault.attempt("trabajo", "mala", AccessOrigin.LOGIN)
    assert vault.custody.reveal(key, ["trabajo"]) == {"trabajo": None}
    vault.attempt("trabajo", "clave-trabajo", AccessOrigin.LOGIN)
    assert vault.custody.reveal(key, ["trabajo"]) == {"trabajo": "clave-trabajo"}


def test_sin_acedor_no_se_custodia_nada(vault):
    vault.set_password_hash("trabajo", hash_password("clave-trabajo"))
    vault.attempt("trabajo", "clave-trabajo", AccessOrigin.LOGIN)
    assert not vault.custody.has("trabajo")


def test_quitar_la_contrasena_descarta_su_custodia(vault):
    activate(vault)
    vault.set_password_hash("trabajo", hash_password("clave-trabajo"))
    vault.custody.store("trabajo", "clave-trabajo")
    vault.clear_password("trabajo")
    assert not vault.custody.has("trabajo")


def test_reiniciar_al_acedor_lo_desactiva_y_pierde_las_custodias(vault):
    activate(vault)
    vault.set_password_hash("trabajo", hash_password("clave-trabajo"))
    vault.custody.store("trabajo", "clave-trabajo")
    vault.reset_admin()
    assert not vault.admin_active()
    assert not vault.custody.has("trabajo")
    # La contraseña del perfil sigue valiendo.
    assert vault.attempt("trabajo", "clave-trabajo", AccessOrigin.LOGIN) is (
        AttemptOutcome.GRANTED
    )
    activate(vault, "nueva-maestra")
    assert vault.admin_active()
    assert vault.open_admin(ADMIN_PASSWORD) is None


# --- Avisos de intrusión para el Acedor ------------------------------------------------------


def test_el_acedor_confirma_sus_avisos_aparte_del_dueno(vault):
    activate(vault)
    vault.set_password_hash("trabajo", hash_password("clave-trabajo"))
    for _ in range(3):
        vault.attempt("trabajo", "mala", AccessOrigin.LOGIN)
    for _ in range(3):
        vault.attempt(ADMIN_PROFILE_ID, "mala", AccessOrigin.LOGIN)
    alerts = vault.pending_admin_alerts()
    assert [a.profile_id for a in alerts] == ["trabajo", ADMIN_PROFILE_ID]
    vault.acknowledge_admin([a.id for a in alerts])
    assert vault.pending_admin_alerts() == []
    # El dueño de «trabajo» todavía no lo ha visto; los del Acedor, sí.
    assert len(vault.pending_alerts("trabajo")) == 1
    assert vault.pending_alerts(ADMIN_PROFILE_ID) == []
