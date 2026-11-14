"""Eventos del bus (bus-eventos.md).

Todos son `dataclass` inmutables y la suscripción es por clase. El bus no guarda eventos:
la interfaz reconstruye su estado solo con los que recibe.

Este módulo contiene los eventos del ciclo de vida, de estado, de voz y las acciones del
usuario; los de diálogo, tareas y paneles se añaden con los componentes que los publican.
"""
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


@dataclass(frozen=True)
class Event:
    """Base de todos los eventos del bus."""


class Activity(StrEnum):
    """Lo que el usuario ve que hace el asistente. Informativa: no es un estado de la FSM."""

    DORMIDO = "dormido"
    REPOSO = "reposo"
    ESCUCHANDO = "escuchando"
    PROCESANDO = "procesando"
    HABLANDO = "hablando"
    ESPERANDO = "esperando"


AudioSource = Literal["mic", "assistant", "none"]
_AUDIO_SOURCES = ("mic", "assistant", "none")


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
class MicStatusChanged(Event):
    """El micrófono ha pasado a estar disponible o no disponible."""

    available: bool


@dataclass(frozen=True)
class AudioLevel(Event):
    """Nivel de audio (0-1) del micrófono o de la voz del asistente, a 20 Hz."""

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


# --- Voz -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptReady(Event):
    """Texto de una orden transcrita. `recognized=False`: frase no reconocida (RN-51)."""

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


# --- Acciones del usuario (interfaz → núcleo, con `publish_threadsafe`) ----------------------


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
