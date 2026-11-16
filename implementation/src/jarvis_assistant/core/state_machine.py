"""Máquina de estados del asistente (maquina-estados.md, AD-01).

Es pura: `handle` no hace E/S ni lee el reloj; cambia el estado y devuelve los efectos que el
orquestador ejecuta en orden. Incluye las filas de diálogo: un módulo pregunta con `ctx.ask`,
la FSM pasa a `AWAITING_*` y el orquestador resuelve la pregunta con lo que la FSM decida.
"""
import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Literal

from jarvis_assistant.core.action_api import ExpectedType, Phrase


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


@dataclass(eq=False)
class DialogueContext:
    """La pregunta en curso. Solo hay una: los diálogos se piden de uno en uno."""

    question: Phrase
    expected_type: ExpectedType
    metadata: Mapping[str, object] = field(default_factory=dict)  # la operación en pausa
    timeout_seconds: float = 20.0
    # Se resuelve con la `DialogueAnswer`; equivale al `pending_callback`.
    continuation: "asyncio.Future | None" = None
    subject: Mapping[str, object] | None = None  # el elemento sobre el que se pregunta
    attempts: int = 0  # respuestas no válidas recibidas

    @property
    def confirmation(self) -> bool:
        return self.expected_type is ExpectedType.BOOLEAN


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
class WindowPressed(Input):
    """El usuario ha pulsado una ventana flotante (moverla, cambiar su tamaño o un control)."""


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


@dataclass(frozen=True)
class DialogueRequested(Input):
    """Un módulo ha llamado a `ctx.ask(…)`."""

    dialogue: DialogueContext


@dataclass(frozen=True)
class Answer(Input):
    """Texto escrito en `AWAITING_*`, ya validado por el enrutador contra el tipo esperado.
    `valid=False`: no es una respuesta admitida; `value` no cuenta."""

    value: object = None
    valid: bool = True


@dataclass(frozen=True)
class DialogueTimeout(Input):
    """Han pasado los segundos de espera sin respuesta (RN-38)."""


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


@dataclass(frozen=True)
class OpenDialogue(Effect):
    """Publicar `DialogueOpened`, decir la pregunta e iniciar el tiempo de espera al
    terminarla."""

    dialogue: DialogueContext


@dataclass(frozen=True)
class RejectDialogue(Effect):
    """La pregunta llega cuando no se puede atender (sin escucha): se resuelve como cancelada,
    sin voz ni eventos."""

    dialogue: DialogueContext


@dataclass(frozen=True)
class RepeatQuestion(Effect):
    """Decir «No le he entendido.» y repetir la pregunta; reiniciar el tiempo de espera."""


@dataclass(frozen=True)
class RestartDialogueTimer(Effect):
    """Reiniciar el tiempo de espera de la pregunta, si ya ha empezado a correr."""


@dataclass(frozen=True)
class ResolveDialogue(Effect):
    """Resolver la pregunta con la respuesta y publicar `DialogueClosed(answered)`. El módulo
    continúa su turno."""

    value: object


@dataclass(frozen=True)
class CancelDialogue(Effect):
    """Resolver la pregunta como cancelada y publicar `DialogueClosed(cancelled)`.
    `announce`: decir «Operación cancelada.». `by_user`: el usuario ha dicho «cancelar» (no
    es tiempo agotado ni respuesta no válida)."""

    announce: bool
    by_user: bool = False


# --- Máquina ---------------------------------------------------------------------------------

_S = AssistantState


class StateMachine:
    """FSM del ciclo de vida. Empieza en `DORMIDO`."""

    def __init__(self, state: AssistantState = AssistantState.DORMIDO) -> None:
        self.state = state
        self._dialogue: DialogueContext | None = None

    @property
    def dialogue(self) -> DialogueContext | None:
        """La pregunta en curso, en `AWAITING_*`."""
        return self._dialogue

    def handle(self, entry: Input) -> list[Effect]:
        """Aplica `entry` al estado actual y devuelve los efectos, en orden."""
        if self.state is _S.DORMIDO:
            return self._asleep(entry)
        if isinstance(entry, ShutdownRequested):
            self.state, self._dialogue = _S.DORMIDO, None
            return [CloseSession(reason="salida", silent=True), ExitProcess()]
        if entry == Control(ControlKind.CERRAR):
            self.state, self._dialogue = _S.DORMIDO, None
            return [CloseSession(reason="voz")]
        if self.state is _S.IDLE:
            return self._resting(entry)
        if self.state is _S.LISTENING_COMMAND:
            return self._listening(entry)
        return self._awaiting(entry)

    def _asleep(self, entry: Input) -> list[Effect]:
        if isinstance(entry, DialogueRequested):
            return [RejectDialogue(entry.dialogue)]
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
        if isinstance(entry, DialogueRequested):
            return [RejectDialogue(entry.dialogue)]
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
        if isinstance(entry, WindowPressed):
            # Tocar una ventana flotante también despierta en silencio.
            self.state = _S.LISTENING_COMMAND
            return [PublishListeningResumed(silent=True), RestartSilenceTimer()]
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
        if isinstance(entry, WindowPressed):
            return [RestartSilenceTimer()]  # usar las ventanas cuenta como actividad
        if entry == Control(ControlKind.CANCELAR):
            return [CancelTurn(announce=True)]
        if entry == Control(ControlKind.REPOSO) or isinstance(entry, SilenceTimeout):
            self.state = _S.IDLE
            return [
                CancelTurn(announce=False),
                SayLifecycle("ciclo.reposo", Transition.REST_ENTERED),
            ]
        if isinstance(entry, DialogueRequested):
            dialogue = entry.dialogue
            dialogue.attempts = 0
            self.state = (
                _S.AWAITING_CONFIRMATION if dialogue.confirmation else _S.AWAITING_PARAMETER
            )
            self._dialogue = dialogue
            return [OpenDialogue(dialogue)]
        return []

    def _awaiting(self, entry: Input) -> list[Effect]:
        """`AWAITING_CONFIRMATION` y `AWAITING_PARAMETER`."""
        dialogue = self._dialogue
        if isinstance(entry, Answer):
            if entry.valid:
                return self._close_dialogue(ResolveDialogue(entry.value))
            if dialogue is not None and dialogue.attempts == 0:
                dialogue.attempts += 1
                return [RepeatQuestion()]
            return self._close_dialogue(CancelDialogue(announce=True))
        if isinstance(entry, DialogueTimeout):
            return self._close_dialogue(CancelDialogue(announce=True))
        if entry == Control(ControlKind.CANCELAR):
            return self._close_dialogue(CancelDialogue(announce=True, by_user=True))
        if isinstance(entry, WakeWord):
            return [RestartDialogueTimer()]
        if entry == Control(ControlKind.REPOSO):
            self._dialogue = None
            self.state = _S.IDLE
            return [
                CancelDialogue(announce=False),
                CancelTurn(announce=False),
                SayLifecycle("ciclo.reposo", Transition.REST_ENTERED),
            ]
        if isinstance(entry, DialogueRequested):
            return [RejectDialogue(entry.dialogue)]  # nunca dos preguntas a la vez
        return []  # los avisos esperan en su cola (RN-39); las órdenes no se atienden

    def _close_dialogue(self, effect: Effect) -> list[Effect]:
        self._dialogue = None
        self.state = _S.LISTENING_COMMAND
        return [effect]
