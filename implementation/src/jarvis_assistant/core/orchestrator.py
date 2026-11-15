"""Bucle de turnos: une la entrada escrita, el enrutador, la FSM y la voz (maquina-estados.md).

Vive en el hilo del núcleo y es el único dueño del estado. Consume entradas de una cola y
ejecuta, en orden, los efectos que devuelve la FSM. La ejecución de acciones (`run_task`), el
diálogo y la entrega de avisos llegan con sus fases.
"""
import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from jarvis_assistant.config import Config
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.core.clock import Clock, TimerHandle
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.repositories import SessionRow
from jarvis_assistant.core.state_machine import AssistantState, StateMachine, Transition
from jarvis_assistant.intent_router.router import HIDE_SCREEN, SHOW_SCREEN, IntentRouter
from jarvis_assistant.speaker.speaker import Speaker

logger = logging.getLogger(__name__)

LEVEL_INTERVAL_SECONDS = 0.05  # 20 Hz (AD-14)

_ACTIVITY_OF_STATE = {
    AssistantState.DORMIDO: Activity.DORMIDO,
    AssistantState.IDLE: Activity.REPOSO,
    AssistantState.LISTENING_COMMAND: Activity.ESCUCHANDO,
    AssistantState.AWAITING_CONFIRMATION: Activity.ESPERANDO,
    AssistantState.AWAITING_PARAMETER: Activity.ESPERANDO,
}


class Sessions(Protocol):
    def open_session(self) -> SessionRow: ...
    def close_session(self, reason: str) -> None: ...


@dataclass(frozen=True)
class _SilenceElapsed:
    token: int


class Orchestrator:
    def __init__(
        self,
        *,
        machine: StateMachine,
        bus: EventBus,
        clock: Clock,
        config: Config,
        router: IntentRouter,
        speaker: Speaker,
        sessions: Sessions,
        on_exit: Callable[[], None] = lambda: None,
    ) -> None:
        self._machine = machine
        self._bus = bus
        self._clock = clock
        self._config = config
        self._router = router
        self._speaker = speaker
        self._sessions = sessions
        self._on_exit = on_exit

        self._queue: asyncio.Queue[object] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stopping = False
        self._session: SessionRow | None = None
        self._published: tuple[str, Activity] | None = None
        self._silence_timer: TimerHandle | None = None
        self._silence_token = 0
        self._level_timer: TimerHandle | None = None

        bus.subscribe(
            events.OpenSessionRequested, lambda _e: self.submit(fsm.OpenSessionRequested())
        )
        bus.subscribe(events.QuitRequested, lambda _e: self.submit(fsm.ShutdownRequested()))
        bus.subscribe(events.TextSubmitted, self.submit)
        bus.subscribe(events.UserTyping, self.submit)
        bus.subscribe(events.SpeechStarted, lambda _e: self._refresh())
        bus.subscribe(events.SpeechFinished, lambda _e: self._refresh())

    @property
    def state(self) -> AssistantState:
        return self._machine.state

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def submit(self, entry: object) -> None:
        """Encola una entrada. Segura desde cualquier hilo."""
        loop = self._loop
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if loop is None or running is loop:
            self._queue.put_nowait(entry)
            return
        try:
            loop.call_soon_threadsafe(self._queue.put_nowait, entry)
        except RuntimeError:
            logger.debug("%s descartada: el núcleo ya no está en marcha", type(entry).__name__)

    async def run(self) -> None:
        """Consume entradas y ejecuta efectos hasta que la FSM pide terminar el proceso."""
        self._loop = asyncio.get_running_loop()
        self._refresh()
        while not self._stopping:
            entry = await self._queue.get()
            try:
                await self._dispatch(entry)
            except Exception:
                logger.exception("Error al atender %s", type(entry).__name__)
            finally:
                self._queue.task_done()
                self._refresh()

    async def idle(self) -> None:
        """Espera a que no queden entradas por atender."""
        await self._queue.join()

    # --- Entradas ----------------------------------------------------------------------------

    async def _dispatch(self, entry: object) -> None:
        if isinstance(entry, events.TextSubmitted):
            await self._on_text(entry.text)
        elif isinstance(entry, events.UserTyping):
            self._restart_silence_timer()  # teclear cuenta como actividad
        elif isinstance(entry, _SilenceElapsed):
            await self._on_silence(entry)
        elif isinstance(entry, fsm.Input):
            await self._handle(entry)
        else:
            logger.warning("Entrada desconocida: %r", entry)

    async def _on_text(self, text: str) -> None:
        if not text.strip():
            return
        entry = self._router.route(text, self._machine.state)
        if entry is None:
            return
        recognized = fsm.Control | fsm.ClosingPhraseInIdle | fsm.WakeWord | fsm.IntentMatched
        if isinstance(entry, recognized):
            logger.info("Frase reconocida: %s", type(entry).__name__)
            self._bus.publish(events.CommandReceived(text, recognized=True))
        await self._handle(entry)

    async def _on_silence(self, elapsed: _SilenceElapsed) -> None:
        if elapsed.token != self._silence_token:
            return
        if self._machine.state is not AssistantState.LISTENING_COMMAND:
            return
        await self._handle(fsm.SilenceTimeout())

    async def _handle(self, entry: fsm.Input) -> None:
        before = self._machine.state
        effects = self._machine.handle(entry)
        after = self._machine.state
        if after is not before:
            logger.info("Estado: %s → %s (%s)", before, after, type(entry).__name__)
            if after is not AssistantState.LISTENING_COMMAND:
                self._cancel_silence_timer()
        for effect in effects:
            await self._execute(effect)

    # --- Efectos -----------------------------------------------------------------------------

    async def _execute(self, effect: fsm.Effect) -> None:
        match effect:
            case fsm.OpenSession():
                self._session = self._sessions.open_session()
                self._speaker.open_output()
            case fsm.SayLifecycle(phrase_id=phrase_id, announces=transition):
                await self._say_lifecycle(phrase_id, transition)
            case fsm.PublishListeningResumed(silent=silent):
                self._bus.publish(events.ListeningResumed(silent=silent))
            case fsm.RestartSilenceTimer():
                self._restart_silence_timer()
            case fsm.StopInterruptibleSpeech():
                self._speaker.stop()
            case fsm.PublishUnrecognized(text=text):
                if text.strip():
                    self._bus.publish(events.CommandReceived(text, recognized=False))
            case fsm.CloseSession(reason=reason, silent=silent):
                await self._close_session(reason, silent)
            case fsm.ExitProcess():
                self._stopping = True
                self._on_exit()
            case fsm.RunTurn(intent=intent) if intent in (SHOW_SCREEN, HIDE_SCREEN):
                # Sin voz: solo la interfaz cambia (catalogo-intenciones.md, sección 2).
                self._bus.publish(events.ShowScreenRequested(visible=intent == SHOW_SCREEN))
                self._restart_silence_timer()
            case fsm.RunTurn():
                logger.warning("No hay módulos de acción registrados: la orden se ignora")
                self._restart_silence_timer()
            case fsm.CancelTurn() | fsm.DeliverPendingNotices() | fsm.DeliverNotice():
                pass  # no hay turnos ni avisos hasta que existan módulos de acción

    async def _say_lifecycle(self, phrase_id: str, transition: Transition) -> None:
        announced = False

        def announce() -> None:
            nonlocal announced
            if not announced:
                announced = True
                logger.debug("Inicio de la transición %s: %.3f", transition.name,
                             self._clock.monotonic())
                self._bus.publish(self._transition_event(transition))

        await self._speaker.say(Phrase(phrase_id), lifecycle=True, on_start=announce)
        announce()  # si la frase no llegó a sonar, la transición se publica igualmente

    def _transition_event(self, transition: Transition) -> events.Event:
        if transition is Transition.SESSION_OPENED:
            session = self._session
            assert session is not None
            return events.SessionOpened(session.id, session.name)
        if transition is Transition.LISTENING_RESUMED:
            return events.ListeningResumed()
        if transition is Transition.REST_ENTERED:
            return events.RestEntered()
        return events.SessionClosed()

    async def _close_session(self, reason: str, silent: bool) -> None:
        self._cancel_silence_timer()
        self._speaker.stop()
        self._sessions.close_session(reason)
        self._session = None
        if silent:
            self._bus.publish(events.SessionClosed())
        else:
            await self._say_lifecycle("ciclo.cierre", Transition.SESSION_CLOSED)
        if self._machine.state is AssistantState.DORMIDO:  # no se ha abierto otra entretanto
            self._speaker.close_output()

    # --- Cuenta de inactividad ---------------------------------------------------------------

    def _restart_silence_timer(self) -> None:
        self._cancel_silence_timer()
        if self._machine.state is not AssistantState.LISTENING_COMMAND:
            return
        token = self._silence_token
        self._silence_timer = self._clock.call_later(
            self._config.settings.input.inactivity_to_idle_seconds,
            lambda: self._queue.put_nowait(_SilenceElapsed(token)),
        )

    def _cancel_silence_timer(self) -> None:
        self._silence_token += 1
        timer, self._silence_timer = self._silence_timer, None
        if timer is not None:
            timer.cancel()

    # --- Actividad y nivel de audio ----------------------------------------------------------

    def _refresh(self) -> None:
        """Publica la actividad si ha cambiado y mantiene el temporizador del nivel."""
        state = self._machine.state
        activity = Activity.HABLANDO if self._speaker.speaking else _ACTIVITY_OF_STATE[state]
        current = (state.value, activity)
        if current != self._published:
            self._published = current
            self._bus.publish(events.AssistantActivityChanged(state.value, activity))
        if self._level_timer is None and self._level_source() != "none":
            self._schedule_level()

    def _level_source(self) -> events.AudioSource:
        return "assistant" if self._speaker.speaking else "none"

    def _schedule_level(self) -> None:
        self._level_timer = self._clock.call_later(LEVEL_INTERVAL_SECONDS, self._publish_level)

    def _publish_level(self) -> None:
        self._level_timer = None
        source = self._level_source()
        level = self._speaker.current_level() if source == "assistant" else 0.0
        self._bus.publish(events.AudioLevel(min(1.0, max(0.0, level)), source))
        if source != "none" and not self._stopping:
            self._schedule_level()
