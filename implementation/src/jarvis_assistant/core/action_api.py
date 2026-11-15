"""Interfaz común de los módulos de acción (arquitectura.md, sección 5; RNF-18, RNF-19).

Es lo único que un módulo conoce del resto del sistema. El diálogo (`ask`), las subtareas y
`invoke` llegan con el diálogo de varios turnos y con los protocolos.
"""
from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from jarvis_assistant.config import Config
    from jarvis_assistant.core.clock import Clock
    from jarvis_assistant.core.database import Database
    from jarvis_assistant.core.events import Event
    from jarvis_assistant.core.notices import Notice
    from jarvis_assistant.core.repositories import SessionRow
    from jarvis_assistant.core.workdir import Workdir


class SlotType(Enum):
    TEXT = "text"  # texto libre
    DIR_PATH = "dir_path"  # carpeta existente (resolución de rutas)
    NEW_NAME = "new_name"  # nombre de archivo o carpeta que se va a crear
    NEW_PATH = "new_path"  # ruta anidada que se va a crear ("a barra b")
    INTEGER = "integer"  # número, en cifras o en letras
    DURATION = "duration"  # "diez minutos", "media hora"
    DATETIME = "datetime"  # "mañana a las nueve"
    CATALOG = "catalog"  # un elemento de una lista conocida (difuso)
    COMMAND_LINE = "command_line"  # binario permitido + argumentos


@dataclass(frozen=True)
class Slot:
    name: str
    type: SlotType
    catalog: str | None = None  # para CATALOG: nombre del catálogo registrado
    optional: bool = False


@dataclass(frozen=True)
class IntentSpec:
    action: str
    patterns: tuple[str, ...]
    slots: tuple[Slot, ...] = ()
    description: str = ""  # para la ayuda
    example: str = ""  # para la ayuda
    panel: str | None = None  # panel que se activa al ejecutarla
    in_protocols: bool = True  # invocable como tarea de protocolo
    # Parámetros que fija el propio patrón («busca el archivo…» fija el tipo).
    fixed: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Phrase:
    """Frase del catálogo `speaker/phrases.py` con sus parámetros."""

    id: str
    params: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    status: Literal["completado", "error"]
    speech: Phrase | None = None
    description: str | None = None  # sustituye la descripción de la tarea
    background: bool = False  # la tarea sigue pendiente (arquitectura.md, sección 4, regla 4)


@dataclass(frozen=True)
class CommandLine:
    """Entidad `COMMAND_LINE` resuelta: un binario permitido y sus argumentos (RN-45)."""

    name: str
    executable: str
    args: tuple[str, ...] = ()
    timeout_seconds: float | None = None  # None = commands.default_timeout_seconds

    @property
    def text(self) -> str:
        return " ".join((self.name, *self.args))


@dataclass(frozen=True)
class Intent:
    """Intención reconocida, con sus entidades ya resueltas y con tipo.

    `error` es la frase del tipo de la entidad que no se pudo resolver: la tarea se crea en
    `error` con ella. `description` es la descripción inicial de la tarea.
    """

    module: str
    action: str
    params: Mapping[str, object] = field(default_factory=dict)
    error: Phrase | None = None
    description: str = field(default="", compare=False)
    panel: str | None = field(default=None, compare=False)

    @property
    def key(self) -> str:
        return f"{self.module}.{self.action}"


@dataclass(frozen=True)
class HelpEntry:
    description: str
    example: str


@dataclass(frozen=True)
class HelpGroup:
    module: str
    title: str
    entries: tuple[HelpEntry, ...]


@dataclass
class ActionContext:
    """Lo que un módulo recibe en cada llamada."""

    session: "SessionRow | None"
    origin: Literal["voz", "protocolo"]
    workdir: "Workdir"
    clock: "Clock"
    config: "Config"
    db: "Database"
    platform: Any
    places: Mapping[str, Path]
    say: Callable[[Phrase], Awaitable[object]]  # dice una frase intermedia
    publish: "Callable[[Event], None]"  # publica un evento de contenido para su panel
    notify: "Callable[[Notice], None]"  # encola un aviso
    # Deja la tarea en segundo plano: al terminar la corrutina, su resultado fija el estado
    # de la tarea y su frase se entrega como aviso (RN-39).
    background: Callable[[Coroutine[Any, Any, ActionResult]], None]
    task_id: int | None = None
    scheduler: Any = None


class ActionModule(Protocol):
    name: str  # clave estable; es `module_name` en la base de datos
    title: str  # para la interfaz

    def intents(self) -> Sequence[IntentSpec]: ...

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult: ...


# Miembros opcionales de un módulo:
#   async def on_session_opened(self, ctx) / on_session_closed(self, ctx)
#   def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]
#       Catálogos para las entidades `CATALOG`. Cada uno es una lista de fuentes, por orden
#       de prioridad: gana la primera con una coincidencia que supere el umbral.
#   def user_actions(self) -> Mapping[type[Event], Callable[[Event], tuple[str, Mapping]]]
#       Acciones del usuario en la interfaz que ejecutan una acción del módulo.
