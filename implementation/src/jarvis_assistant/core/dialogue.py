"""Diálogo con el usuario: la pregunta abierta, su tiempo de espera y su respuesta
(arquitectura.md, sección 6; maquina-estados.md).

Un módulo pregunta con `ctx.ask`. La pregunta entra en el bucle del núcleo como
`DialogueRequested` y la FSM pasa a `AWAITING_*`; lo que se escribe entonces es la respuesta y
la corrutina del módulo sigue cuando la FSM la resuelve. Como varias órdenes pueden ir a la vez,
las preguntas se hacen de una en una: la segunda espera a que se resuelva la primera.

El tiempo de espera empieza a correr cuando termina de decirse la pregunta. Al vencer, entra en
el bucle como `DialogueElapsed`; uno de una pregunta anterior ya no vale.

Lo usa solo el orquestador, que ejecuta los efectos de la FSM.
"""
import asyncio
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.action_api import DialogueAnswer, ExpectedType, Phrase
from jarvis_assistant.core.announcer import Announcement, Announcer
from jarvis_assistant.core.clock import Clock, TimerHandle
from jarvis_assistant.core.event_bus import EventBus

logger = logging.getLogger(__name__)

# Respuestas admitidas que la interfaz muestra con cada tipo de pregunta.
HINTS: Mapping[ExpectedType, tuple[str, ...]] = {
    ExpectedType.BOOLEAN: ("Sí", "No", "Cancelar"),
    ExpectedType.NEW_FILENAME: ("Otro nombre", "Cancelar"),
    ExpectedType.DATETIME: ("Una fecha", "Cancelar"),
    ExpectedType.REMINDER_ACTION: ("Otro aviso", "Fecha límite", "No"),
    ExpectedType.SESSION_IDS: ("1, 3, 5", "1-5", "Cancelar"),
}


@dataclass(frozen=True)
class DialogueElapsed:
    """Ha vencido el tiempo de espera de la pregunta `token`."""

    token: int


class Dialogues:
    """La pregunta abierta y su temporizador.

    `submit`: pone una entrada en el bucle del núcleo. `awaiting`: la FSM espera una
    respuesta. `announce`: pone frases en la cola de voz. `render`: texto de una frase.
    """

    def __init__(
        self,
        *,
        bus: EventBus,
        clock: Clock,
        announcer: Announcer,
        submit: Callable[[object], None],
        awaiting: Callable[[], bool],
        announce: Callable[..., None],
        render: Callable[[Phrase], str],
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._announcer = announcer
        self._submit = submit
        self._awaiting = awaiting
        self._announce = announce
        self._render = render
        self._dialogue: fsm.DialogueContext | None = None
        self._lock = asyncio.Lock()
        self._timer: TimerHandle | None = None
        self._token = 0
        self._armed = False  # el tiempo de espera ya corre: la pregunta se ha dicho

    @property
    def current(self) -> fsm.DialogueContext | None:
        return self._dialogue

    def elapsed(self, entry: DialogueElapsed) -> bool:
        """El vencimiento es de la pregunta abierta y la FSM sigue esperando."""
        return entry.token == self._token and self._awaiting()

    async def ask(
        self,
        question: Phrase,
        expected_type: ExpectedType,
        timeout_seconds: float,
        *,
        metadata: Mapping[str, object] | None = None,
        subject: Mapping[str, object] | None = None,
        speech: list[Phrase] | None = None,
    ) -> DialogueAnswer:
        """`ctx.ask`: pregunta y espera la respuesta sin bloquear el bucle. Lo que la tarea
        llevaba dicho se dice antes de la pregunta."""
        async with self._lock:
            if speech:
                self._announce(*speech)
                speech.clear()
            dialogue = fsm.DialogueContext(
                question, expected_type, dict(metadata or {}), timeout_seconds,
                asyncio.get_running_loop().create_future(), subject,
            )  # fmt: skip
            self._submit(fsm.DialogueRequested(dialogue))
            answer = await dialogue.continuation  # type: ignore[misc]
            logger.info("Diálogo resuelto: %s", "cancelado" if answer.cancelled else "respuesta")
            return answer

    def open(self, dialogue: fsm.DialogueContext) -> None:
        """`OpenDialogue`: publica la pregunta y la dice; el tiempo de espera empieza al
        terminar de decirla."""
        self._dialogue = dialogue
        self._cancel_timer()
        try:
            text = self._render(dialogue.question)
        except Exception:
            logger.exception("Pregunta sin frase: %s", dialogue.question.id)
            text = ""
        self._bus.publish(
            events.DialogueOpened(
                text, dialogue.expected_type.name, HINTS.get(dialogue.expected_type, ()),
                dialogue.timeout_seconds, dialogue.subject,
            )
        )  # fmt: skip
        self._speak(dialogue.question)

    def ask_again(self) -> None:
        """Respuesta no válida, primera vez: «No le he entendido.» (o «No he entendido la
        fecha.» si se esperaba una) y la pregunta otra vez."""
        if self._dialogue is not None:
            reason = (
                Phrase("entidad.fecha")
                if self._dialogue.expected_type is ExpectedType.DATETIME
                else Phrase("general.no_entendido")
            )
            self._speak(reason, self._dialogue.question)

    def restart_timer(self) -> None:
        """`RestartDialogueTimer`: vuelve a contar, si ya contaba."""
        if self._armed:
            self._arm_timer()

    def close(self, answer: DialogueAnswer, outcome: events.DialogueOutcome) -> None:
        """Resuelve la pregunta abierta, si la hay, y publica `DialogueClosed`."""
        dialogue, self._dialogue = self._dialogue, None
        self._cancel_timer()
        if dialogue is None:
            return
        settle(dialogue, answer)
        self._bus.publish(events.DialogueClosed(outcome))

    # --- Internos ---

    def _speak(self, *phrases: Phrase) -> None:
        self._cancel_timer()
        self._announcer.submit(Announcement(phrases, on_delivered=self._question_said))

    def _question_said(self) -> None:
        if self._dialogue is not None and self._awaiting():
            self._arm_timer()

    def _arm_timer(self) -> None:
        self._cancel_timer()
        if self._dialogue is None:
            return
        self._armed = True
        token = self._token
        self._timer = self._clock.call_later(
            self._dialogue.timeout_seconds, lambda: self._submit(DialogueElapsed(token))
        )

    def _cancel_timer(self) -> None:
        self._token += 1
        self._armed = False
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.cancel()


def settle(dialogue: fsm.DialogueContext, answer: DialogueAnswer) -> None:
    """Entrega la respuesta a la corrutina que pregunta, si sigue esperando."""
    future = dialogue.continuation
    if future is not None and not future.done():
        future.set_result(answer)
