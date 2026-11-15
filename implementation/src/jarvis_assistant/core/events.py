"""Eventos del bus (bus-eventos.md).

Todos son `dataclass` inmutables y la suscripción es por clase. El bus no guarda eventos:
la interfaz reconstruye su estado solo con los que recibe.

Este módulo contiene los eventos del ciclo de vida, de estado, de órdenes, de voz, de diálogo,
de tareas, el panel activo y las acciones del usuario; los de contenido de cada panel se añaden
con los módulos que los publican.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal


@dataclass(frozen=True)
class Event:
    """Base de todos los eventos del bus."""


class Activity(StrEnum):
    """Lo que el usuario ve que hace el asistente. Informativa: no es un estado de la FSM."""

    DORMIDO = "dormido"
    REPOSO = "reposo"
    ESCUCHANDO = "escuchando"  # atiende las órdenes escritas
    PROCESANDO = "procesando"
    HABLANDO = "hablando"
    ESPERANDO = "esperando"


AudioSource = Literal["assistant", "none"]
_AUDIO_SOURCES = ("assistant", "none")


# --- Ciclo de vida y estado ------------------------------------------------------------------


@dataclass(frozen=True)
class SessionOpened(Event):
    """Se ha abierto una sesión: la interfaz muestra la pantalla con la animación de despertar."""

    session_id: int
    name: str


@dataclass(frozen=True)
class ListeningResumed(Event):
    """El asistente vuelve de reposo a escucha. `silent`: sin la frase «Le escucho»."""

    silent: bool = False


@dataclass(frozen=True)
class RestEntered(Event):
    """El asistente pasa a reposo; la interfaz sigue visible."""


@dataclass(frozen=True)
class SessionClosed(Event):
    """La sesión se ha cerrado; al terminar la animación, la interfaz se oculta."""


@dataclass(frozen=True)
class AssistantActivityChanged(Event):
    """Nuevo estado de la FSM (por su nombre) y actividad visible."""

    state: str
    activity: Activity


@dataclass(frozen=True)
class AudioLevel(Event):
    """Nivel de audio (0-1) de la voz del asistente, a 20 Hz."""

    level: float
    source: AudioSource

    def __post_init__(self) -> None:
        if not 0.0 <= self.level <= 1.0:
            raise ValueError(f"El nivel de audio debe estar entre 0 y 1: {self.level}")
        if self.source not in _AUDIO_SOURCES:
            raise ValueError(f"Origen de audio desconocido: {self.source!r}")


# --- Sesión ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionChanged(Event):
    """Datos de la sesión actual: al abrirla y cada vez que cambian."""

    session_id: int
    name: str
    is_important: bool


# --- Órdenes y voz ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandReceived(Event):
    """Texto de una orden escrita. `recognized=False`: frase no reconocida (RN-51)."""

    text: str
    recognized: bool


@dataclass(frozen=True)
class SpeechStarted(Event):
    """El asistente empieza a decir `text`. `interruptible`: no es del ciclo de vida."""

    text: str
    interruptible: bool


@dataclass(frozen=True)
class SpeechFinished(Event):
    interrupted: bool


# --- Diálogo, tareas y paneles ---------------------------------------------------------------

TaskStatus = Literal["pendiente", "error", "completado"]
TASK_STATUSES = ("pendiente", "error", "completado")
DialogueOutcome = Literal["answered", "cancelled"]


@dataclass(frozen=True)
class DialogueOpened(Event):
    """El asistente ha hecho una pregunta. `hints`: respuestas admitidas que se muestran."""

    question: str
    expected_type: str
    hints: tuple[str, ...]
    timeout_seconds: float
    subject: Mapping[str, object] | None = None


@dataclass(frozen=True)
class DialogueClosed(Event):
    outcome: DialogueOutcome


@dataclass(frozen=True)
class TaskUpdated(Event):
    """Único evento de estado de tarea (RN-01). `parent_id`: la tarea del protocolo, si la hay."""

    task_id: int
    parent_id: int | None
    module: str
    description: str
    status: TaskStatus
    detail: str | None
    at: datetime

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError(f"Estado de tarea desconocido: {self.status!r}")


@dataclass(frozen=True)
class PanelActivated(Event):
    """`panel` pasa a ser el panel activo de la interfaz."""

    panel: str


# --- Acciones del usuario (interfaz → núcleo, con `publish_threadsafe`) ----------------------


@dataclass(frozen=True)
class TextSubmitted(Event):
    """El usuario ha enviado `text` desde la caja de texto."""

    text: str


@dataclass(frozen=True)
class UserTyping(Event):
    """El usuario está tecleando en la caja de texto; como mucho, una vez por segundo."""


@dataclass(frozen=True)
class SilenceRequested(Event):
    """Botón de silencio: calla la locución en curso."""


@dataclass(frozen=True)
class OpenSessionRequested(Event):
    """«Abrir sesión» en el menú de la bandeja."""


@dataclass(frozen=True)
class ShowScreenRequested(Event):
    """«Mostrar pantalla» en el menú de la bandeja."""

    visible: bool = True


@dataclass(frozen=True)
class QuitRequested(Event):
    """«Salir» en el menú de la bandeja o fin de la sesión del sistema operativo."""
