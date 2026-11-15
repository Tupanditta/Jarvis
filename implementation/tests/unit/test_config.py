"""Carga y validación de la configuración TOML (T-0.5, configuracion.md)."""
import dataclasses
from pathlib import Path

import pytest

from jarvis_assistant import config as cfg

# Tabla de `settings.toml` de configuracion.md.
SPEC_DEFAULTS = {
    "input": {"inactivity_to_idle_seconds": 30},
    "tts": {"voice": "es_ES-davefx-medium", "volume": 1.0, "cache_size": 64},
    "router": {
        "intent_threshold": 80, "wake_threshold": 80, "control_threshold": 80,
        "idle_closing_threshold": 85, "catalog_threshold": 75, "path_threshold": 80,
        "default_hour": 9,
    },
    "dialogue": {"timeout_seconds": 20, "max_collisions": 3},
    "commands": {"default_timeout_seconds": 120, "output_lines": 200},
    "search": {"max_results": 10, "fallback_timeout_seconds": 5},
    "reminders": {"snooze_minutes": 10, "max_triggers": 5, "autoconfirm_seconds": 300},
    "ui": {
        "hud_corner": "top-right", "hud_collapse_seconds": 8, "quality": "high",
        "reduce_motion": False,
    },
    "startup": {"open_session_on_start": False},
    "logging": {"level": "INFO"},
}  # fmt: skip


def write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def load_ok(directory: Path, **kwargs) -> cfg.Config:
    config, errors = cfg.load(directory, **kwargs)
    assert errors == []
    return config


def settings_as_dict(settings: cfg.Settings) -> dict:
    return dataclasses.asdict(settings)


# --- Valores predeterminados -----------------------------------------------------------------


def test_sin_carpeta_de_configuracion_se_usan_los_predeterminados(tmp_path):
    config = load_ok(tmp_path / "no-existe")
    assert settings_as_dict(config.settings) == SPEC_DEFAULTS


def test_los_predeterminados_del_resto_de_archivos(tmp_path):
    config = load_ok(tmp_path)
    assert config.catalog == cfg.Catalog(discover_installed_apps=True, apps=(), pages=())
    assert dict(config.places) == {}
    assert [b.name for b in config.binaries] == [
        "git", "gcc", "g++", "make", "python", "pip", "node", "npm",
    ]  # fmt: skip
    assert dict(config.aliases) == {}
    assert config.protocols == ()
    assert config.structures == ()


@pytest.mark.parametrize("name", cfg.CONFIG_FILES)
def test_un_archivo_vacio_es_valido(tmp_path, name):
    write(tmp_path, name, "")
    assert load_ok(tmp_path) == load_ok(tmp_path / "vacia")


def test_una_clave_presente_sustituye_solo_a_su_predeterminado(tmp_path):
    write(tmp_path, "settings.toml", "[tts]\nvolume = 0.7\n")
    tts = load_ok(tmp_path).settings.tts
    assert tts.volume == 0.7
    assert tts.cache_size == 64


def test_un_entero_vale_donde_se_espera_un_decimal(tmp_path):
    write(tmp_path, "settings.toml", "[input]\ninactivity_to_idle_seconds = 45\n")
    seconds = load_ok(tmp_path).settings.input.inactivity_to_idle_seconds
    assert seconds == 45.0 and isinstance(seconds, float)


def test_la_configuracion_es_inmutable(tmp_path):
    config = load_ok(tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.settings.tts.volume = 0.9
    with pytest.raises(TypeError):
        config.aliases["a"] = "b"
    with pytest.raises(TypeError):
        config.places["a"] = Path("b")


# --- Claves desconocidas: aviso --------------------------------------------------------------


def test_una_clave_desconocida_avisa_y_no_invalida_el_archivo(tmp_path):
    write(tmp_path, "settings.toml", "[tts]\nvolume = 0.4\nvolumen = 3\n")
    config, errors = cfg.load(tmp_path)
    assert config.settings.tts.volume == 0.4
    assert len(errors) == 1
    error = errors[0]
    assert (error.file, error.key, error.warning) == ("settings.toml", "tts.volumen", True)
    assert "desconocida" in error.reason


def test_una_seccion_desconocida_avisa(tmp_path):
    write(tmp_path, "settings.toml", "[inventada]\nx = 1\n")
    _, errors = cfg.load(tmp_path)
    assert [(e.key, e.warning) for e in errors] == [("inventada", True)]


def test_las_secciones_de_la_entrada_por_voz_solo_producen_avisos(tmp_path):
    """Un `settings.toml` anterior al cambio a texto se sigue cargando."""
    write(
        tmp_path,
        "settings.toml",
        "[audio]\nsilence_to_idle_seconds = 60\n[stt]\nmodel = \"small\"\n"
        "[tts]\nvolume = 0.5\n[ui]\nwake_brings_screen_to_front = true\n",
    )
    config, errors = cfg.load(tmp_path)
    assert config.settings.tts.volume == 0.5
    assert config.settings.input.inactivity_to_idle_seconds == 30.0
    assert all(error.warning for error in errors)
    assert {error.key for error in errors} == {"audio", "stt", "ui.wake_brings_screen_to_front"}


def test_una_clave_desconocida_en_un_elemento_de_lista_avisa(tmp_path):
    write(tmp_path, "commands.toml", '[[binaries]]\nname = "git"\nexecutable = "git"\ncolor = 1\n')
    config, errors = cfg.load(tmp_path)
    assert [b.name for b in config.binaries] == ["git"]
    assert [(e.key, e.warning) for e in errors] == [("binaries[0].color", True)]


# --- Tipos erróneos y valores fuera de rango -------------------------------------------------


@pytest.mark.parametrize(
    ("text", "key", "fragment"),
    [
        ('[tts]\nvolume = "alto"\n', "tts.volume", "número"),
        ("[ui]\nreduce_motion = 1\n", "ui.reduce_motion", "booleano"),
        ("[tts]\ncache_size = 2.5\n", "tts.cache_size", "entero"),
        ("[tts]\ncache_size = true\n", "tts.cache_size", "entero"),
        ("[tts]\nvoice = 3\n", "tts.voice", "texto"),
        ("input = 3\n", "input", "tabla"),
        ("[tts]\nvolume = 1.5\n", "tts.volume", "entre 0 y 1"),
        (
            "[input]\ninactivity_to_idle_seconds = 1\n",
            "input.inactivity_to_idle_seconds",
            "entre 5 y 600",
        ),
        ("[router]\nwake_threshold = 101\n", "router.wake_threshold", "entre 0 y 100"),
        ("[router]\ndefault_hour = 24\n", "router.default_hour", "entre 0 y 23"),
        ("[router]\nintent_threshold = -1\n", "router.intent_threshold", "entre 0 y 100"),
        ('[ui]\nquality = "ultra"\n', "ui.quality", "high"),
        ('[ui]\nhud_corner = "centro"\n', "ui.hud_corner", "top-right"),
        ('[logging]\nlevel = "TRACE"\n', "logging.level", "INFO"),
        ('[tts]\nvoice = ""\n', "tts.voice", "vacío"),
    ],
)
def test_un_valor_invalido_indica_archivo_clave_y_motivo(tmp_path, text, key, fragment):
    write(tmp_path, "settings.toml", text)
    config, errors = cfg.load(tmp_path)
    assert len(errors) == 1
    error = errors[0]
    assert (error.file, error.key, error.warning) == ("settings.toml", key, False)
    assert fragment in error.reason
    assert settings_as_dict(config.settings) == SPEC_DEFAULTS


def test_un_archivo_con_sintaxis_invalida_es_un_error(tmp_path):
    write(tmp_path, "aliases.toml", "[aliases\n")
    config, errors = cfg.load(tmp_path)
    assert [(e.file, e.key, e.warning) for e in errors] == [("aliases.toml", "", False)]
    assert dict(config.aliases) == {}


def test_un_archivo_que_no_es_utf8_es_un_error(tmp_path):
    tmp_path.joinpath("aliases.toml").write_bytes(b'[aliases]\n"a" = "\xff\xfe"\n')
    _, errors = cfg.load(tmp_path)
    assert [e.file for e in errors] == ["aliases.toml"]


def test_el_error_de_un_archivo_no_afecta_a_los_demas(tmp_path):
    write(tmp_path, "settings.toml", "[tts]\ncache_size = -1\n")
    write(tmp_path, "aliases.toml", '[aliases]\n"ce de" = "cd"\n')
    config, errors = cfg.load(tmp_path)
    assert [e.file for e in errors] == ["settings.toml"]
    assert dict(config.aliases) == {"ce de": "cd"}


# --- Recarga ---------------------------------------------------------------------------------


def test_recargar_con_un_archivo_invalido_conserva_el_anterior_y_devuelve_el_error(tmp_path):
    write(tmp_path, "settings.toml", "[tts]\nvolume = 0.5\n")
    write(tmp_path, "aliases.toml", '[aliases]\n"guit" = "git"\n')
    previous = load_ok(tmp_path)

    write(tmp_path, "settings.toml", "[tts]\nvolume = 7\n")
    write(tmp_path, "aliases.toml", '[aliases]\n"ele ese" = "ls"\n')
    config, errors = cfg.load(tmp_path, previous=previous)

    assert [(e.file, e.key) for e in errors] == [("settings.toml", "tts.volume")]
    assert config.settings == previous.settings
    assert dict(config.aliases) == {"ele ese": "ls"}


def test_recargar_archivos_validos_aplica_los_cambios(tmp_path):
    previous = load_ok(tmp_path)
    write(tmp_path, "settings.toml", "[tts]\nvolume = 0.5\n")
    assert load_ok(tmp_path, previous=previous).settings.tts.volume == 0.5


# --- catalog.toml ----------------------------------------------------------------------------

CATALOG = """
discover_installed_apps = false

[[apps]]
name = "Visual Studio Code"
aliases = ["code", "vs code"]
path = "C:/Code.exe"
args = ["--new-window"]

[[apps]]
name = "Bloc de notas"
path = "notepad.exe"

[[pages]]
name = "GitHub"
aliases = ["git hub"]
url = "https://github.com"
"""


def test_catalogo_de_aplicaciones_y_paginas(tmp_path):
    write(tmp_path, "catalog.toml", CATALOG)
    catalog = load_ok(tmp_path).catalog
    assert catalog.discover_installed_apps is False
    assert catalog.apps == (
        cfg.AppEntry("Visual Studio Code", "C:/Code.exe", ("code", "vs code"), ("--new-window",)),
        cfg.AppEntry("Bloc de notas", "notepad.exe"),
    )
    assert catalog.pages == (cfg.PageEntry("GitHub", "https://github.com", ("git hub",)),)


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ('[[apps]]\npath = "x.exe"\n', "apps[0].name"),
        ('[[apps]]\nname = "X"\n', "apps[0].path"),
        ('[[apps]]\nname = "X"\npath = "x"\naliases = "x"\n', "apps[0].aliases"),
        ('[[apps]]\nname = "X"\npath = "x"\naliases = [1]\n', "apps[0].aliases"),
        ('[[pages]]\nname = "X"\n', "pages[0].url"),
        ('[[pages]]\nname = "X"\nurl = "ftp://x"\n', "pages[0].url"),
        ("apps = 3\n", "apps"),
        ('discover_installed_apps = "si"\n', "discover_installed_apps"),
    ],
)
def test_catalogo_invalido(tmp_path, text, key):
    write(tmp_path, "catalog.toml", text)
    config, errors = cfg.load(tmp_path)
    assert [(e.file, e.key, e.warning) for e in errors] == [("catalog.toml", key, False)]
    assert config.catalog == cfg.Catalog()


# --- places.toml, aliases.toml ---------------------------------------------------------------


def test_lugares_con_nombre(tmp_path):
    write(tmp_path, "places.toml", '[places]\nproyectos = "D:/Proyectos"\n')
    assert dict(load_ok(tmp_path).places) == {"proyectos": Path("D:/Proyectos")}


def test_un_lugar_que_no_es_texto_es_un_error(tmp_path):
    write(tmp_path, "places.toml", "[places]\nproyectos = 3\n")
    _, errors = cfg.load(tmp_path)
    assert [(e.file, e.key) for e in errors] == [("places.toml", "places.proyectos")]


def test_alias_de_transcripcion(tmp_path):
    write(tmp_path, "aliases.toml", '[aliases]\n"ce de" = "cd"\n"guit" = "git"\n')
    assert dict(load_ok(tmp_path).aliases) == {"ce de": "cd", "guit": "git"}


def test_un_alias_que_no_es_texto_es_un_error(tmp_path):
    write(tmp_path, "aliases.toml", '[aliases]\n"ce de" = ["cd"]\n')
    _, errors = cfg.load(tmp_path)
    assert [(e.file, e.key) for e in errors] == [("aliases.toml", "aliases.ce de")]


# --- commands.toml ---------------------------------------------------------------------------

COMMANDS = """
[[binaries]]
name = "git"
executable = "git"
aliases = ["guit"]
timeout_seconds = 60

[[binaries]]
name = "gcc"
executable = "C:/mingw/bin/gcc.exe"
"""


def test_binarios_permitidos(tmp_path):
    write(tmp_path, "commands.toml", COMMANDS)
    assert load_ok(tmp_path).binaries == (
        cfg.Binary("git", "git", ("guit",), 60.0),
        cfg.Binary("gcc", "C:/mingw/bin/gcc.exe"),
    )


def test_una_lista_de_binarios_vacia_no_permite_ninguno(tmp_path):
    write(tmp_path, "commands.toml", "binaries = []\n")
    assert load_ok(tmp_path).binaries == ()


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ('[[binaries]]\nexecutable = "git"\n', "binaries[0].name"),
        ('[[binaries]]\nname = "git"\n', "binaries[0].executable"),
        (
            '[[binaries]]\nname = "git"\nexecutable = "git"\ntimeout_seconds = 0\n',
            "binaries[0].timeout_seconds",
        ),
        (
            '[[binaries]]\nname = "git"\nexecutable = "a"\n'
            '[[binaries]]\nname = "Git"\nexecutable = "b"\n',
            "binaries[1].name",
        ),
    ],
)
def test_binarios_invalidos(tmp_path, text, key):
    write(tmp_path, "commands.toml", text)
    config, errors = cfg.load(tmp_path)
    assert [(e.file, e.key) for e in errors] == [("commands.toml", key)]
    assert len(config.binaries) == 8


# --- structures.toml -------------------------------------------------------------------------


def test_estructuras_de_carpetas(tmp_path):
    write(
        tmp_path,
        "structures.toml",
        '[[structures]]\nname = "proyecto python"\nfolders = ["src", "tests"]\n',
    )
    assert load_ok(tmp_path).structures == (cfg.StructureDef("proyecto python", ("src", "tests")),)


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ('[[structures]]\nfolders = ["a"]\n', "structures[0].name"),
        ('[[structures]]\nname = "x"\n', "structures[0].folders"),
        ('[[structures]]\nname = "x"\nfolders = []\n', "structures[0].folders"),
    ],
)
def test_estructuras_invalidas(tmp_path, text, key):
    write(tmp_path, "structures.toml", text)
    config, errors = cfg.load(tmp_path)
    assert [(e.file, e.key) for e in errors] == [("structures.toml", key)]
    assert config.structures == ()


# --- protocols.toml (validación estructural; el registro de intenciones llega en la fase 6) ---

PROTOCOLS = """
[[protocols]]
id = "modo-trabajo"
name = "modo trabajo"
aliases = ["a trabajar"]
important = true

  [[protocols.tasks]]
  module = "comandos"
  action = "cd"
  params = { ruta = "proyectos barra jarvis" }

  [[protocols.tasks]]
  module = "comandos"
  action = "ejecutar"
  params = { comando = "git status" }
  stop_on_error = true
  description = "Estado del repositorio"
"""


def test_protocolo_valido(tmp_path):
    write(tmp_path, "protocols.toml", PROTOCOLS)
    (protocol,) = load_ok(tmp_path).protocols
    assert (protocol.id, protocol.name, protocol.aliases, protocol.important) == (
        "modo-trabajo", "modo trabajo", ("a trabajar",), True,
    )  # fmt: skip
    first, second = protocol.tasks
    assert (first.module, first.action, dict(first.params)) == (
        "comandos", "cd", {"ruta": "proyectos barra jarvis"},
    )  # fmt: skip
    assert (first.stop_on_error, first.description) == (False, None)
    assert (second.stop_on_error, second.description) == (True, "Estado del repositorio")


def test_un_protocolo_invalido_se_descarta_y_los_demas_se_cargan(tmp_path):
    broken = '\n[[protocols]]\nid = "roto"\nname = "roto"\n'
    write(tmp_path, "protocols.toml", PROTOCOLS + broken)
    config, errors = cfg.load(tmp_path)
    assert [p.id for p in config.protocols] == ["modo-trabajo"]
    assert [(e.file, e.key, e.warning) for e in errors] == [
        ("protocols.toml", "protocols[1].tasks", False)
    ]


@pytest.mark.parametrize(
    ("second", "key"),
    [
        ('id = "modo-trabajo"\nname = "otro"', "protocols[1].id"),
        ('id = "otro"\nname = "Modo Trabajo"', "protocols[1].name"),
        ('id = "otro"\nname = "a trabajar"', "protocols[1].name"),
    ],
)
def test_un_protocolo_con_id_o_nombre_repetido_se_descarta(tmp_path, second, key):
    extra = (
        f"\n[[protocols]]\n{second}\n"
        '  [[protocols.tasks]]\n  module = "comandos"\n  action = "ls"\n'
    )
    write(tmp_path, "protocols.toml", PROTOCOLS + extra)
    config, errors = cfg.load(tmp_path)
    assert [p.id for p in config.protocols] == ["modo-trabajo"]
    assert [e.key for e in errors] == [key]


def test_una_tarea_sin_modulo_descarta_su_protocolo(tmp_path):
    write(
        tmp_path,
        "protocols.toml",
        '[[protocols]]\nid = "p"\nname = "p"\n  [[protocols.tasks]]\n  action = "ls"\n',
    )
    config, errors = cfg.load(tmp_path)
    assert config.protocols == ()
    assert [e.key for e in errors] == ["protocols[0].tasks[0].module"]


# --- Archivos predeterminados del paquete ----------------------------------------------------


def test_el_paquete_incluye_un_archivo_predeterminado_por_cada_archivo():
    names = {path.name for path in cfg.DEFAULTS_DIR.glob("*.toml")}
    assert names == set(cfg.CONFIG_FILES)


def test_los_archivos_predeterminados_se_cargan_sin_errores_ni_avisos():
    config = load_ok(cfg.DEFAULTS_DIR)
    assert settings_as_dict(config.settings) == SPEC_DEFAULTS
    assert [b.name for b in config.binaries] == [b.name for b in cfg.default_config().binaries]
    assert dict(config.aliases) == {"ce de": "cd", "ele ese": "ls", "guit": "git"}
    assert [s.name for s in config.structures] == ["proyecto python"]


def test_el_settings_predeterminado_explica_cada_clave():
    lines = (cfg.DEFAULTS_DIR / "settings.toml").read_text(encoding="utf-8").splitlines()
    for section, keys in SPEC_DEFAULTS.items():
        assert f"[{section}]" in lines
        for key in keys:
            index = next(i for i, line in enumerate(lines) if line.startswith(f"{key} = "))
            assert lines[index - 1].startswith("# "), f"{section}.{key} sin comentario"


def test_install_defaults_copia_los_archivos_en_el_primer_arranque(tmp_path):
    target = tmp_path / "config"
    created = cfg.install_defaults(target)
    assert sorted(path.name for path in created) == sorted(cfg.CONFIG_FILES)
    assert load_ok(target) == load_ok(cfg.DEFAULTS_DIR)


def test_install_defaults_no_sobrescribe_lo_que_el_usuario_ya_tiene(tmp_path):
    write(tmp_path, "aliases.toml", '[aliases]\n"mio" = "git"\n')
    created = cfg.install_defaults(tmp_path)
    assert "aliases.toml" not in {path.name for path in created}
    assert dict(load_ok(tmp_path).aliases) == {"mio": "git"}
    assert cfg.install_defaults(tmp_path) == []


def test_cargar_no_escribe_en_la_carpeta_de_configuracion(tmp_path):
    cfg.load(tmp_path)
    assert list(tmp_path.iterdir()) == []
