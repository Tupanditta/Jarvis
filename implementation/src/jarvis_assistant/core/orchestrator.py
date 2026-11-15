"""Bucle de turnos: une la entrada escrita, el enrutador, la FSM, los módulos y la voz
(maquina-estados.md; arquitectura.md, sección 4).

Vive en el hilo del núcleo y es el único dueño del estado. Consume entradas de una cola y
ejecuta, en orden, los efectos que devuelve la FSM. Cada orden se atiende como un turno, una
tarea `asyncio`: así las frases de control se atienden aunque haya una orden en curso (RN-44,
RN-52). `run_task` es la única función que ejecuta acciones (AD-13). El diálogo llega con su
fase.
"""
import asyncio
import logging
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from jarvis_assistant.config import Config, ConfigError
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.action_api import ActionContext, ActionResult, Intent, Phrase
from jarvis_assistant.core.clock import Clock, TimerHandle
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.notices import Notice, NoticeQueue
from jarvis_assistant.core.repositories import ActivityRepository, SessionRow
from jarvis_assistant.core.state_machine import AssistantState, StateMachine, Transition
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router.router import (
    CORE_MODULE,
    HELP,
    HIDE_SCREEN,
    REPEAT,
    SHOW_SCREEN,
    IntentRouter,
)
from jarvis_assistant.speaker.phrases import render
from jarvis_assistant.speaker.speaker import Speaker

logger = logging.getLogger(__name__)

LEVEL_INTERVAL_SECONDS = 0.05  # 20 Hz (AD-14)
CANCELLED_REASON = "cancelada"  # RN-52
CLOSED_REASON = "sesión cerrada"  # RN-46
HELP_PANEL = "ayuda"

_ACTIVITY_OF_STATE = {
    AssistantState.DORMIDO: Activity.DORMIDO,
    AssistantState.IDLE: Activity.REPOSO,
    AssistantState.LISTENING_COMMAND: Activity.ESCUCHANDO,
    AssistantState.AWAITING_CONFIRMATION: Activity.ESPERANDO,
    AssistantState.AWAITING_PARAMETER: Activity.ESPERANDO,
}

Origin = Literal["voz", "protocolo"]
Reload = Callable[[Config], tuple[Config, Sequence[ConfigError]]]


class Sessions(Protocol):
    def open_session(self) -> SessionRow: ...
    def close_session(self, reason: str) -> None: ...


@dataclass(frozen=True)
class _SilenceElapsed:
    token: int


@dataclass(frozen=True)
class _TurnDone:
    turn: asyncio.Task


@dataclass(frozen=True)
class _Poke:
    """Hay algo nuevo que entregar (un aviso): el bucle debe mirar."""


@dataclass(frozen=True)
class _UserAction:
    """Acción del usuario en la interfaz que ejecuta una acción de un módulo."""

    module: str
    action: str
    params: Mapping[str, object]


@dataclass
class _Task:
    """Tarea registrada: lo que hace falta para publicar su estado."""

    id: int
    parent: int | None
    module: str
    description: str
    reason: str = CANCELLED_REASON  # motivo si se cancela mientras sigue en segundo plano


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
        database: Database,
        platform: Any,
        workdir: Workdir,
        modules: Sequence[Any] = (),
        reload_config: Reload | None = None,
        on_exit: Callable[[], None] = lambda: None,
    ) -> None:
        self._machine = machine
        self._bus = bus
        self._clock = clock
        self._config = config
        self._router = router
        self._speaker = speaker
        self._sessions = sessions
        self._database = database
        self._platform = platform
        self._workdir = workdir
        self._reload_config = reload_config
        self._on_exit = on_exit
        self._activities = ActivityRepository(database)

        self._queue: asyncio.Queue[object] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stopping = False
        self._session: SessionRow | None = None
        self._published: tuple[str, Activity] | None = None
        self._silence_timer: TimerHandle | None = None
        self._silence_token = 0
        self._level_timer: TimerHandle | None = None

        self._modules: dict[str, Any] = {}
        self._panels: dict[tuple[str, str], str | None] = {}
        self._turn: asyncio.Task | None = None
        self._executing = 0  # acciones en ejecución: la actividad es «procesando»
        self._waiting: str | None = None  # la orden que espera a que acabe el turno (RN-44)
        self._notices = NoticeQueue()
        self._background: dict[asyncio.Task, _Task] = {}
        self._places: dict[str, Path] = {}

        for module in modules:
            self._register(module)
        self._apply_config(config)

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

    @property
    def modules(self) -> Mapping[str, Any]:
        return self._modules

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
                self._pump()
            except Exception:
                logger.exception("Error al atender %s", type(entry).__name__)
            finally:
                self._queue.task_done()
                self._refresh()

    async def idle(self) -> None:
        """Espera a que no queden entradas por atender."""
        await self._queue.join()

    # --- Registro de módulos -----------------------------------------------------------------

    def _register(self, module: Any) -> None:
        """Añade un módulo de acción: sus intenciones al enrutador y sus acciones aquí."""
        self._router.register(module)
        self._modules[module.name] = module
        for spec in module.intents():
            self._panels.setdefault((module.name, spec.action), spec.panel)
        for event_type, to_action in getattr(module, "user_actions", dict)().items():
            self._bus.subscribe(
                event_type,
                lambda event, name=module.name, to_action=to_action: self.submit(
                    _UserAction(name, *to_action(event))
                ),
            )

    def _apply_config(self, config: Config) -> None:
        self._config = config
        self._places = {**self._platform.default_places(), **config.places}
        self._router.configure(
            config.settings.router, config.aliases, binaries=config.binaries, places=self._places
        )

    # --- Entradas ----------------------------------------------------------------------------

    async def _dispatch(self, entry: object) -> None:
        if isinstance(entry, events.TextSubmitted):
            await self._on_text(entry.text)
        elif isinstance(entry, events.UserTyping):
            self._restart_silence_timer()  # teclear cuenta como actividad
        elif isinstance(entry, _SilenceElapsed):
            await self._on_silence(entry)
        elif isinstance(entry, _TurnDone):
            self._on_turn_done(entry.turn)
        elif isinstance(entry, _UserAction):
            await self._on_user_action(entry)
        elif isinstance(entry, _Poke):
            pass  # `_pump` hace el resto
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
        if isinstance(entry, fsm.IntentMatched) and self._turn_active():
            # Un turno a la vez: como máximo una orden espera; las demás se descartan.
            if self._waiting is None:
                self._waiting = text
            else:
                logger.info("Orden descartada: ya hay una en espera")
            return
        recognized = fsm.Control | fsm.ClosingPhraseInIdle | fsm.WakeWord | fsm.IntentMatched
        if isinstance(entry, recognized):
            logger.info("Frase reconocida: %s", type(entry).__name__)
            self._bus.publish(events.CommandReceived(text, recognized=True))
        await self._handle(entry)

    async def _on_user_action(self, entry: _UserAction) -> None:
        if self._session is None or self._turn_active():
            logger.info("Acción %s.%s ignorada", entry.module, entry.action)
            return
        intent = Intent(
            entry.module, entry.action, entry.params,
            description=entry.action.replace("_", " "),
            panel=self._panels.get((entry.module, entry.action)),
        )  # fmt: skip
        await self._handle(fsm.IntentMatched(intent))

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
                await self._open_session()
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
            case fsm.RunTurn(intent=intent):
                if isinstance(intent, Intent):
                    self._start_turn(self._run_intent(intent))
                else:
                    logger.warning("Intención desconocida: %r", intent)
                    self._restart_silence_timer()
            case fsm.CancelTurn(announce=announce):
                await self._cancel(announce)
            case fsm.DeliverNotice(notice=notice):
                if isinstance(notice, Notice):
                    self._start_turn(self._deliver(notice))
            case fsm.DeliverPendingNotices():
                pass  # los entrega `_pump` cuando termina la frase de apertura

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

    # --- Sesión ------------------------------------------------------------------------------

    async def _open_session(self) -> None:
        self._reload()
        self._session = self._sessions.open_session()
        self._workdir.reset()  # RN-14
        self._speaker.open_output()
        await self._session_hook("on_session_opened")

    def _reload(self) -> None:
        """Relee la configuración (RF-96). Un archivo inválido conserva su versión anterior;
        el aviso se da tras la frase de apertura."""
        if self._reload_config is None:
            return
        try:
            config, errors = self._reload_config(self._config)
        except Exception:
            logger.exception("No se ha podido recargar la configuración")
            return
        self._apply_config(config)
        reported: set[str] = set()
        for error in errors:
            if error.warning:
                logger.warning("Configuración: %s, %s: %s", error.file, error.key, error.reason)
                continue
            logger.error("Configuración: %s, clave %s: %s", error.file, error.key, error.reason)
            self._bus.publish(events.ConfigReloadFailed(error.file, error.reason))
            if error.file not in reported:
                reported.add(error.file)
                self._notices.add(
                    Notice(Phrase("config.error", {"archivo": Path(error.file).stem}))
                )

    async def _close_session(self, reason: str, silent: bool) -> None:
        self._cancel_silence_timer()
        await self._cancel_turn()
        await self._cancel_background(CLOSED_REASON)  # RN-46
        self._speaker.stop()
        await self._session_hook("on_session_closed")
        self._notices.clear()
        self._sessions.close_session(reason)
        self._session = None
        if silent:
            self._bus.publish(events.SessionClosed())
        else:
            await self._say_lifecycle("ciclo.cierre", Transition.SESSION_CLOSED)
        if self._machine.state is AssistantState.DORMIDO:  # no se ha abierto otra entretanto
            self._speaker.close_output()

    async def _session_hook(self, name: str) -> None:
        ctx = self._context("voz", None)
        for module in self._modules.values():
            hook = getattr(module, name, None)
            if hook is None:
                continue
            try:
                await hook(ctx)
            except Exception:
                logger.exception("%s de %s ha fallado", name, module.name)

    # --- Turnos ------------------------------------------------------------------------------

    def _turn_active(self) -> bool:
        return self._turn is not None and not self._turn.done()

    def _start_turn(self, body: Coroutine[Any, Any, object]) -> None:
        async def turn() -> None:
            try:
                await body
            except asyncio.CancelledError:
                raise
            except Exception:  # RNF-23: un turno que falla no bloquea al asistente
                logger.exception("El turno ha fallado")

        self._cancel_silence_timer()  # la cuenta de inactividad no corre durante el turno
        task = asyncio.ensure_future(turn())
        self._turn = task
        task.add_done_callback(lambda done: self._queue.put_nowait(_TurnDone(done)))

    def _on_turn_done(self, turn: asyncio.Task) -> None:
        if self._turn is turn:
            self._turn = None
        self._restart_silence_timer()  # la cuenta empieza al terminar la respuesta

    def _pump(self) -> None:
        """Con el asistente libre: atiende la orden en espera o entrega el siguiente aviso."""
        if self._stopping or self._session is None or self._turn_active():
            return
        state = self._machine.state
        if state is AssistantState.LISTENING_COMMAND:
            if self._waiting is not None:
                text, self._waiting = self._waiting, None
                self._queue.put_nowait(events.TextSubmitted(text))
                return
            notice = self._notices.pop()
            if notice is not None:
                self._start_turn(self._deliver(notice))
        elif state is AssistantState.IDLE:
            # Un aviso de recordatorio pone al asistente en escucha; los demás esperan (RN-39).
            reminder = self._notices.pop_reminder()
            if reminder is not None:
                self._queue.put_nowait(fsm.NoticeReady(reminder, reminder=True))

    async def _cancel_turn(self) -> bool:
        """Cancela el turno en curso y la orden en espera. True si había turno."""
        self._waiting = None
        turn = self._turn
        if turn is None or turn.done():
            return False
        self._speaker.stop()
        turn.cancel()
        await asyncio.gather(turn, return_exceptions=True)
        if self._turn is turn:
            self._turn = None
        return True

    async def _cancel(self, announce: bool) -> None:
        """`CancelTurn`. Con `announce` es «cancelar»: también detiene lo que sigue en segundo
        plano y, si había algo que cancelar, dice «Cancelado.»."""
        cancelled = await self._cancel_turn()
        if not announce:
            return
        if self._background:
            await self._cancel_background(CANCELLED_REASON)
            cancelled = True
        if cancelled:
            self._start_turn(self._say(Phrase("general.cancelado")))

    async def _run_intent(self, intent: Intent) -> None:
        if intent.module == CORE_MODULE:
            await self._run_core(intent)
        else:
            await self.run_task(
                intent.module, intent.action, intent.params, origin="voz",
                description=intent.description, error=intent.error,
            )  # fmt: skip

    async def _run_core(self, intent: Intent) -> None:
        """Intenciones del núcleo: no son tareas de ningún módulo de acción."""
        if intent in (SHOW_SCREEN, HIDE_SCREEN):
            # Sin voz: solo la interfaz cambia (catalogo-intenciones.md, sección 2).
            self._bus.publish(events.ShowScreenRequested(visible=intent == SHOW_SCREEN))
        elif intent == HELP:
            self._bus.publish(events.HelpShown(self._router.help()))
            self._bus.publish(events.PanelActivated(HELP_PANEL))
            await self._say(Phrase("general.ayuda"))
        elif intent == REPEAT:
            await self._say(self._speaker.last_phrase or Phrase("general.nada_que_repetir"))
        else:
            logger.warning("Intención del núcleo desconocida: %s", intent.key)

    async def _deliver(self, notice: Notice) -> None:
        if notice.panel is not None:
            self._bus.publish(events.PanelActivated(notice.panel))
        await self._say(notice.phrase)
        if notice.on_delivered is not None:
            notice.on_delivered()

    async def _say(self, phrase: Phrase) -> None:
        try:
            await self._speaker.say(phrase)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("No se ha podido decir %s", phrase.id)

    def _notify(self, notice: Notice) -> None:
        self._notices.add(notice)
        self._queue.put_nowait(_Poke())

    # --- Tareas ------------------------------------------------------------------------------

    async def run_task(
        self,
        module: str,
        action: str,
        params: Mapping[str, object],
        *,
        origin: Origin = "voz",
        parent: int | None = None,
        description: str | None = None,
        error: Phrase | None = None,
        quiet: bool = False,
    ) -> ActionResult:
        """Ejecuta una acción como tarea: la registra en `pendiente`, llama al módulo, captura
        cualquier excepción (RNF-23), fija el estado final y dice la respuesta.

        `error`: una entidad no se pudo resolver; la tarea se crea ya en `error` con esa frase.
        Con `quiet`, la respuesta solo se dice si es un error.
        """
        session = self._session
        if session is None:
            raise RuntimeError("No hay sesión abierta")
        task = _Task(
            self._activities.add(
                session.id, module, description or f"{module} {action}", self._clock.now(), parent
            ),
            parent, module, description or f"{module} {action}",
        )  # fmt: skip
        self._publish_task(task, "pendiente")
        panel = self._panels.get((module, action))
        if panel is not None:
            self._bus.publish(events.PanelActivated(panel))
        self._executing += 1
        self._refresh()
        try:
            if error is not None:
                result = ActionResult("error", error)
            else:
                ctx = self._context(origin, task)
                result = await self._modules[module].execute(action, params, ctx)
        except asyncio.CancelledError:
            self._finish_task(task, "error", CANCELLED_REASON)
            raise
        except Exception:
            logger.exception("La acción %s.%s ha fallado", module, action)
            result = ActionResult("error", Phrase("general.error"))
        finally:
            self._executing -= 1
            self._refresh()
        if result.description:
            task.description = result.description
        if result.background and result.status == "completado":
            self._publish_task(task, "pendiente")  # sigue en segundo plano
        else:
            self._finish_task(task, result.status, self._detail(result))
        if result.speech is not None and not (quiet and result.status == "completado"):
            await self._say(result.speech)
        return result

    def _context(self, origin: Origin, task: _Task | None) -> ActionContext:
        def background(work: Coroutine[Any, Any, ActionResult]) -> None:
            if task is None:
                work.close()
                raise RuntimeError("Solo una tarea puede seguir en segundo plano")
            self._spawn_background(task, work)

        return ActionContext(
            session=self._session,
            origin=origin,
            workdir=self._workdir,
            clock=self._clock,
            config=self._config,
            db=self._database,
            platform=self._platform,
            places=self._places,
            say=self._say,
            publish=self._bus.publish,
            notify=self._notify,
            background=background,
            task_id=None if task is None else task.id,
        )

    @staticmethod
    def _detail(result: ActionResult) -> str | None:
        """Motivo que se muestra bajo una tarea en `error`: su frase."""
        if result.status != "error" or result.speech is None:
            return None
        try:
            return render(result.speech)
        except Exception:
            return None

    def _publish_task(self, task: _Task, status: str, detail: str | None = None) -> None:
        self._bus.publish(
            events.TaskUpdated(
                task.id, task.parent, task.module, task.description,
                status,  # type: ignore[arg-type]
                detail, self._clock.now().astimezone(),
            )
        )

    def _finish_task(self, task: _Task, status: str, detail: str | None = None) -> None:
        self._activities.finish(task.id, status, task.description, self._clock.now())
        self._publish_task(task, status, detail)

    # --- Tareas en segundo plano -------------------------------------------------------------

    def _spawn_background(self, task: _Task, work: Coroutine[Any, Any, ActionResult]) -> None:
        job = asyncio.ensure_future(work)
        self._background[job] = task
        job.add_done_callback(self._background_done)

    def _background_done(self, job: asyncio.Task) -> None:
        """El trabajo en segundo plano ha terminado: su resultado fija el estado de la tarea
        y su frase se entrega como aviso cuando el asistente quede libre (RN-39)."""
        task = self._background.pop(job, None)
        if task is None:
            return
        if job.cancelled():
            self._finish_task(task, "error", task.reason)
            return
        if job.exception() is not None:
            logger.error("La tarea en segundo plano ha fallado", exc_info=job.exception())
            result = ActionResult("error", Phrase("general.error"))
        else:
            result = job.result()
        if result.description:
            task.description = result.description
        self._finish_task(task, result.status, self._detail(result))
        if result.speech is not None:
            self._notify(Notice(result.speech))

    async def _cancel_background(self, reason: str) -> None:
        jobs = list(self._background)
        for job in jobs:
            self._background[job].reason = reason
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        for job in jobs:
            self._background_done(job)

    # --- Cuenta de inactividad ---------------------------------------------------------------

    def _restart_silence_timer(self) -> None:
        self._cancel_silence_timer()
        if self._machine.state is not AssistantState.LISTENING_COMMAND or self._turn_active():
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
        if self._speaker.speaking:
            activity = Activity.HABLANDO
        elif self._executing:
            activity = Activity.PROCESANDO
        else:
            activity = _ACTIVITY_OF_STATE[state]
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
