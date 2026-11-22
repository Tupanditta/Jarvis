"""Perfiles, plantillas de pantalla y escritura de la configuración (ventana de
configuración)."""
from pathlib import Path

import pytest
import tomlkit

from jarvis_assistant import config as cfg
from jarvis_assistant.config.catalog import dump_catalog
from jarvis_assistant.config.ids import make_id
from jarvis_assistant.config.layouts import DEFAULT_INPUT_WIDTH, dump_layouts
from jarvis_assistant.config.profiles import DEFAULT_PROFILE_ID, dump_profiles
from jarvis_assistant.config.settings import dump_sound
from jarvis_assistant.config.writer import read_document, write_documents


def write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


LAYOUT = cfg.ScreenLayout(
    "programar", "Programar",
    dock=cfg.BarPosition(0.3, 0.05), input=cfg.BarPosition(0.6, 0.9), input_width=0.4,
    windows={
        "comandos": cfg.WindowPlacement(True, 0.1, 0.2, 0.3, 0.4, 2),
        "ayuda": cfg.WindowPlacement(False, 0.5, 0.1, 0.2, 0.3, 0),
    },
    meters={"recursos": False, "ruido": True},
)  # fmt: skip


# --- Perfiles --------------------------------------------------------------------------------


def test_sin_perfiles_hay_uno_predeterminado_con_el_nombre_de_settings(tmp_path):
    write(tmp_path, "settings.toml", '[user]\nname = "Jane Doe"\n')
    config, errors = cfg.load(tmp_path)
    assert errors == []
    assert config.profiles == ()
    (profile,) = config.all_profiles()
    assert (profile.id, profile.user_name, profile.layout) == (DEFAULT_PROFILE_ID, "Jane Doe", "")
    assert config.profile("otro") == profile


def test_los_perfiles_se_leen_y_el_desconocido_resuelve_al_primero(tmp_path):
    write(tmp_path, "profiles.toml", """
[[profiles]]
id = "trabajo"
name = "Trabajo"
user_name = "Jane Doe"

[[profiles]]
id = "casa"
name = "Casa"
""")
    config, errors = cfg.load(tmp_path)
    assert errors == []
    assert [p.id for p in config.all_profiles()] == ["trabajo", "casa"]
    assert config.profile("casa").name == "Casa"
    assert config.profile("nadie").id == "trabajo"
    assert config.profile(None).user_name == "Jane Doe"


@pytest.mark.parametrize("entries, key", [
    ('id = "Mal Id"\nname = "A"', "profiles[0].id"),
    ('id = "a"\nname = ""', "profiles[0].name"),
])  # fmt: skip
def test_un_perfil_invalido_se_descarta_con_error(tmp_path, entries, key):
    text = f'[[profiles]]\n{entries}\n\n[[profiles]]\nid = "b"\nname = "B"\n'
    write(tmp_path, "profiles.toml", text)
    config, errors = cfg.load(tmp_path)
    assert [(e.file, e.key, e.warning) for e in errors] == [("profiles.toml", key, False)]
    assert [p.id for p in config.profiles] == ["b"]


def test_perfiles_repetidos_por_id_o_nombre(tmp_path):
    write(tmp_path, "profiles.toml", """
[[profiles]]
id = "a"
name = "Uno"
[[profiles]]
id = "a"
name = "Dos"
[[profiles]]
id = "c"
name = "uno"
""")
    config, errors = cfg.load(tmp_path)
    assert [e.key for e in errors] == ["profiles[1].id", "profiles[2].name"]
    assert [p.id for p in config.profiles] == ["a"]


def test_un_perfil_con_una_plantilla_que_no_existe_avisa_y_usa_la_de_fabrica(tmp_path):
    write(tmp_path, "profiles.toml", '[[profiles]]\nid = "a"\nname = "A"\nlayout = "nada"\n')
    config, errors = cfg.load(tmp_path)
    assert [(e.file, e.warning) for e in errors] == [("profiles.toml", True)]
    assert config.layout(config.profile("a").layout) == cfg.FACTORY_LAYOUT


# --- Plantillas ------------------------------------------------------------------------------


def test_una_plantilla_se_lee_con_sus_barras_y_ventanas(tmp_path):
    write(tmp_path, "layouts.toml", """
[[layouts]]
id = "programar"
name = "Programar"
[layouts.dock]
x = 0.3
y = 0.05
[layouts.input]
x = 0.6
y = 0.9
width = 0.4
[layouts.windows.comandos]
open = true
x = 0.1
y = 0.2
width = 0.3
height = 0.4
order = 2
[layouts.windows.ayuda]
x = 0.5
y = 0.1
width = 0.2
height = 0.3
[layouts.meters]
recursos = false
ruido = true
""")
    config, errors = cfg.load(tmp_path)
    assert errors == []
    assert config.layouts == (LAYOUT,)
    assert config.layout("programar") == LAYOUT
    assert config.layout("") == cfg.FACTORY_LAYOUT
    assert [item.id for item in config.all_layouts()] == [cfg.FACTORY_LAYOUT_ID, "programar"]


def test_una_plantilla_sin_barras_usa_las_posiciones_de_fabrica(tmp_path):
    write(tmp_path, "layouts.toml", '[[layouts]]\nid = "a"\nname = "A"\n')
    (layout,) = cfg.load(tmp_path)[0].layouts
    assert (layout.dock, layout.input, layout.input_width) == (
        cfg.FACTORY_LAYOUT.dock, cfg.FACTORY_LAYOUT.input, DEFAULT_INPUT_WIDTH
    )
    assert [layout.meter_shown(meter) for meter in cfg.METERS] == [
        meter.shown for meter in cfg.METERS
    ]


@pytest.mark.parametrize("body, key", [
    ('id = "fabrica"\nname = "X"', "layouts[0].id"),
    ('id = "a"\nname = "Fábrica"', "layouts[0].name"),
    ('id = "a"\nname = "A"\n[layouts.dock]\nx = 1.5', "layouts[0].dock.x"),
    ('id = "a"\nname = "A"\n[layouts.input]\nwidth = 0.01', "layouts[0].input.width"),
    ('id = "a"\nname = "A"\n[layouts.windows.ayuda]\nwidth = 0.01',
     "layouts[0].windows.ayuda.width"),
    ('id = "a"\nname = "A"\n[layouts.meters]\nruido = "si"', "layouts[0].meters.ruido"),
])  # fmt: skip
def test_una_plantilla_invalida_se_descarta_con_error(tmp_path, body, key):
    write(tmp_path, "layouts.toml", f"[[layouts]]\n{body}\n")
    config, errors = cfg.load(tmp_path)
    assert [(e.key, e.warning) for e in errors] == [(key, False)]
    assert config.layouts == ()


# --- Escritura -------------------------------------------------------------------------------


def test_volcar_y_releer_da_lo_mismo(tmp_path):
    profiles = (cfg.Profile("a", "Trabajo", "Jane Doe", "programar"), cfg.Profile("b", "Casa"))
    apps = (cfg.AppEntry("Editor", "C:/editor.exe", ("ed",), ("--nuevo",)),)
    pages = (cfg.PageEntry("Ejemplo", "https://example.com", ("ej",)),)
    documents = {name: read_document(tmp_path, name) for name in
                 ("settings.toml", "catalog.toml", "profiles.toml", "layouts.toml")}
    dump_sound(documents["settings.toml"], cfg.SoundSettings(enabled=False))
    dump_catalog(documents["catalog.toml"], apps, pages)
    dump_profiles(documents["profiles.toml"], profiles)
    dump_layouts(documents["layouts.toml"], [LAYOUT])
    write_documents(tmp_path, documents)

    config, errors = cfg.load(tmp_path)
    assert errors == []
    assert config.settings.sound.enabled is False
    assert (config.catalog.apps, config.catalog.pages) == (apps, pages)
    assert config.profiles == profiles
    assert config.layouts == (LAYOUT,)


def test_guardar_conserva_los_comentarios_y_las_demas_claves(tmp_path):
    write(tmp_path, "settings.toml", "# Cabecera\n[tts]\n# Volumen\nvolume = 0.5\n")
    document = read_document(tmp_path, "settings.toml")
    dump_sound(document, cfg.SoundSettings(enabled=False))
    write_documents(tmp_path, {"settings.toml": document})
    text = (tmp_path / "settings.toml").read_text(encoding="utf-8")
    assert "# Cabecera" in text and "# Volumen" in text and "volume = 0.5" in text
    assert cfg.load(tmp_path)[0].settings.sound.enabled is False


def test_un_documento_ausente_parte_del_predeterminado_con_sus_comentarios(tmp_path):
    document = read_document(tmp_path, "catalog.toml")
    assert "discover_installed_apps" in tomlkit.dumps(document)
    assert "#" in tomlkit.dumps(document)


def test_la_escritura_no_deja_temporales(tmp_path):
    write_documents(tmp_path, {"profiles.toml": tomlkit.document()})
    assert [p.name for p in tmp_path.iterdir()] == ["profiles.toml"]


def test_check_valida_sin_cargar():
    assert cfg.check("layouts.toml", {"layouts": [{"id": "a", "name": "A"}]}) == []
    errors = cfg.check("settings.toml", {"sound": {"enabled": "si"}})
    assert [(e.key, e.warning) for e in errors] == [("sound.enabled", False)]


def test_ids_nuevos_a_partir_del_nombre():
    assert make_id("Mi Plantilla", ()) == "mi-plantilla"
    assert make_id("Programación", {"programacion"}) == "programacion-2"
    assert make_id("¡!", ()) == "elemento"


def test_el_id_y_el_nombre_del_acedor_estan_reservados(tmp_path):
    from jarvis_assistant import config as cfg

    (tmp_path / "profiles.toml").write_text(
        '[[profiles]]\nid = "acedor"\nname = "Jefe"\n\n'
        '[[profiles]]\nid = "jefe"\nname = "acedor"\n\n'
        '[[profiles]]\nid = "casa"\nname = "Casa"\n',
        encoding="utf-8",
    )
    config, errors = cfg.load(tmp_path)
    assert [p.id for p in config.profiles] == ["casa"]
    assert len([e for e in errors if e.file == "profiles.toml"]) == 2
