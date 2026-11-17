"""Configuración: modelos inmutables y carga de los archivos TOML (RNF-26, AD-11).

Un módulo por archivo, con sus `dataclass` y su función `parse`; `loader` los reúne en
`Config`. El asistente solo lee la configuración. El único que la escribe es la ventana de
configuración (`configurator/`), con `writer`, y solo al pulsar Guardar.

Este módulo reexporta la interfaz pública: `from jarvis_assistant.config import Config`.
"""
from jarvis_assistant.config.catalog import AppEntry, Catalog, PageEntry
from jarvis_assistant.config.commands import DEFAULT_BINARIES, Binary
from jarvis_assistant.config.layouts import (
    FACTORY_LAYOUT,
    FACTORY_LAYOUT_ID,
    BarPosition,
    ScreenLayout,
    WindowPlacement,
)
from jarvis_assistant.config.loader import (
    CONFIG_FILES,
    DEFAULTS_DIR,
    Config,
    check,
    default_config,
    install_defaults,
    load,
)
from jarvis_assistant.config.profiles import Profile
from jarvis_assistant.config.protocols import ProtocolDef, ProtocolTask, validate_protocols
from jarvis_assistant.config.reader import ConfigError
from jarvis_assistant.config.settings import (
    CommandsSettings,
    DialogueSettings,
    InputSettings,
    LoggingSettings,
    RemindersSettings,
    RouterSettings,
    SearchSettings,
    Settings,
    SoundSettings,
    StartupSettings,
    TtsSettings,
    UiSettings,
    UserSettings,
)
from jarvis_assistant.config.structures import StructureDef

__all__ = [
    "CONFIG_FILES", "DEFAULTS_DIR", "DEFAULT_BINARIES", "FACTORY_LAYOUT", "FACTORY_LAYOUT_ID",
    "AppEntry", "BarPosition", "Binary", "Catalog", "CommandsSettings", "Config", "ConfigError",
    "DialogueSettings", "InputSettings", "LoggingSettings", "PageEntry", "Profile",
    "ProtocolDef", "ProtocolTask", "RemindersSettings", "RouterSettings", "ScreenLayout",
    "SearchSettings", "Settings", "SoundSettings", "StartupSettings", "StructureDef",
    "TtsSettings", "UiSettings", "UserSettings", "WindowPlacement",
    "check", "default_config", "install_defaults", "load", "validate_protocols",
]  # fmt: skip
