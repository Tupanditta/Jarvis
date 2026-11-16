"""Configuración: modelos inmutables y carga de los archivos TOML (RNF-26, AD-11).

El asistente solo lee estos archivos (RES-36). Toda clave ausente toma el valor
predeterminado de este módulo; un archivo ausente o vacío es válido. Cada archivo se valida
por separado: si uno es inválido se conserva su configuración anterior (o la predeterminada
en el arranque) y el error indica archivo, clave y motivo.

Al cargar se comprueba la estructura de los protocolos. Su validación contra el registro de
intenciones (`validate_protocols`) la hace el orquestador, que conoce el registro, cada vez
que aplica la configuración.
"""
import dataclasses
import shutil
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

DEFAULTS_DIR = Path(__file__).resolve().parent / "resources" / "config_defaults"

CONFIG_FILES = (
    "settings.toml",
    "catalog.toml",
    "places.toml",
    "commands.toml",
    "aliases.toml",
    "protocols.toml",
    "structures.toml",
)

# --- settings.toml ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InputSettings:
    inactivity_to_idle_seconds: float = 120.0


@dataclass(frozen=True)
class TtsSettings:
    voice: str = "es_ES-davefx-medium"
    volume: float = 1.0
    cache_size: int = 64


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
    # Nombre del usuario, para la presentación del asistente. Vacío: no lo dice.
    name: str = ""


@dataclass(frozen=True)
class Settings:
    input: InputSettings = field(default_factory=InputSettings)
    tts: TtsSettings = field(default_factory=TtsSettings)
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
_SETTINGS_RULES: dict[str, tuple[float, float] | frozenset[str] | str] = {
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

# --- Resto de archivos -----------------------------------------------------------------------


@dataclass(frozen=True)
class AppEntry:
    name: str
    path: str  # ejecutable, acceso directo o nombre en el PATH
    aliases: tuple[str, ...] = ()
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageEntry:
    name: str
    url: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Catalog:
    discover_installed_apps: bool = True
    apps: tuple[AppEntry, ...] = ()
    pages: tuple[PageEntry, ...] = ()


@dataclass(frozen=True)
class Binary:
    """Binario permitido (RN-45)."""

    name: str
    executable: str  # nombre en el PATH o ruta absoluta
    aliases: tuple[str, ...] = ()
    timeout_seconds: float | None = None  # None = commands.default_timeout_seconds


@dataclass(frozen=True)
class ProtocolTask:
    module: str
    action: str
    params: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))
    stop_on_error: bool = False
    description: str | None = None


@dataclass(frozen=True)
class ProtocolDef:
    id: str
    name: str
    tasks: tuple[ProtocolTask, ...]
    aliases: tuple[str, ...] = ()
    important: bool = False


@dataclass(frozen=True)
class StructureDef:
    name: str
    folders: tuple[str, ...]


DEFAULT_BINARIES = tuple(
    Binary(name, name) for name in ("git", "gcc", "g++", "make", "python", "pip", "node", "npm")
)


@dataclass(frozen=True)
class Config:
    settings: Settings = field(default_factory=Settings)
    catalog: Catalog = field(default_factory=Catalog)
    places: Mapping[str, Path] = field(default_factory=lambda: MappingProxyType({}))
    binaries: tuple[Binary, ...] = DEFAULT_BINARIES
    aliases: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    protocols: tuple[ProtocolDef, ...] = ()
    structures: tuple[StructureDef, ...] = ()


@dataclass(frozen=True)
class ConfigError:
    """Problema de un archivo de configuración.

    Con `warning` el archivo se ha cargado igualmente (clave desconocida). Sin él, o bien el
    archivo entero se ha sustituido por su configuración anterior, o bien (protocolos) se ha
    descartado el elemento que indica `key`.
    """

    file: str
    key: str
    reason: str
    warning: bool = False


def default_config() -> Config:
    """Configuración con todos los valores predeterminados del código."""
    return Config()


def install_defaults(config_dir: Path) -> list[Path]:
    """Copia a `config_dir` los archivos predeterminados que falten (primer arranque).

    Nunca sobrescribe un archivo existente. Devuelve los archivos creados.
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for name in CONFIG_FILES:
        target = config_dir / name
        if not target.exists():
            shutil.copyfile(DEFAULTS_DIR / name, target)
            created.append(target)
    return created


def load(config_dir: Path, *, previous: Config | None = None) -> tuple[Config, list[ConfigError]]:
    """Carga la configuración de `config_dir`.

    Un archivo inválido conserva la parte de `previous` que le corresponde (los valores
    predeterminados si no hay `previous`) y añade un `ConfigError` a la lista devuelta.
    """
    fallback = previous if previous is not None else default_config()
    values: dict[str, Any] = {}
    errors: list[ConfigError] = []
    for name, attribute, parse in _PARSERS:
        issues: list[ConfigError] = []
        try:
            reader = _Reader(_read_toml(config_dir / name), "", name, issues)
            values[attribute] = parse(reader)
            reader.close()
        except _InvalidError as invalid:
            values[attribute] = getattr(fallback, attribute)
            errors.append(ConfigError(name, invalid.key, invalid.reason))
        else:
            errors.extend(issues)
    return Config(**values), errors


# --- Lectura y validación --------------------------------------------------------------------

_MISSING = object()
_REQUIRED = object()


class _InvalidError(Exception):
    """Valor inválido que invalida el archivo (o el elemento) que lo contiene."""

    def __init__(self, key: str, reason: str) -> None:
        super().__init__(f"{key}: {reason}")
        self.key = key
        self.reason = reason


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        return {}
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise _InvalidError("", f"sintaxis TOML inválida: {error}") from error
    except OSError as error:
        raise _InvalidError("", f"no se puede leer: {error}") from error


class _Reader:
    """Lee las claves de una tabla TOML comprobando su tipo y anota las que sobran."""

    def __init__(
        self, data: Mapping[str, Any], prefix: str, file: str, issues: list[ConfigError]
    ) -> None:
        self._data = data
        self._prefix = prefix
        self._file = file
        self._issues = issues
        self._seen: set[str] = set()

    def key(self, name: str) -> str:
        return f"{self._prefix}.{name}" if self._prefix else name

    def _take(self, name: str, default: object) -> object:
        self._seen.add(name)
        value = self._data.get(name, _MISSING)
        if value is _MISSING and default is _REQUIRED:
            raise _InvalidError(self.key(name), "falta; es obligatoria")
        return value

    def text(
        self,
        name: str,
        default: object = _REQUIRED,
        *,
        choices: frozenset[str] | None = None,
        non_empty: bool = False,
    ) -> Any:
        value = self._take(name, default)
        if value is _MISSING:
            return default
        if not isinstance(value, str):
            raise _InvalidError(self.key(name), "debe ser un texto")
        if choices is not None and value not in choices:
            raise _InvalidError(self.key(name), "debe ser uno de: " + ", ".join(sorted(choices)))
        if non_empty and not value.strip():
            raise _InvalidError(self.key(name), "no puede estar vacío")
        return value

    def boolean(self, name: str, default: object = _REQUIRED) -> Any:
        value = self._take(name, default)
        if value is _MISSING:
            return default
        if not isinstance(value, bool):
            raise _InvalidError(self.key(name), "debe ser un booleano (true o false)")
        return value

    def integer(
        self, name: str, default: object = _REQUIRED, bounds: tuple[float, float] | None = None
    ) -> Any:
        value = self._take(name, default)
        if value is _MISSING:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            raise _InvalidError(self.key(name), "debe ser un entero")
        self._check_bounds(name, value, bounds)
        return value

    def number(
        self, name: str, default: object = _REQUIRED, bounds: tuple[float, float] | None = None
    ) -> Any:
        value = self._take(name, default)
        if value is _MISSING:
            return default
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise _InvalidError(self.key(name), "debe ser un número")
        self._check_bounds(name, value, bounds)
        return float(value)

    def _check_bounds(self, name: str, value: float, bounds: tuple[float, float] | None) -> None:
        if bounds is not None and not bounds[0] <= value <= bounds[1]:
            raise _InvalidError(self.key(name), f"debe estar entre {bounds[0]:g} y {bounds[1]:g}")

    def texts(self, name: str, default: object = (), *, non_empty: bool = False) -> Any:
        value = self._take(name, default)
        if value is _MISSING:
            return default
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise _InvalidError(self.key(name), "debe ser una lista de textos")
        if non_empty and (not value or not all(item.strip() for item in value)):
            raise _InvalidError(self.key(name), "no puede estar vacía ni tener textos vacíos")
        return tuple(value)

    def table(self, name: str) -> "_Reader":
        """Subtabla `name`; una tabla ausente equivale a una vacía."""
        value = self._take(name, None)
        if value is _MISSING:
            value = {}
        if not isinstance(value, dict):
            raise _InvalidError(self.key(name), "debe ser una tabla")
        return _Reader(value, self.key(name), self._file, self._issues)

    def tables(self, name: str, default: object = None) -> "list[_Reader] | None":
        """Lista de tablas `name`, o None si la clave no está."""
        value = self._take(name, default)
        if value is _MISSING:
            return None
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise _InvalidError(self.key(name), "debe ser una lista de tablas")
        return [
            _Reader(item, f"{self.key(name)}[{index}]", self._file, self._issues)
            for index, item in enumerate(value)
        ]

    def items(self) -> list[tuple[str, Any]]:
        """Todas las claves de la tabla, para las tablas de contenido libre."""
        self._seen.update(self._data)
        return list(self._data.items())

    def error(self, key: str, reason: str) -> None:
        """Anota un error que descarta un elemento sin invalidar el archivo."""
        self._issues.append(ConfigError(self._file, key, reason))

    def close(self) -> None:
        """Avisa de las claves que nadie ha leído."""
        for name in self._data:
            if name not in self._seen:
                self._issues.append(
                    ConfigError(self._file, self.key(name), "clave desconocida", warning=True)
                )


def _parse_settings(reader: _Reader) -> Settings:
    sections = {}
    for section in dataclasses.fields(Settings):
        table = reader.table(section.name)
        cls = section.default_factory  # type: ignore[misc]
        values = {}
        for item in dataclasses.fields(cls):  # type: ignore[arg-type]
            rule = _SETTINGS_RULES.get(f"{section.name}.{item.name}")
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


def _parse_catalog(reader: _Reader) -> Catalog:
    discover = reader.boolean("discover_installed_apps", True)
    apps = []
    for item in reader.tables("apps") or []:
        apps.append(
            AppEntry(
                name=item.text("name", non_empty=True),
                path=item.text("path", non_empty=True),
                aliases=item.texts("aliases"),
                args=item.texts("args"),
            )
        )
        item.close()
    pages = []
    for item in reader.tables("pages") or []:
        name = item.text("name", non_empty=True)
        url = item.text("url")
        if not url.startswith(("http://", "https://")):
            raise _InvalidError(item.key("url"), "debe empezar por http:// o https://")
        pages.append(PageEntry(name=name, url=url, aliases=item.texts("aliases")))
        item.close()
    return Catalog(discover_installed_apps=discover, apps=tuple(apps), pages=tuple(pages))


def _text_table(reader: _Reader, name: str) -> dict[str, str]:
    table = reader.table(name)
    result = {}
    for key, value in table.items():
        if not isinstance(value, str) or not value.strip():
            raise _InvalidError(table.key(key), "debe ser un texto no vacío")
        result[key] = value
    return result


def _parse_places(reader: _Reader) -> Mapping[str, Path]:
    places = _text_table(reader, "places")
    return MappingProxyType({name: Path(value).expanduser() for name, value in places.items()})


def _parse_aliases(reader: _Reader) -> Mapping[str, str]:
    return MappingProxyType(_text_table(reader, "aliases"))


def _parse_binaries(reader: _Reader) -> tuple[Binary, ...]:
    items = reader.tables("binaries")
    if items is None:
        return DEFAULT_BINARIES
    binaries = []
    names: set[str] = set()
    for item in items:
        name = item.text("name", non_empty=True)
        if name.casefold() in names:
            raise _InvalidError(item.key("name"), f"el binario «{name}» está repetido")
        names.add(name.casefold())
        binaries.append(
            Binary(
                name=name,
                executable=item.text("executable", non_empty=True),
                aliases=item.texts("aliases"),
                timeout_seconds=item.number("timeout_seconds", None, (1, 3600)),
            )
        )
        item.close()
    return tuple(binaries)


def _parse_structures(reader: _Reader) -> tuple[StructureDef, ...]:
    structures = []
    for item in reader.tables("structures") or []:
        structures.append(
            StructureDef(
                name=item.text("name", non_empty=True),
                folders=item.texts("folders", _REQUIRED, non_empty=True),
            )
        )
        item.close()
    return tuple(structures)


def _parse_protocol(item: _Reader) -> ProtocolDef:
    protocol_id = item.text("id", non_empty=True)
    name = item.text("name", non_empty=True)
    aliases = item.texts("aliases")
    important = item.boolean("important", False)
    tasks = []
    for task in item.tables("tasks", _REQUIRED) or []:
        params = dict(task.table("params").items())
        for key, value in params.items():
            if not isinstance(value, str | int | float | bool):
                raise _InvalidError(
                    task.key(f"params.{key}"), "debe ser un texto, un número o un booleano"
                )
        tasks.append(
            ProtocolTask(
                module=task.text("module", non_empty=True),
                action=task.text("action", non_empty=True),
                params=MappingProxyType(params),
                stop_on_error=task.boolean("stop_on_error", False),
                description=task.text("description", None),
            )
        )
        task.close()
    if not tasks:
        raise _InvalidError(item.key("tasks"), "el protocolo no tiene tareas")
    item.close()
    return ProtocolDef(
        id=protocol_id, name=name, tasks=tuple(tasks), aliases=aliases, important=important
    )


def _parse_protocols(reader: _Reader) -> tuple[ProtocolDef, ...]:
    """Un protocolo no válido se descarta con un error; los demás se cargan."""
    protocols = []
    ids: set[str] = set()
    names: set[str] = set()
    for item in reader.tables("protocols") or []:
        try:
            protocol = _parse_protocol(item)
            if protocol.id in ids:
                raise _InvalidError(item.key("id"), f"el id «{protocol.id}» está repetido")
            for field_name, spoken in [("name", protocol.name)] + [
                ("aliases", alias) for alias in protocol.aliases
            ]:
                if spoken.casefold() in names:
                    raise _InvalidError(item.key(field_name), f"el nombre «{spoken}» está repetido")
        except _InvalidError as invalid:
            reader.error(invalid.key, invalid.reason)
            continue
        ids.add(protocol.id)
        names.update(spoken.casefold() for spoken in (protocol.name, *protocol.aliases))
        protocols.append(protocol)
    return tuple(protocols)


def validate_protocols(
    protocols: Sequence[ProtocolDef], specs_of: Callable[[str, str], Sequence[Any]]
) -> tuple[tuple[ProtocolDef, ...], list[ConfigError]]:
    """Valida cada tarea contra el registro de intenciones (`specs_of(module, action)`, las
    `IntentSpec` registradas de la acción): la acción existe, admite protocolos y tiene sus
    parámetros obligatorios. Un protocolo no válido se descarta con un error; los demás se
    devuelven."""
    valid: list[ProtocolDef] = []
    errors: list[ConfigError] = []
    for position, protocol in enumerate(protocols):
        reason = None
        for number, task in enumerate(protocol.tasks):
            reason = _task_problem(task, specs_of(task.module, task.action))
            if reason is not None:
                key = f"protocols[{position}].tasks[{number}]"
                errors.append(ConfigError("protocols.toml", key, f"{protocol.id}: {reason}"))
                break
        if reason is None:
            valid.append(protocol)
    return tuple(valid), errors


def _task_problem(task: ProtocolTask, specs: Sequence[Any]) -> str | None:
    intent = f"{task.module}.{task.action}"
    if not specs:
        return f"la acción {intent} no existe"
    if not all(spec.in_protocols for spec in specs):
        return f"la acción {intent} no se puede usar en un protocolo"
    # Obligatorio: lo que todas sus formas piden y ninguna fija por sí misma.
    required = set.intersection(*(
        {slot.name for slot in spec.slots if not slot.optional and slot.name not in spec.fixed}
        for spec in specs
    ))  # fmt: skip
    missing = sorted(required - set(task.params))
    if missing:
        return f"a {intent} le falta el parámetro {', '.join(missing)}"
    return None


_PARSERS: tuple[tuple[str, str, Callable[[_Reader], Any]], ...] = (
    ("settings.toml", "settings", _parse_settings),
    ("catalog.toml", "catalog", _parse_catalog),
    ("places.toml", "places", _parse_places),
    ("commands.toml", "binaries", _parse_binaries),
    ("aliases.toml", "aliases", _parse_aliases),
    ("protocols.toml", "protocols", _parse_protocols),
    ("structures.toml", "structures", _parse_structures),
)
