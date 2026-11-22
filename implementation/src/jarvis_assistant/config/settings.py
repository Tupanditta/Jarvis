"""`settings.toml`: ajustes generales, una sección por tema."""
import dataclasses
from dataclasses import dataclass, field
from typing import Any

from jarvis_assistant.config.reader import Reader


@dataclass(frozen=True)
class InputSettings:
    inactivity_to_idle_seconds: float = 120.0


@dataclass(frozen=True)
class TtsSettings:
    voice: str = "es_ES-davefx-medium"
    volume: float = 1.0
    cache_size: int = 64


@dataclass(frozen=True)
class SoundSettings:
    # Sonido del asistente: su voz y el aviso de las ventanas al aparecer. Desactivado, los
    # subtítulos se siguen mostrando.
    enabled: bool = True


@dataclass(frozen=True)
class RouterSettings:
    intent_threshold: int = 80
    wake_threshold: int = 80
    control_threshold: int = 80
    idle_closing_threshold: int = 85
    catalog_threshold: int = 75
    path_threshold: int = 80
    default_hour: int = 9


@dataclass(frozen=True)
class DialogueSettings:
    timeout_seconds: float = 20.0
    max_collisions: int = 3


@dataclass(frozen=True)
class CommandsSettings:
    default_timeout_seconds: float = 120.0
    output_lines: int = 200


@dataclass(frozen=True)
class SearchSettings:
    max_results: int = 10
    fallback_timeout_seconds: float = 5.0


@dataclass(frozen=True)
class RemindersSettings:
    snooze_minutes: int = 10
    max_triggers: int = 5
    autoconfirm_seconds: float = 300.0


@dataclass(frozen=True)
class UiSettings:
    hud_corner: str = "top-right"
    hud_collapse_seconds: float = 8.0
    quality: str = "high"
    reduce_motion: bool = False


@dataclass(frozen=True)
class StartupSettings:
    open_session_on_start: bool = False


@dataclass(frozen=True)
class LoggingSettings:
    level: str = "INFO"


@dataclass(frozen=True)
class UserSettings:
    # Obsoleto: el nombre lo da cada perfil (`profiles.toml`). Se usa solo si no hay perfiles.
    name: str = ""


@dataclass(frozen=True)
class Settings:
    input: InputSettings = field(default_factory=InputSettings)
    tts: TtsSettings = field(default_factory=TtsSettings)
    sound: SoundSettings = field(default_factory=SoundSettings)
    router: RouterSettings = field(default_factory=RouterSettings)
    dialogue: DialogueSettings = field(default_factory=DialogueSettings)
    commands: CommandsSettings = field(default_factory=CommandsSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    reminders: RemindersSettings = field(default_factory=RemindersSettings)
    ui: UiSettings = field(default_factory=UiSettings)
    startup: StartupSettings = field(default_factory=StartupSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    user: UserSettings = field(default_factory=UserSettings)


_NON_EMPTY = "non-empty"
_PERCENT = (0, 100)
_UNIT = (0, 1)

# Límites de cada clave: (mínimo, máximo), valores admitidos o `_NON_EMPTY`.
_RULES: dict[str, tuple[float, float] | frozenset[str] | str] = {
    "input.inactivity_to_idle_seconds": (5, 600),
    "tts.voice": _NON_EMPTY,
    "tts.volume": _UNIT,
    "tts.cache_size": (0, 1024),
    "router.intent_threshold": _PERCENT,
    "router.wake_threshold": _PERCENT,
    "router.control_threshold": _PERCENT,
    "router.idle_closing_threshold": _PERCENT,
    "router.catalog_threshold": _PERCENT,
    "router.path_threshold": _PERCENT,
    "router.default_hour": (0, 23),
    "dialogue.timeout_seconds": (5, 120),
    "dialogue.max_collisions": (1, 10),
    "commands.default_timeout_seconds": (1, 3600),
    "commands.output_lines": (10, 5000),
    "search.max_results": (1, 50),
    "search.fallback_timeout_seconds": (1, 60),
    "reminders.snooze_minutes": (1, 1440),
    "reminders.max_triggers": (1, 20),
    "reminders.autoconfirm_seconds": (10, 3600),
    "ui.hud_corner": frozenset({"top-right", "top-left", "bottom-right", "bottom-left"}),
    "ui.hud_collapse_seconds": (1, 600),
    "ui.quality": frozenset({"high", "medium", "low"}),
    "logging.level": frozenset({"DEBUG", "INFO", "WARNING", "ERROR"}),
}


def parse_settings(reader: Reader) -> Settings:
    sections = {}
    for section in dataclasses.fields(Settings):
        table = reader.table(section.name)
        cls = section.default_factory  # type: ignore[misc]
        values: dict[str, Any] = {}
        for item in dataclasses.fields(cls):  # type: ignore[arg-type]
            rule = _RULES.get(f"{section.name}.{item.name}")
            bounds = rule if isinstance(rule, tuple) else None
            default = item.default
            if isinstance(default, bool):
                values[item.name] = table.boolean(item.name, default)
            elif isinstance(default, int):
                values[item.name] = table.integer(item.name, default, bounds)
            elif isinstance(default, float):
                values[item.name] = table.number(item.name, default, bounds)
            else:
                values[item.name] = table.text(
                    item.name,
                    default,
                    choices=rule if isinstance(rule, frozenset) else None,
                    non_empty=rule == _NON_EMPTY,
                )
        table.close()
        sections[section.name] = cls(**values)  # type: ignore[misc]
    return Settings(**sections)


def dump_sound(document: Any, sound: SoundSettings) -> None:
    """Escribe la sección `[sound]` en un documento `tomlkit`, sin tocar el resto."""
    import tomlkit

    if "sound" not in document:
        table = tomlkit.table()
        table.add(tomlkit.comment("Sonido del asistente: su voz y el aviso de las ventanas."))
        document.add(tomlkit.nl())
        document.add("sound", table)
    document["sound"]["enabled"] = sound.enabled
