"""Interfaz común de los módulos de acción (arquitectura.md, sección 5; RNF-18, RNF-19).

Es lo único que un módulo conoce del resto del sistema. Las subtareas e `invoke` son para el
módulo Protocolos.
"""
from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
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


# Recurso compartido entre módulos: el directorio de trabajo (RN-14). Las acciones declaran
# los recursos que leen y que cambian; el planificador usa esa declaración para decidir qué
# tareas pueden ejecutarse a la vez (`core/task_queue.py`).
WORKDIR = "workdir"

# Motivo de una tarea que termina sin hacer nada porque el usuario la ha cancelado (RN-52).
CANCELLED_REASON = "cancelada"
# Motivo de una tarea que no llega a ejecutarse porque la sesión se cierra (RN-46).
CLOSED_REASON = "sesión cerrada"
# Clave de `metadata` en `ctx.ask`: la pregunta es un ofrecimiento («¿Se los dicto?»). Si se
# cancela o se agota el tiempo, no se dice «Operación cancelada.»: no había nada en marcha.
OFFER = "oferta"


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
    # Ocupa el turno: mientras se ejecuta, ninguna otra orden empieza (un protocolo, RN-55).
    exclusive: bool = False
    # Parámetros que fija el propio patrón («busca el archivo…» fija el tipo).
    fixed: Mapping[str, object] = field(default_factory=dict)
    # Recursos compartidos que la acción lee y que cambia, además de los que se deducen de
    # sus entidades (`resources_read`). Una tarea espera a las anteriores que cambian algo
    # que ella usa; las demás se ejecutan en paralelo con las de otros módulos.
    reads: frozenset[str] = frozenset()
    writes: frozenset[str] = frozenset()

    @property
    def resources_read(self) -> frozenset[str]:
        """Lo declarado en `reads` más lo que leen sus entidades al resolverse: una ruta se
        resuelve respecto al directorio de trabajo y un elemento de catálogo, en su lista."""
        found = set(self.reads)
        for slot in self.slots:
            if slot.type is SlotType.DIR_PATH:
                found.add(WORKDIR)
            elif slot.type is SlotType.CATALOG and slot.catalog:
                found.add(slot.catalog)
        return frozenset(found)


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
    # Motivo que se muestra bajo la tarea en `error`; sin él, el texto de `speech`.
    detail: str | None = None
    # Se llama cuando el asistente termina de decir la respuesta, también si se ha cortado;
    # si no hay nada que decir, al terminar la tarea. Recordatorio: el plazo de RN-29.
    on_spoken: Callable[[], None] | None = field(default=None, compare=False)

    @classmethod
    def cancelled(
        cls, speech: Phrase | None = None, description: str | None = None
    ) -> "ActionResult":
        """La tarea termina en `error` con el motivo «cancelada» (RN-19, RN-52)."""
        return cls("error", speech, description, detail=CANCELLED_REASON)


class ExpectedType(Enum):
    """Qué respuesta espera una pregunta (maquina-estados.md, «Contexto de diálogo»)."""

    BOOLEAN = "boolean"  # sí / no → AWAITING_CONFIRMATION
    NEW_FILENAME = "new_filename"  # un nombre de archivo o carpeta → AWAITING_PARAMETER
    DATETIME = "datetime"  # una fecha y hora → AWAITING_PARAMETER
    REMINDER_ACTION = "reminder_action"  # «otro aviso …» / «fecha límite …» / «no»


@dataclass(frozen=True)
class ReminderAction:
    """Respuesta a `REMINDER_ACTION` distinta de «no»: «otro aviso {fecha}» (`aviso`) o
    «fecha límite {fecha}» (`limite`). La fecha aún no se ha comprobado que sea futura."""

    kind: Literal["aviso", "limite"]
    when: datetime


@dataclass(frozen=True)
class DialogueAnswer:
    """Respuesta a `ctx.ask`. `cancelled`: «cancelar», tiempo agotado o respuesta no válida
    dos veces. Si no, `value` ya está validado: `bool` para `BOOLEAN`, `str` para
    `NEW_FILENAME`, `datetime` para `DATETIME` (sin comprobar que sea futura),
    `ReminderAction` o `False` para `REMINDER_ACTION`. Una negación es `value=False`, no una
    cancelación."""

    cancelled: bool
    value: object | None = None


@dataclass(frozen=True)
class Subtask:
    """Tarea hija creada con `ctx.subtask`: queda en `pendiente` hasta que se ejecuta con
    `ctx.invoke(..., subtask=...)` o hasta que `fail(motivo)` la deja en `error`."""

    id: int
    fail: Callable[[str], None] = field(compare=False)


# Ejecuta otra acción por la interfaz común, con `run_task`, como subtarea de la tarea actual.
# `invoke(module, action, params, *, quiet=True, subtask=None, description=None,
# resolve=False)`. Con `quiet`, la respuesta de voz solo se dice si es un error; con
# `resolve`, los parámetros llegan como texto y se resuelven en este momento, como las
# entidades de una orden escrita (`IntentRouter.resolve_params`).
Invoke = Callable[..., Awaitable[ActionResult]]


def _no_subtasks(*_args: object, **_kwargs: object) -> Subtask:
    raise RuntimeError("Este contexto no admite subtareas")


async def _no_invoke(*_args: object, **_kwargs: object) -> ActionResult:
    raise RuntimeError("Este contexto no puede invocar otras acciones")


# Pregunta al usuario y espera su respuesta sin bloquear (RES-21, RES-22).
# `ask(question, expected_type, *, metadata=None, subject=None)`. `subject`: el elemento sobre
# el que se pregunta, para la interfaz; `metadata`: los datos de la operación en pausa.
Ask = Callable[..., Awaitable[DialogueAnswer]]


async def _no_dialogue(*_args: object, **_kwargs: object) -> DialogueAnswer:
    """Sin nadie a quien preguntar, la pregunta se cancela."""
    return DialogueAnswer(cancelled=True)


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
    # La respuesta solo se dice si es un error: el resultado ya se ve en la ventana que
    # pidió la acción.
    quiet: bool = field(default=False, compare=False)

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
    # Añade una frase a la respuesta de la tarea. La respuesta completa se dice seguida,
    # cuando le llega el turno en la cola de voz: no se mezcla con la de otra tarea.
    say: Callable[[Phrase], Awaitable[object]]
    publish: "Callable[[Event], None]"  # publica un evento de contenido para su panel
    notify: "Callable[[Notice], None]"  # encola un aviso
    # Deja la tarea en segundo plano: al terminar la corrutina, su resultado fija el estado
    # de la tarea y su frase se entrega como aviso (RN-39).
    background: Callable[[Coroutine[Any, Any, ActionResult]], None]
    task_id: int | None = None
    scheduler: Any = None  # `core/scheduler.py`: trabajos a una fecha
    ask: Ask = _no_dialogue
    # El panel destacado de la interfaz: el último `PanelActivated` (RN-25).
    active_panel: str | None = None
    # Solo los usa el módulo Protocolos. `subtask(module, description)` crea una tarea hija en
    # `pendiente`; `invoke` ejecuta una acción como subtarea (ver `Invoke`).
    subtask: Callable[[str, str], Subtask] = _no_subtasks
    invoke: Invoke = _no_invoke


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
#       Acciones del usuario en la interfaz que ejecutan una acción del módulo. Para las
#       acciones de las ventanas basta el evento genérico `ActionRequested`.
