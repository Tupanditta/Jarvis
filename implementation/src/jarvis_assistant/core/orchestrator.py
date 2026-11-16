"""Bucle de turnos: une la entrada escrita, el enrutador, la FSM, los módulos y la voz
(maquina-estados.md; arquitectura.md, sección 4).

Vive en el hilo del núcleo y es el único dueño del estado. Consume entradas de una cola y
ejecuta, en orden, los efectos que devuelve la FSM.

Un mensaje puede traer varias órdenes separadas por `--`. Cada orden entra en la cola de
órdenes (`task_queue.py`), que decide cuándo puede empezar: las de módulos distintos se
ejecutan a la vez y las del mismo módulo, o las que dependen de un recurso que otra cambia,
en su orden. Cada orden se ejecuta en su propia tarea `asyncio`: así las frases de control se
atienden aunque haya órdenes en curso (RN-52). Las respuestas no se dicen dentro de la orden:
van a la cola de voz (`announcer.py`), que las dice de una en una en el orden en que terminan.

`run_task` es la única función que ejecuta acciones (AD-13). Un protocolo ejecuta sus tareas
con `ctx.invoke`, que también pasa por `run_task`, como subtareas de la suya.

Diálogo: un módulo pregunta con `ctx.ask`. La pregunta entra como `DialogueRequested` y la
FSM pasa a `AWAITING_*`; lo que se escribe entonces es la respuesta, y la corrutina del módulo
sigue cuando la FSM la resuelve. Como varias órdenes pueden ir a la vez, las preguntas se hacen
de una en una: la segunda espera a que se resuelva la primera.
"""
import asyncio
import dataclasses
import logging
from collections.abc import Callable, Coroutine, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from jarvis_assistant.config import Config, ConfigError, validate_protocols
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.action_api import (
    CANCELLED_REASON,
    CLOSED_REASON,
    OFFER,
    ActionContext,
    ActionResult,
    DialogueAnswer,
    ExpectedType,
    Intent,
    IntentSpec,
    Phrase,
    Subtask,
)
from jarvis_assistant.core.announcer import Announcement, Announcer
from jarvis_assistant.core.clock import Clock, TimerHandle
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.notices import Notice, NoticeQueue
from jarvis_assistant.core.repositories import ActivityRepository, SessionRow
from jarvis_assistant.core.state_machine import AssistantState, StateMachine, Transition
from jarvis_assistant.core.task_queue import Claim, Job, TaskQueue
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router.batch import split_orders
from jarvis_assistant.intent_router.router import (
    ASIDE_WINDOW,
    ASIDE_WINDOWS,
    CORE_MODULE,
    HELP,
    HIDE_SCREEN,
    REPEAT,
    RESTORE_WINDOW,
    RESTORE_WINDOWS,
    SHOW_SCREEN,
    IntentRouter,
    Order,
    ParamError,
)
from jarvis_assistant.speaker.phrases import render
from jarvis_assistant.speaker.speaker import Speaker

logger = logging.getLogger(__name__)

LEVEL_INTERVAL_SECONDS = 0.05  # 20 Hz (AD-14)
HELP_PANEL = "ayuda"

_ACTIVITY_OF_STATE = {
    AssistantState.DORMIDO: Activity.DORMIDO,
    AssistantState.IDLE: Activity.REPOSO,
    AssistantState.LISTENING_COMMAND: Activity.ESCUCHANDO,
    AssistantState.AWAITING_CONFIRMATION: Activity.ESPERANDO,
    AssistantState.AWAITING_PARAMETER: Activity.ESPERANDO,
}

# Respuestas admitidas que la interfaz muestra con cada tipo de pregunta.
HINTS: Mapping[ExpectedType, tuple[str, ...]] = {
    ExpectedType.BOOLEAN: ("Sí", "No", "Cancelar"),
    ExpectedType.NEW_FILENAME: ("Otro nombre", "Cancelar"),
    ExpectedType.DATETIME: ("Una fecha", "Cancelar"),
    ExpectedType.REMINDER_ACTION: ("Otro aviso", "Fecha límite", "No"),
}

_AWAITING = (AssistantState.AWAITING_CONFIRMATION, AssistantState.AWAITING_PARAMETER)

Origin = Literal["voz", "protocolo"]
Reload = Callable[[Config], tuple[Config, Sequence[ConfigError]]]


class Sessions(Protocol):
    def open_session(self) -> SessionRow: ...
    def close_session(self, reason: str) -> None: ...


@dataclass(frozen=True)
class _SilenceElapsed:
    token: int


@dataclass(frozen=True)
class _DialogueElapsed:
    token: int


@dataclass
class _Work:
    """Orden en la cola: su texto y, cuando empieza, su intención y la tarea que la ejecuta.

    Una orden escrita llega como `order` y se resuelve al empezar; una acción pedida desde
    una ventana llega ya como `intent`.
    """

    text: str
    order: Order | None = None
    intent: Intent | None = None
    runner: asyncio.Task | None = None


@dataclass(frozen=True)
class _JobDone:
    job: Job[_Work]


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
        scheduler: Any = None,
    ) -> None:
        """`scheduler`: trabajos a una fecha (`core/scheduler.py`), para los módulos."""
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
        self._scheduler = scheduler
        self._activities = ActivityRepository(database)
        self._active_panel: str | None = None  # el último `PanelActivated`

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
        self._jobs: TaskQueue[_Work] = TaskQueue()
        self._queued: tuple[str, ...] = ()  # lo último publicado en `OrderQueueChanged`
        self._announcer = Announcer(
            self._say, speaker.stop, on_idle=lambda: self._queue.put_nowait(_Poke())
        )
        self._executing = 0  # acciones en ejecución: la actividad es «procesando»
        self._notices = NoticeQueue()
        self._background: dict[asyncio.Task, _Task] = {}
        self._unrun: dict[int, _Task] = {}  # subtareas creadas que aún no se han ejecutado
        # Motivo de las tareas que se cancelan: «cancelada», o «sesión cerrada» al cerrar.
        self._cancel_reason = CANCELLED_REASON
        self._places: dict[str, Path] = {}
        # Diálogo: la pregunta abierta, el turno para preguntar y su tiempo de espera, que
        # empieza a correr (`armed`) cuando termina de decirse la pregunta.
        self._dialogue: fsm.DialogueContext | None = None
        self._dialogue_lock = asyncio.Lock()
        self._dialogue_timer: TimerHandle | None = None
        self._dialogue_token = 0
        self._dialogue_armed = False

        for module in modules:
            self._register(module)
        for error in self._apply_config(config):
            logger.error("Configuración: %s, clave %s: %s", error.file, error.key, error.reason)

        bus.subscribe(
            events.OpenSessionRequested, lambda _e: self.submit(fsm.OpenSessionRequested())
        )
        bus.subscribe(events.QuitRequested, lambda _e: self.submit(fsm.ShutdownRequested()))
        bus.subscribe(events.TextSubmitted, self.submit)
        bus.subscribe(events.UserTyping, self.submit)
        bus.subscribe(events.WindowPressed, lambda _e: self.submit(fsm.WindowPressed()))
        bus.subscribe(
            events.ActionRequested,
            lambda e: self.submit(_UserAction(e.module, e.action, e.params)),
        )
        # El botón de silencio calla la respuesta en curso y las que esperaban su turno.
        bus.subscribe(events.SilenceRequested, lambda _e: self._announcer.clear())
        bus.subscribe(events.PanelActivated, self._panel_activated)
        bus.subscribe(events.SpeechStarted, lambda _e: self._refresh())
        bus.subscribe(events.SpeechFinished, lambda _e: self._refresh())

    @property
    def state(self) -> AssistantState:
        return self._machine.state

    @property
    def modules(self) -> Mapping[str, Any]:
        return self._modules

    def _panel_activated(self, event: events.PanelActivated) -> None:
        self._active_panel = event.panel

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

    def _apply_config(self, config: Config) -> list[ConfigError]:
        """Aplica la configuración. Los protocolos se validan contra el registro de
        intenciones: uno no válido se descarta con un error y los demás se cargan."""
        protocols, errors = validate_protocols(config.protocols, self._router.specs_of)
        if len(protocols) != len(config.protocols):
            config = dataclasses.replace(config, protocols=protocols)
        self._config = config
        self._places = {**self._platform.default_places(), **config.places}
        self._router.configure(
            config.settings.router, config.aliases, binaries=config.binaries, places=self._places
        )
        return errors

    # --- Entradas ----------------------------------------------------------------------------

    async def _dispatch(self, entry: object) -> None:
        if isinstance(entry, events.TextSubmitted):
            await self._on_text(entry.text)
        elif isinstance(entry, events.UserTyping):
            self._restart_silence_timer()  # teclear cuenta como actividad
        elif isinstance(entry, _SilenceElapsed):
            await self._on_silence(entry)
        elif isinstance(entry, _DialogueElapsed):
            if entry.token == self._dialogue_token and self._machine.state in _AWAITING:
                await self._handle(fsm.DialogueTimeout())
        elif isinstance(entry, _JobDone):
            self._jobs.finish(entry.job)
        elif isinstance(entry, _UserAction):
            await self._on_user_action(entry)
        elif isinstance(entry, _Poke):
            pass  # `_pump` hace el resto
        elif isinstance(entry, fsm.Input):
            await self._handle(entry)
        else:
            logger.warning("Entrada desconocida: %r", entry)

    async def _on_text(self, text: str) -> None:
        if self._machine.state in _AWAITING:
            await self._on_answer(text)
            return
        orders = split_orders(text)
        if len(orders) > 1:
            await self._on_batch(orders)
            return
        if not orders:
            return
        if orders[0] != text.strip():
            text = orders[0]  # un separador suelto al principio o al final no cuenta
        entry = self._router.route(text, self._machine.state, resolve=False)
        if entry is None:
            return
        recognized = fsm.Control | fsm.ClosingPhraseInIdle | fsm.WakeWord | fsm.IntentMatched
        if isinstance(entry, recognized):
            logger.info("Frase reconocida: %s", type(entry).__name__)
            if not _changes_state(entry):
                self._bus.publish(events.CommandReceived(text, recognized=True))
        await self._handle(entry)

    async def _on_answer(self, text: str) -> None:
        """En espera, el mensaje entero es la respuesta (o una frase de control)."""
        if not text.strip():
            return
        entry = self._router.route(text, self._machine.state, self._machine.dialogue)
        if entry is None:
            return
        recognized = not isinstance(entry, fsm.Answer) or entry.valid
        if not _changes_state(entry):
            self._bus.publish(events.CommandReceived(text.strip(), recognized=recognized))
        await self._handle(entry)

    async def _on_batch(self, orders: Sequence[str]) -> None:
        """Varias órdenes en un mensaje: entran en la cola en el orden en que se han escrito.
        Dentro de un mensaje así solo valen órdenes: las frases de control y la de activación
        se escriben solas."""
        if self._machine.state not in (AssistantState.LISTENING_COMMAND, AssistantState.IDLE):
            return
        logger.info("Mensaje con %d órdenes", len(orders))
        for text in orders:
            order = self._router.prepare(text)
            if order is None:
                await self._handle(fsm.NoMatch(text))
                continue
            self._bus.publish(events.CommandReceived(text, recognized=True))
            await self._handle(fsm.IntentMatched(order))

    async def _on_user_action(self, entry: _UserAction) -> None:
        if self._session is None or not self._router.specs_of(entry.module, entry.action):
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
                self._announcer.clear()
            case fsm.PublishUnrecognized(text=text):
                if text.strip():
                    self._bus.publish(events.CommandReceived(text, recognized=False))
            case fsm.CloseSession(reason=reason, silent=silent):
                await self._close_session(reason, silent)
            case fsm.ExitProcess():
                self._stopping = True
                self._on_exit()
            case fsm.RunTurn(intent=request):
                self._enqueue(request)
            case fsm.CancelTurn(announce=announce):
                await self._cancel(announce)
            case fsm.DeliverNotice(notice=notice):
                if isinstance(notice, Notice):
                    self._deliver(notice)
            case fsm.DeliverPendingNotices():
                pass  # los entrega `_pump` cuando termina la frase de apertura
            case fsm.OpenDialogue(dialogue=dialogue):
                self._open_dialogue(dialogue)
            case fsm.RejectDialogue(dialogue=dialogue):
                _settle(dialogue, DialogueAnswer(cancelled=True))
            case fsm.RepeatQuestion():
                self._ask_again()
            case fsm.RestartDialogueTimer():
                if self._dialogue_armed:
                    self._arm_dialogue_timer()
            case fsm.ResolveDialogue(value=value):
                self._close_dialogue(DialogueAnswer(cancelled=False, value=value), "answered")
            case fsm.CancelDialogue(announce=announce, by_user=by_user):
                dialogue = self._dialogue
                self._close_dialogue(DialogueAnswer(cancelled=True, by_user=by_user), "cancelled")
                # «¿Quiere añadir otro aviso…?» cancelada no cancela nada: el recordatorio se
                # guarda con lo que tiene (recordatorio.md, «Creación con una orden»).
                # Tampoco un ofrecimiento sin respuesta (`OFFER`): no había nada en marcha.
                keeps = dialogue is not None and (
                    dialogue.expected_type is ExpectedType.REMINDER_ACTION
                    or bool(dialogue.metadata.get(OFFER))
                )
                if announce and not keeps:
                    self._announce(Phrase("general.operacion_cancelada"))

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
        errors = [*errors, *self._apply_config(config)]
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
        self._close_dialogue(DialogueAnswer(cancelled=True), "cancelled")
        self._cancel_reason = CLOSED_REASON  # RN-46: también el protocolo en curso
        try:
            await self._cancel_orders()
        finally:
            self._cancel_reason = CANCELLED_REASON
        await self._cancel_background(CLOSED_REASON)
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

    # --- Cola de órdenes ---------------------------------------------------------------------

    def _busy(self) -> bool:
        """Hay órdenes en la cola o en ejecución, o respuestas por decir."""
        return len(self._jobs) > 0 or self._announcer.active

    def _enqueue(self, request: object) -> None:
        """`RunTurn`: la orden entra en la cola. Empieza cuando el planificador lo permite."""
        if isinstance(request, Order):
            self._jobs.add(self._claim(request.specs), _Work(request.text, order=request))
        elif isinstance(request, Intent):
            specs = self._router.specs_of(request.module, request.action)
            claim = self._claim((request.module, spec) for spec in specs)
            self._jobs.add(claim, _Work(request.description, intent=request))
        else:
            logger.warning("Orden desconocida: %r", request)

    def _claim(self, specs: Iterable[tuple[str, IntentSpec]]) -> Claim:
        """Lo que ocupa una orden que puede acabar siendo cualquiera de `specs`. Una acción
        `exclusive` ocupa todos los módulos: ninguna otra orden se ejecuta a la vez."""
        lanes: set[str] = set()
        reads: set[str] = set()
        writes: set[str] = set()
        for module, spec in specs:
            lanes.add(module)
            if spec.exclusive:
                lanes |= {CORE_MODULE, *self._modules}
            reads |= spec.resources_read
            writes |= spec.writes
        return Claim(frozenset(lanes), frozenset(reads), frozenset(writes))

    def _start_ready(self) -> None:
        """Pone en marcha las órdenes que ya pueden empezar. Una orden escrita se resuelve
        aquí, no al escribirla: así ve lo que han dejado las órdenes anteriores."""
        while ready := self._jobs.take_ready():
            for job in ready:
                work = job.payload
                if work.intent is None:
                    assert work.order is not None
                    work.intent = intent = self._router.resolve(work.order)
                    specs = self._router.specs_of(intent.module, intent.action)
                    self._jobs.narrow(job, self._claim((intent.module, spec) for spec in specs))
                work.runner = self._spawn(job, work.intent)

    def _spawn(self, job: Job[_Work], intent: Intent) -> asyncio.Task:
        async def body() -> None:
            try:
                await self._run_intent(intent)
            except asyncio.CancelledError:
                raise
            except Exception:  # RNF-23: una orden que falla no bloquea al asistente
                logger.exception("La orden %s ha fallado", intent.key)

        runner = asyncio.ensure_future(body())
        runner.add_done_callback(lambda _done: self._queue.put_nowait(_JobDone(job)))
        return runner

    def _publish_queue(self) -> None:
        waiting = tuple(job.payload.text for job in self._jobs.waiting)
        if waiting != self._queued:
            self._queued = waiting
            self._bus.publish(events.OrderQueueChanged(waiting))

    def _pump(self) -> None:
        """Tras cada entrada: arranca las órdenes que pueden empezar y, con el asistente
        libre, entrega el siguiente aviso y mantiene la cuenta de inactividad."""
        if self._stopping or self._session is None:
            return
        self._start_ready()
        self._publish_queue()
        if self._busy():
            self._cancel_silence_timer()  # la cuenta no corre con órdenes o respuestas en curso
            return
        state = self._machine.state
        if state is AssistantState.LISTENING_COMMAND:
            notice = self._notices.pop()
            if notice is not None:
                self._cancel_silence_timer()
                self._deliver(notice)
            elif self._silence_timer is None:
                self._restart_silence_timer()  # la cuenta empieza al terminar la respuesta
        elif state is AssistantState.IDLE:
            # Un aviso de recordatorio pone al asistente en escucha; los demás esperan (RN-39).
            reminder = self._notices.pop_reminder()
            if reminder is not None:
                self._queue.put_nowait(fsm.NoticeReady(reminder, reminder=True))

    async def _cancel_orders(self) -> bool:
        """Cancela las órdenes en curso y en espera y calla las respuestas. True si había
        algo."""
        jobs = self._jobs.clear()
        runners = [job.payload.runner for job in jobs if job.payload.runner is not None]
        for runner in runners:
            runner.cancel()
        await asyncio.gather(*runners, return_exceptions=True)
        spoke = self._announcer.clear()
        self._publish_queue()
        return bool(jobs) or spoke

    async def _cancel(self, announce: bool) -> None:
        """`CancelTurn`. Con `announce` es «cancelar»: también detiene lo que sigue en segundo
        plano y, si había algo que cancelar, dice «Cancelado.»."""
        cancelled = await self._cancel_orders()
        if not announce:
            return
        if self._background:
            await self._cancel_background(CANCELLED_REASON)
            cancelled = True
        if cancelled:
            self._announce(Phrase("general.cancelado"))

    async def _run_intent(self, intent: Intent) -> None:
        if intent.module == CORE_MODULE:
            self._run_core(intent)
        else:
            await self.run_task(
                intent.module, intent.action, intent.params, origin="voz",
                description=intent.description, error=intent.error, quiet=intent.quiet,
            )  # fmt: skip

    def _run_core(self, intent: Intent) -> None:
        """Intenciones del núcleo: no son tareas de ningún módulo de acción."""
        if intent in (SHOW_SCREEN, HIDE_SCREEN):
            # Sin voz: solo la interfaz cambia (catalogo-intenciones.md, sección 2).
            self._bus.publish(events.ShowScreenRequested(visible=intent == SHOW_SCREEN))
        elif intent.action in (ASIDE_WINDOW, RESTORE_WINDOW):
            # Sin voz, salvo si no hay ninguna ventana con ese nombre.
            if intent.error is not None:
                self._announce(intent.error)
            else:
                self._bus.publish(events.WindowAsideRequested(
                    str(intent.params["ventana"]), aside=intent.action == ASIDE_WINDOW
                ))  # fmt: skip
        elif intent in (ASIDE_WINDOWS, RESTORE_WINDOWS):
            self._bus.publish(events.WindowAsideRequested(aside=intent == ASIDE_WINDOWS))
        elif intent == HELP:
            self._bus.publish(events.HelpShown(self._router.help()))
            self._bus.publish(events.PanelActivated(HELP_PANEL))
            if not intent.quiet:
                self._announce(Phrase("general.ayuda"))
        elif intent == REPEAT:
            self._announce(self._speaker.last_phrase or Phrase("general.nada_que_repetir"))
        else:
            logger.warning("Intención del núcleo desconocida: %s", intent.key)

    # --- Diálogo ------------------------------------------------------------------------------

    async def _ask(
        self,
        question: Phrase,
        expected_type: ExpectedType,
        *,
        metadata: Mapping[str, object] | None = None,
        subject: Mapping[str, object] | None = None,
        speech: list[Phrase] | None = None,
    ) -> DialogueAnswer:
        """`ctx.ask`: pregunta y espera la respuesta sin bloquear el bucle. Lo que la tarea
        llevaba dicho se dice antes de la pregunta."""
        async with self._dialogue_lock:
            if speech:
                self._announce(*speech)
                speech.clear()
            dialogue = fsm.DialogueContext(
                question, expected_type, dict(metadata or {}),
                self._config.settings.dialogue.timeout_seconds,
                asyncio.get_running_loop().create_future(), subject,
            )  # fmt: skip
            self._queue.put_nowait(fsm.DialogueRequested(dialogue))
            answer = await dialogue.continuation  # type: ignore[misc]
            logger.info("Diálogo resuelto: %s", "cancelado" if answer.cancelled else "respuesta")
            return answer

    def _open_dialogue(self, dialogue: fsm.DialogueContext) -> None:
        """`OpenDialogue`: publica la pregunta y la dice; el tiempo de espera empieza al
        terminar de decirla."""
        self._dialogue = dialogue
        self._cancel_dialogue_timer()
        try:
            text = render(dialogue.question)
        except Exception:
            logger.exception("Pregunta sin frase: %s", dialogue.question.id)
            text = ""
        self._bus.publish(
            events.DialogueOpened(
                text, dialogue.expected_type.name, HINTS.get(dialogue.expected_type, ()),
                dialogue.timeout_seconds, dialogue.subject,
            )
        )  # fmt: skip
        self._speak_question(dialogue.question)

    def _ask_again(self) -> None:
        """Respuesta no válida, primera vez: «No le he entendido.» (o «No he entendido la
        fecha.» si se esperaba una) y la pregunta otra vez."""
        if self._dialogue is not None:
            reason = (
                Phrase("entidad.fecha")
                if self._dialogue.expected_type is ExpectedType.DATETIME
                else Phrase("general.no_entendido")
            )
            self._speak_question(reason, self._dialogue.question)

    def _speak_question(self, *phrases: Phrase) -> None:
        self._cancel_dialogue_timer()
        self._announcer.submit(Announcement(phrases, on_delivered=self._question_said))

    def _question_said(self) -> None:
        if self._dialogue is not None and self._machine.state in _AWAITING:
            self._arm_dialogue_timer()

    def _arm_dialogue_timer(self) -> None:
        self._cancel_dialogue_timer()
        if self._dialogue is None:
            return
        self._dialogue_armed = True
        token = self._dialogue_token
        self._dialogue_timer = self._clock.call_later(
            self._dialogue.timeout_seconds,
            lambda: self._queue.put_nowait(_DialogueElapsed(token)),
        )

    def _cancel_dialogue_timer(self) -> None:
        self._dialogue_token += 1
        self._dialogue_armed = False
        timer, self._dialogue_timer = self._dialogue_timer, None
        if timer is not None:
            timer.cancel()

    def _close_dialogue(self, answer: DialogueAnswer, outcome: events.DialogueOutcome) -> None:
        """Resuelve la pregunta abierta, si la hay, y publica `DialogueClosed`."""
        dialogue, self._dialogue = self._dialogue, None
        self._cancel_dialogue_timer()
        if dialogue is None:
            return
        _settle(dialogue, answer)
        self._bus.publish(events.DialogueClosed(outcome))

    # --- Voz ---------------------------------------------------------------------------------

    def _announce(self, *phrases: Phrase, on_delivered: Callable[[], None] | None = None) -> None:
        """Pone una respuesta en la cola de voz. `on_delivered`: al terminar de decirla; sin
        nada que decir, en el acto."""
        if phrases:
            self._announcer.submit(Announcement(phrases, on_delivered=on_delivered))
        elif on_delivered is not None:
            on_delivered()

    def _deliver(self, notice: Notice) -> None:
        """Entrega un aviso: activa su panel al empezar a decirlo."""
        panel = notice.panel
        self._announcer.submit(
            Announcement(
                (notice.phrase,),
                on_start=None if panel is None
                else lambda: self._bus.publish(events.PanelActivated(panel)),
                on_delivered=notice.on_delivered,
            )
        )  # fmt: skip

    async def _say(self, phrase: Phrase) -> bool:
        """Dice una frase. True si se ha cortado antes de terminar."""
        try:
            return (await self._speaker.say(phrase)).interrupted
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("No se ha podido decir %s", phrase.id)
            return False

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
        task: "_Task | None" = None,
    ) -> ActionResult:
        """Ejecuta una acción como tarea: la registra en `pendiente`, llama al módulo, captura
        cualquier excepción (RNF-23), fija el estado final y deja la respuesta en la cola de
        voz, que la dice cuando le llega el turno.

        `error`: una entidad no se pudo resolver; la tarea se crea ya en `error` con esa frase.
        Con `quiet`, la respuesta solo se dice si es un error. `task`: una subtarea ya creada
        con `ctx.subtask`, que es la que se ejecuta.
        """
        if self._session is None:
            raise RuntimeError("No hay sesión abierta")
        if task is None:
            task = self._new_task(module, description or f"{module} {action}", parent)
        else:
            self._publish_task(task, "pendiente")
        panel = self._panels.get((module, action))
        if panel is not None:
            self._bus.publish(events.PanelActivated(panel))
        self._executing += 1
        self._refresh()
        speech: list[Phrase] = []  # la respuesta: lo que el módulo dice al trabajar y al final
        try:
            if error is not None:
                result = ActionResult("error", error)
            else:
                ctx = self._context(origin, task, speech)
                result = await self._modules[module].execute(action, params, ctx)
        except asyncio.CancelledError:
            self._finish_task(task, "error", self._cancel_reason)
            self._fail_unrun(task, self._cancel_reason)
            raise
        except Exception:
            logger.exception("La acción %s.%s ha fallado", module, action)
            result = ActionResult("error", Phrase("general.error"))
        finally:
            self._executing -= 1
            self._refresh()
        self._fail_unrun(task, CANCELLED_REASON)  # subtareas que el módulo no ha ejecutado
        if result.description:
            task.description = result.description
        if result.background and result.status == "completado":
            self._publish_task(task, "pendiente")  # sigue en segundo plano
        else:
            self._finish_task(task, result.status, self._detail(result))
        if result.speech is not None:
            speech.append(result.speech)
        if quiet and result.status == "completado":
            speech = []
        self._announce(*speech, on_delivered=result.on_spoken)
        return result

    def _new_task(self, module: str, description: str, parent: int | None) -> _Task:
        """Registra una tarea en `pendiente` como actividad de la sesión y la publica."""
        assert self._session is not None
        task = _Task(
            self._activities.add(self._session.id, module, description, self._clock.now(), parent),
            parent, module, description,
        )  # fmt: skip
        self._publish_task(task, "pendiente")
        return task

    def _fail_unrun(self, parent: _Task, reason: str) -> None:
        """Las subtareas de `parent` que no han llegado a ejecutarse quedan en `error`."""
        for task_id, task in list(self._unrun.items()):
            if task.parent == parent.id:
                del self._unrun[task_id]
                self._finish_task(task, "error", reason)

    def _subtask(self, parent: _Task | None, module: str, description: str) -> Subtask:
        """`ctx.subtask`: una tarea hija en `pendiente`, que se ejecuta después con `invoke`."""
        if parent is None:
            raise RuntimeError("Solo una tarea puede tener subtareas")
        task = self._new_task(module, description, parent.id)
        self._unrun[task.id] = task

        def fail(reason: str) -> None:
            if self._unrun.pop(task.id, None) is not None:
                self._finish_task(task, "error", reason)

        return Subtask(task.id, fail)

    async def _invoke(
        self,
        parent: _Task | None,
        speech: list[Phrase] | None,
        module: str,
        action: str,
        params: Mapping[str, object],
        *,
        quiet: bool = True,
        subtask: Subtask | None = None,
        description: str | None = None,
        resolve: bool = False,
    ) -> ActionResult:
        """`ctx.invoke`: ejecuta una acción como subtarea de `parent`, por la misma interfaz y
        con el mismo `run_task` que una orden del usuario. Lo que la tarea llevaba dicho se
        dice antes (como antes de una pregunta): así el protocolo anuncia que empieza."""
        if parent is None:
            raise RuntimeError("Solo una tarea puede invocar otras acciones")
        if speech:
            self._announce(*speech)
            speech.clear()
        task = None
        if subtask is not None:
            task = self._unrun.pop(subtask.id, None)
            if task is None:
                raise RuntimeError(f"La subtarea {subtask.id} ya no está pendiente")
        error = None
        if resolve:
            try:
                params = self._router.resolve_params(module, action, params)
            except ParamError as unresolved:
                error = unresolved.phrase
            except KeyError:
                error = Phrase("general.error")
        return await self.run_task(
            module, action, params, origin="protocolo", parent=parent.id,
            description=description, error=error, quiet=quiet, task=task,
        )  # fmt: skip

    def _context(
        self, origin: Origin, task: _Task | None, speech: list[Phrase] | None = None
    ) -> ActionContext:
        """`speech`: donde se acumula lo que la tarea dice; sin tarea, va directo a la cola."""

        async def say(phrase: Phrase) -> None:
            if speech is None:
                self._announce(phrase)
            else:
                speech.append(phrase)

        async def ask(
            question: Phrase,
            expected_type: ExpectedType,
            *,
            metadata: Mapping[str, object] | None = None,
            subject: Mapping[str, object] | None = None,
        ) -> DialogueAnswer:
            return await self._ask(
                question, expected_type, metadata=metadata, subject=subject, speech=speech
            )

        def background(work: Coroutine[Any, Any, ActionResult]) -> None:
            if task is None:
                work.close()
                raise RuntimeError("Solo una tarea puede seguir en segundo plano")
            self._spawn_background(task, work)

        async def invoke(
            module: str, action: str, params: Mapping[str, object], **options: Any
        ) -> ActionResult:
            return await self._invoke(task, speech, module, action, params, **options)

        return ActionContext(
            session=self._session,
            origin=origin,
            workdir=self._workdir,
            clock=self._clock,
            config=self._config,
            db=self._database,
            platform=self._platform,
            places=self._places,
            say=say,
            publish=self._bus.publish,
            notify=self._notify,
            background=background,
            task_id=None if task is None else task.id,
            scheduler=self._scheduler,
            ask=ask,
            active_panel=self._active_panel,
            subtask=lambda module, description: self._subtask(task, module, description),
            invoke=invoke,
        )

    @staticmethod
    def _detail(result: ActionResult) -> str | None:
        """Motivo que se muestra bajo una tarea en `error`: el del módulo o, si no, su frase."""
        if result.status != "error":
            return None
        if result.detail is not None:
            return result.detail
        if result.speech is None:
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
        if self._machine.state is not AssistantState.LISTENING_COMMAND or self._busy():
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
        elif state in _AWAITING:
            activity = Activity.ESPERANDO  # la tarea que pregunta sigue en ejecución
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


def _changes_state(entry: fsm.Input) -> bool:
    """Frase de activación, de reposo o de cierre: cambia el estado y no se muestra como
    subtítulo; sí se muestra lo que responde el asistente."""
    if isinstance(entry, fsm.Control):
        return entry.kind in (fsm.ControlKind.REPOSO, fsm.ControlKind.CERRAR)
    return isinstance(entry, fsm.WakeWord | fsm.ClosingPhraseInIdle)


def _settle(dialogue: fsm.DialogueContext, answer: DialogueAnswer) -> None:
    """Entrega la respuesta a la corrutina que pregunta, si sigue esperando."""
    future = dialogue.continuation
    if future is not None and not future.done():
        future.set_result(answer)
