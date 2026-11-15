"""Máquina de estados del asistente (maquina-estados.md, AD-01).

Es pura: `handle` no hace E/S ni lee el reloj; cambia el estado y devuelve los efectos que el
orquestador ejecuta en orden. Las filas de diálogo de la tabla de transiciones (estados
`AWAITING_*` y sus entradas) llegan con el diálogo de varios turnos.
"""
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Literal


class AssistantState(StrEnum):
    DORMIDO = "DORMIDO"
    IDLE = "IDLE"
    LISTENING_COMMAND = "LISTENING_COMMAND"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    AWAITING_PARAMETER = "AWAITING_PARAMETER"


class ControlKind(StrEnum):
    REPOSO = "reposo"
    CERRAR = "cerrar"
    CANCELAR = "cancelar"


class Transition(Enum):
    """Evento del ciclo de vida que acompaña a una frase y se publica al empezar su audio."""

    SESSION_OPENED = "session_opened"
    LISTENING_RESUMED = "listening_resumed"
    REST_ENTERED = "rest_entered"
    SESSION_CLOSED = "session_closed"


# --- Entradas --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Input:
    """Base de las entradas de la máquina de estados."""


@dataclass(frozen=True)
class WakeWord(Input):
    """Frase de activación «Hey Jarvis» escrita por el usuario."""


@dataclass(frozen=True)
class Control(Input):
    """Frase de control reconocida por el enrutador (RN-52)."""

    kind: ControlKind


@dataclass(frozen=True)
class IntentMatched(Input):
    intent: object


@dataclass(frozen=True)
class NoMatch(Input):
    text: str


@dataclass(frozen=True)
class ClosingPhraseInIdle(Input):
    """«Buenas noches Jarvis» escrita en reposo."""


@dataclass(frozen=True)
class SilenceTimeout(Input):
    """Han pasado los segundos sin escribir que llevan a reposo (RF-78)."""


@dataclass(frozen=True)
class NoticeReady(Input):
    notice: object
    reminder: bool = False


@dataclass(frozen=True)
class OpenSessionRequested(Input):
    """«Abrir sesión» de la bandeja, o el arranque con `startup.open_session_on_start`."""


@dataclass(frozen=True)
class ShutdownRequested(Input):
    """Salir desde la bandeja o fin de la sesión del sistema operativo."""


# --- Efectos ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Effect:
    """Base de los efectos que ejecuta el orquestador."""


@dataclass(frozen=True)
class OpenSession(Effect):
    """Crear la sesión nueva (RF-01)."""


@dataclass(frozen=True)
class SayLifecycle(Effect):
    """Decir una frase del ciclo de vida y publicar su evento al empezar el audio (RNF-22)."""

    phrase_id: str
    announces: Transition


@dataclass(frozen=True)
class PublishListeningResumed(Effect):
    silent: bool = False


@dataclass(frozen=True)
class DeliverPendingNotices(Effect):
    """Entregar los avisos que quedaron pendientes sin sesión (RF-41)."""


@dataclass(frozen=True)
class DeliverNotice(Effect):
    notice: object


@dataclass(frozen=True)
class RestartSilenceTimer(Effect):
    """Iniciar o reiniciar la cuenta de inactividad."""


@dataclass(frozen=True)
class StopInterruptibleSpeech(Effect):
    """Callar la locución en curso, si se puede interrumpir (RN-48)."""


@dataclass(frozen=True)
class RunTurn(Effect):
    intent: object


@dataclass(frozen=True)
class PublishUnrecognized(Effect):
    """Publicar la frase como no reconocida (RN-51)."""

    text: str


@dataclass(frozen=True)
class CancelTurn(Effect):
    """Cancelar el turno en curso, si lo hay. `announce`: decir «Cancelado.» si lo había."""

    announce: bool


@dataclass(frozen=True)
class CloseSession(Effect):
    """Cierre de sesión completo. `silent`: sin frase ni animación.

    `reason="voz"` es el cierre pedido por el usuario con la frase de cierre. El valor se
    conserva de cuando la frase se decía: es el que guarda la base de datos.
    """

    reason: Literal["voz", "salida"]
    silent: bool = False


@dataclass(frozen=True)
class ExitProcess(Effect):
    """Terminar el proceso."""


# --- Máquina ---------------------------------------------------------------------------------

_S = AssistantState


class StateMachine:
    """FSM del ciclo de vida. Empieza en `DORMIDO`."""

    def __init__(self, state: AssistantState = AssistantState.DORMIDO) -> None:
        self.state = state

    def handle(self, entry: Input) -> list[Effect]:
        """Aplica `entry` al estado actual y devuelve los efectos, en orden."""
        if self.state is _S.DORMIDO:
            return self._asleep(entry)
        if isinstance(entry, ShutdownRequested):
            self.state = _S.DORMIDO
            return [CloseSession(reason="salida", silent=True), ExitProcess()]
        if entry == Control(ControlKind.CERRAR):
            self.state = _S.DORMIDO
            return [CloseSession(reason="voz")]
        if self.state is _S.IDLE:
            return self._resting(entry)
        if self.state is _S.LISTENING_COMMAND:
            return self._listening(entry)
        return []

    def _asleep(self, entry: Input) -> list[Effect]:
        if isinstance(entry, WakeWord | OpenSessionRequested):
            self.state = _S.LISTENING_COMMAND
            return [
                OpenSession(),
                SayLifecycle("ciclo.apertura", Transition.SESSION_OPENED),
                DeliverPendingNotices(),
                RestartSilenceTimer(),
            ]
        if isinstance(entry, ShutdownRequested):
            return [ExitProcess()]
        return []

    def _resting(self, entry: Input) -> list[Effect]:
        if isinstance(entry, WakeWord):
            self.state = _S.LISTENING_COMMAND
            return [
                SayLifecycle("ciclo.escucha", Transition.LISTENING_RESUMED),
                RestartSilenceTimer(),
            ]
        if isinstance(entry, ClosingPhraseInIdle):
            self.state = _S.DORMIDO
            return [CloseSession(reason="voz")]
        if isinstance(entry, IntentMatched | NoMatch):
            # Cualquier texto despierta en silencio y se atiende como en escucha.
            self.state = _S.LISTENING_COMMAND
            return [PublishListeningResumed(silent=True), *self._listening(entry)]
        if isinstance(entry, NoticeReady) and entry.reminder:
            self.state = _S.LISTENING_COMMAND
            return [
                PublishListeningResumed(silent=True),
                DeliverNotice(entry.notice),
                RestartSilenceTimer(),
            ]
        return []

    def _listening(self, entry: Input) -> list[Effect]:
        if isinstance(entry, IntentMatched):
            return [RunTurn(entry.intent)]
        if isinstance(entry, NoMatch):
            return [PublishUnrecognized(entry.text), RestartSilenceTimer()]
        if isinstance(entry, WakeWord):
            return [StopInterruptibleSpeech(), RestartSilenceTimer()]
        if entry == Control(ControlKind.CANCELAR):
            return [CancelTurn(announce=True)]
        if entry == Control(ControlKind.REPOSO) or isinstance(entry, SilenceTimeout):
            self.state = _S.IDLE
            return [
                CancelTurn(announce=False),
                SayLifecycle("ciclo.reposo", Transition.REST_ENTERED),
            ]
        return []
