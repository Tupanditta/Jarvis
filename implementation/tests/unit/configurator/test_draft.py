"""Ventana de configuración sin QML: apartados, borrador y guardado (configurador.md)."""
from pathlib import Path

import pytest

from jarvis_assistant import config as cfg
from jarvis_assistant.config import FACTORY_LAYOUT, BarPosition
from jarvis_assistant.configurator.draft import Draft
from jarvis_assistant.configurator.editor import LayoutEditor
from jarvis_assistant.configurator.registry import SECTIONS, SectionContext


def write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


class Rig:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.editor = LayoutEditor()
        self.sections = {}
        for spec in SECTIONS:
            self.sections[spec.id] = spec.create(SectionContext(self.editor, self.sections))
        self.draft = Draft(directory, self.sections)
        self.draft.open()

    @property
    def layouts(self):
        return self.sections["plantillas"]

    @property
    def profiles(self):
        return self.sections["perfiles"]

    @property
    def sound(self):
        return self.sections["sonido"]

    @property
    def catalog(self):
        return self.sections["aplicaciones"]

    def files(self) -> set[str]:
        if not self.directory.exists():
            return set()
        return {path.name for path in self.directory.iterdir()}

    def loaded(self) -> cfg.Config:
        config, errors = cfg.load(self.directory)
        assert [e for e in errors if not e.warning] == []
        return config


@pytest.fixture
def rig(tmp_path, qapp):
    return Rig(tmp_path / "config")


# --- Borrador --------------------------------------------------------------------------------


def test_al_abrir_no_hay_cambios_y_guardar_sin_cambios_no_escribe(rig):
    assert not rig.draft.dirty
    assert rig.draft.save().saved
    assert rig.files() == set()


def test_nada_se_escribe_hasta_guardar_y_abrir_de_nuevo_descarta(rig):
    rig.sound.setEnabled(False)
    assert rig.draft.dirty and rig.files() == set()
    rig.draft.open()  # salir sin guardar
    assert not rig.draft.dirty and rig.sound.enabled
    assert rig.files() == set()


def test_guardar_escribe_solo_los_archivos_de_los_apartados_cambiados(rig):
    rig.sound.setEnabled(False)
    result = rig.draft.save()
    assert result.saved and result.problems == []
    assert rig.files() == {"settings.toml"}
    assert rig.loaded().settings.sound.enabled is False
    assert not rig.draft.dirty


def test_guardar_conserva_lo_que_el_usuario_escribio_a_mano(rig):
    write(rig.directory, "settings.toml", "# Mis notas\n[tts]\nvolume = 0.4\n")
    rig.draft.open()
    rig.sound.setEnabled(False)
    rig.draft.save()
    text = (rig.directory / "settings.toml").read_text(encoding="utf-8")
    assert "# Mis notas" in text and "volume = 0.4" in text


def test_con_problemas_no_se_escribe_nada(rig):
    rig.profiles.setName(0, "")
    rig.sound.setEnabled(False)
    result = rig.draft.save()
    assert not result.saved
    assert result.problems == ["Hay un perfil sin nombre."]
    assert rig.files() == set()


def test_un_archivo_con_errores_bloquea_su_apartado(rig):
    write(rig.directory, "catalog.toml", '[[pages]]\nname = "X"\nurl = "ftp://x"\n')
    rig.draft.open()
    assert "catalog.toml" in rig.catalog.locked
    assert rig.sound.locked == ""


# --- Perfiles --------------------------------------------------------------------------------


def test_sin_perfiles_empieza_con_el_predeterminado_y_se_escribe_al_guardar(rig):
    write(rig.directory, "settings.toml", '[user]\nname = "Jane Doe"\n')
    rig.draft.open()
    items = rig.profiles.items
    assert [(p["name"], p["userName"]) for p in items] == [("Predeterminado", "Jane Doe")]
    row = rig.profiles.add()
    rig.profiles.setName(row, "Casa")
    rig.profiles.setUserName(row, "John Doe")
    assert rig.draft.save().saved
    profiles = rig.loaded().profiles
    assert [(p.name, p.user_name) for p in profiles] == [
        ("Predeterminado", "Jane Doe"), ("Casa", "John Doe")
    ]


def test_el_ultimo_perfil_no_se_elimina_y_los_nombres_no_se_repiten(rig):
    rig.profiles.remove(0)
    assert len(rig.profiles.items) == 1
    row = rig.profiles.add()
    rig.profiles.setName(row, "predeterminádo")
    assert rig.draft.save().problems == ["El nombre de perfil «predeterminádo» está repetido."]


# --- Plantillas ------------------------------------------------------------------------------


def test_crear_una_plantilla_pasa_por_el_editor_y_queda_en_el_borrador(rig):
    rig.layouts.create()
    assert rig.editor.active and rig.editor.name == "Plantilla nueva"
    rig.editor.workspace.moveDock(0.1, 0.9)
    rig.editor.workspace.set_open("comandos", True)
    assert rig.editor.accept()
    assert not rig.editor.active
    assert [item["name"] for item in rig.layouts.items] == ["Fábrica", "Plantilla nueva"]
    assert rig.files() == set()
    assert rig.draft.save().saved
    (layout,) = rig.loaded().layouts
    assert layout.dock == BarPosition(0.1, 0.9)
    assert layout.windows["comandos"].open


def test_cancelar_el_editor_no_cambia_nada(rig):
    rig.layouts.create()
    rig.editor.cancel()
    assert not rig.editor.active and len(rig.layouts.items) == 1
    assert not rig.draft.dirty


def test_el_editor_no_acepta_un_nombre_vacio_ni_repetido(rig):
    rig.layouts.create()
    rig.editor.setName("  ")
    assert not rig.editor.accept() and rig.editor.error
    rig.editor.setName("fabrica")
    assert not rig.editor.accept() and "Ya hay una plantilla" in rig.editor.error
    rig.editor.setName("Estudio")
    assert rig.editor.accept()


def test_editar_una_plantilla_parte_de_su_disposicion(rig):
    rig.layouts.create()
    rig.editor.workspace.placeInput(0.5, 0.2, 0.6)
    rig.editor.accept()
    layout_id = rig.layouts.items[1]["id"]
    rig.layouts.edit(layout_id)
    assert rig.editor.workspace.inputY == 0.2
    rig.editor.cancel()


def test_eliminar_una_plantilla_en_uso_pasa_sus_perfiles_a_la_de_fabrica(rig):
    rig.layouts.create()
    rig.editor.accept()
    layout_id = rig.layouts.items[1]["id"]
    rig.profiles.setLayout(0, layout_id)
    assert rig.layouts.items[1]["usedBy"] == "Predeterminado"
    rig.layouts.remove(layout_id)
    assert rig.profiles.items[0]["layout"] == ""
    assert rig.draft.save().saved
    assert rig.loaded().profiles[0].layout == ""


def test_duplicar_la_de_fabrica_crea_una_editable(rig):
    rig.layouts.duplicate("fabrica")
    item = rig.layouts.items[1]
    assert item["name"] == "Fábrica (copia)" and not item["factory"]
    rig.draft.save()
    assert rig.loaded().layouts[0].dock == FACTORY_LAYOUT.dock


# --- Sonido ----------------------------------------------------------------------------------


def test_volver_al_valor_inicial_sigue_contando_como_cambio_pero_guarda_lo_mismo(rig):
    rig.sound.setEnabled(False)
    rig.sound.setEnabled(True)
    assert rig.draft.save().saved
    assert rig.loaded().settings.sound.enabled is True


# --- Aplicaciones y páginas ------------------------------------------------------------------


def test_anadir_una_aplicacion_y_una_pagina(rig):
    problem = rig.catalog.submit(-1, "app", " Editor ", "C:/editor.exe", "--nuevo", "ed, el editor")
    assert problem == ""
    assert rig.catalog.submit(-1, "page", "Ejemplo", "https://example.com", "", "ej") == ""
    assert [item["kind"] for item in rig.catalog.items] == ["app", "page"]
    assert rig.draft.save().saved
    catalog = rig.loaded().catalog
    editor = cfg.AppEntry("Editor", "C:/editor.exe", ("ed", "el editor"), ("--nuevo",))
    assert catalog.apps == (editor,)
    assert catalog.pages == (cfg.PageEntry("Ejemplo", "https://example.com", ("ej",)),)


@pytest.mark.parametrize("kind, name, target, aliases, fragment", [
    ("app", "", "x.exe", "", "nombre"),
    ("app", "A", "", "", "ruta"),
    ("page", "P", "example.com", "", "http"),
    ("page", "Otra", "https://example.com", "editor", "ya es el nombre"),
])  # fmt: skip
def test_un_formulario_invalido_no_se_guarda_en_el_borrador(
    rig, kind, name, target, aliases, fragment
):
    rig.catalog.submit(-1, "app", "Editor", "C:/editor.exe", "", "")
    rig.draft.save()
    problem = rig.catalog.submit(-1, kind, name, target, "", aliases)
    assert fragment in problem
    assert len(rig.catalog.items) == 1
    assert not rig.draft.dirty


def test_editar_y_eliminar_entradas(rig):
    rig.catalog.submit(-1, "app", "Editor", "C:/editor.exe", "", "")
    assert rig.catalog.submit(0, "app", "Editor", "D:/editor.exe", "", "") == ""
    assert rig.catalog.entry(0)["target"] == "D:/editor.exe"
    rig.catalog.remove(0)
    assert rig.catalog.items == []


def test_una_ruta_que_no_existe_solo_avisa(rig, tmp_path):
    assert rig.catalog.warning("app", "code") == ""  # nombre del PATH
    assert rig.catalog.warning("app", str(tmp_path / "no.exe"))
    assert rig.catalog.warning("page", "https://example.com") == ""
