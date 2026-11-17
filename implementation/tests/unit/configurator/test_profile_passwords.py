"""Apartado Perfiles con perfiles protegidos: bloqueo, desbloqueo y contraseña al guardar."""
from datetime import UTC, datetime

import pytest

from jarvis_assistant.configurator.draft import Draft
from jarvis_assistant.configurator.editor import LayoutEditor
from jarvis_assistant.configurator.registry import SECTIONS, SectionContext
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.repositories import ReminderRepository
from jarvis_assistant.core.security import (
    AccessOrigin,
    AttemptOutcome,
    ProfileVault,
    hash_password,
)

PROFILES = """\
[[profiles]]
id = "trabajo"
name = "Trabajo"

[[profiles]]
id = "secreto"
name = "Confidencial"
"""
PASSWORD = "clave-1234"


class Rig:
    def __init__(self, directory, db: Database) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "profiles.toml").write_text(PROFILES, encoding="utf-8")
        self.vault = ProfileVault(db)
        self.vault.set_password_hash("secreto", hash_password(PASSWORD))
        self.editor = LayoutEditor()
        self.sections = {}
        for spec in SECTIONS:
            context = SectionContext(self.editor, self.sections, self.vault)
            self.sections[spec.id] = spec.create(context)
        self.draft = Draft(directory, self.sections)
        self.draft.open()

    @property
    def profiles(self):
        return self.sections["perfiles"]

    def item(self, profile_id: str) -> dict:
        return next(item for item in self.profiles.items if item["id"] == profile_id)

    def row(self, profile_id: str) -> int:
        return [item["id"] for item in self.profiles.items].index(profile_id)


@pytest.fixture
def db():
    database = Database(":memory:")
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def rig(tmp_path, qapp, db):
    return Rig(tmp_path / "config", db)


def test_un_perfil_protegido_aparece_bloqueado(rig):
    assert (rig.item("secreto")["protected"], rig.item("secreto")["unlocked"]) == (True, False)
    assert (rig.item("trabajo")["protected"], rig.item("trabajo")["unlocked"]) == (False, True)


def test_bloqueado_no_se_edita_ni_se_duplica_ni_se_elimina(rig):
    row = rig.row("secreto")
    rig.profiles.setName(row, "Otro nombre")
    assert rig.profiles.duplicate(row) == -1
    rig.profiles.remove(row)
    rig.profiles.clearPassword(row)
    assert rig.profiles.setPassword(row, "nueva-clave", "nueva-clave") != ""
    assert rig.item("secreto")["name"] == "Confidencial"
    assert len(rig.profiles.items) == 2
    assert not rig.profiles.dirty


def test_desbloquear_con_la_contrasena_permite_editarlo(rig):
    row = rig.row("secreto")
    assert rig.profiles.unlock(row, PASSWORD) == "concedido"
    assert rig.item("secreto")["unlocked"]
    rig.profiles.setName(row, "Privado")
    assert rig.item("secreto")["name"] == "Privado"


def test_tres_fallos_en_la_configuracion_registran_un_aviso(rig):
    row = rig.row("secreto")
    outcomes = [rig.profiles.unlock(row, "mala") for _ in range(3)]
    assert outcomes == ["denegado", "denegado", "bloqueado"]
    assert not rig.item("secreto")["unlocked"]
    (alert,) = rig.vault.pending_alerts("secreto")
    assert alert.origin.value == "configuracion"


def test_poner_contrasena_se_aplica_al_guardar(rig):
    row = rig.row("trabajo")
    assert rig.profiles.setPassword(row, "abc", "abc") != ""  # menos de 4
    assert rig.profiles.setPassword(row, "abcd", "abce") != ""  # no coinciden
    assert not rig.vault.is_protected("trabajo")
    assert rig.profiles.setPassword(row, "abcd", "abcd") == ""
    assert rig.item("trabajo")["protected"]
    assert not rig.vault.is_protected("trabajo")  # todavía no se ha guardado
    assert rig.draft.save().saved
    assert rig.vault.is_protected("trabajo")
    assert rig.vault.attempt("trabajo", "abcd", AccessOrigin.SETTINGS) is AttemptOutcome.GRANTED
    # Recién protegido en esta ventana: sigue desbloqueado hasta cerrarla.
    assert rig.item("trabajo")["unlocked"]


def test_descartar_no_pone_la_contrasena(rig):
    rig.profiles.setPassword(rig.row("trabajo"), "abcd", "abcd")
    rig.draft.open()
    assert not rig.item("trabajo")["protected"]
    assert not rig.vault.is_protected("trabajo")


def test_quitar_la_contrasena_pide_desbloquear_y_se_aplica_al_guardar(rig):
    row = rig.row("secreto")
    rig.profiles.unlock(row, PASSWORD)
    rig.profiles.clearPassword(row)
    assert not rig.item("secreto")["protected"]
    assert rig.draft.save().saved
    assert not rig.vault.is_protected("secreto")


def test_eliminar_un_perfil_desbloqueado_retira_sus_datos(rig, db):
    ReminderRepository(db, "secreto").create("Clave", [], None, rig_now())
    row = rig.row("secreto")
    rig.profiles.unlock(row, PASSWORD)
    rig.profiles.remove(row)
    assert rig.draft.save().saved
    assert not rig.vault.is_protected("secreto")
    assert ReminderRepository(db, "secreto").listable() == []


def test_duplicar_un_perfil_protegido_no_copia_la_contrasena(rig):
    row = rig.row("secreto")
    rig.profiles.unlock(row, PASSWORD)
    copy = rig.profiles.duplicate(row)
    assert copy >= 0
    item = rig.profiles.items[copy]
    assert (item["protected"], item["unlocked"]) == (False, True)


def test_un_perfil_nuevo_no_reutiliza_el_id_de_uno_protegido_que_ya_no_esta(tmp_path, qapp, db):
    rig = Rig(tmp_path / "config", db)
    rig.vault.set_password_hash("perfil-nuevo", hash_password(PASSWORD))
    rig.draft.open()  # la ventana se abre con esa contraseña ya guardada
    row = rig.profiles.add()
    assert rig.profiles.items[row]["id"] != "perfil-nuevo"
    assert not rig.profiles.items[row]["protected"]


def rig_now():
    return datetime(2026, 1, 1, tzinfo=UTC)
