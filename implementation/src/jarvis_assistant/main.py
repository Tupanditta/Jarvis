"""Composición y arranque del proceso (proceso.md).

`build_app` construye y conecta todos los componentes sin lanzar hilos ni abrir dispositivos.
`main` añade lo real: carpetas, registro, instancia única, modelos, Qt y el hilo del núcleo.
"""
import argparse
import asyncio
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from jarvis_assistant import __version__
from jarvis_assistant import config as config_module
from jarvis_assistant.action_modules.app_launcher import AppLauncher
from jarvis_assistant.action_modules.command_runner import CommandRunner
from jarvis_assistant.action_modules.file_manager import FileCreation, FileSearch
from jarvis_assistant.action_modules.protocol_runner import ProtocolRunner
from jarvis_assistant.action_modules.reminder_manager import ReminderManager
from jarvis_assistant.action_modules.session_manager import History, SessionManager
from jarvis_assistant.config import Config
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.action_api import ActionModule
from jarvis_assistant.core.clock import Clock, SystemClock
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.orchestrator import Orchestrator, Reload
from jarvis_assistant.core.scheduler import ApsScheduler, ClockScheduler, Scheduler
from jarvis_assistant.core.security import ProfileVault
from jarvis_assistant.core.state_machine import StateMachine
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router.router import IntentRouter
from jarvis_assistant.os_adapters.base import PlatformAdapter
from jarvis_assistant.paths import PROFILE_FILE_NAME, AppPaths, missing_models
from jarvis_assistant.process.logging_setup import (
    LEVELS,
    install_asyncio_handler,
    install_excepthooks,
    setup_logging,
)
from jarvis_assistant.process.single_instance import acquire_single_instance
from jarvis_assistant.speaker.piper_synth import Synthesizer
from jarvis_assistant.speaker.player import AudioPlayer
from jarvis_assistant.speaker.speaker import Speaker

logger = logging.getLogger(__name__)

MUTEX_NAME = "Local\\JarvisAssistant"
SHUTDOWN_LIMIT_SECONDS = 3.0
_MISSING_MODELS_NOTICE_MS = 6000

# Módulos de acción registrados. Añadir un módulo es añadir aquí su clase: `build_app` crea
# una instancia por aplicación. El orden es el de desempate entre patrones. El módulo Sesión
# va aparte, antes que todos: también lo usa el orquestador para abrir y cerrar la sesión.
ACTION_MODULES: list[Callable[[], ActionModule]] = [
    CommandRunner, AppLauncher, FileSearch, FileCreation, History, ReminderManager,
    ProtocolRunner,
]


@dataclass
class Adapters:
    """Todo lo que toca hardware, modelos, reloj o sistema operativo (RES-47)."""

    platform: PlatformAdapter
    clock: Clock
    database: Database
    synthesizer: Synthesizer
    player: AudioPlayer
    # Trabajos a una fecha. Sin él, uno sobre `clock`: el de las pruebas, con reloj falso.
    scheduler: Scheduler | None = None


@dataclass
class App:
    config: Config
    bus: EventBus
    machine: StateMachine
    router: IntentRouter
    sessions: SessionManager
    speaker: Speaker
    orchestrator: Orchestrator
    adapters: Adapters
    workdir: Workdir


def build_app(
    config: Config,
    adapters: Adapters,
    *,
    bus: EventBus | None = None,
    on_exit: Callable[[], None] = lambda: None,
    home: Path | None = None,
    reload_config: Reload | None = None,
    windows: Sequence[str] = (),
) -> App:
    """Construye el grafo completo sin lanzar hilos ni abrir dispositivos.

    `home`: carpeta del usuario, donde empieza el directorio de trabajo de cada sesión.
    `reload_config`: relee la configuración al abrir cada sesión (RF-96).
    `windows`: títulos de las ventanas flotantes de la interfaz, para «aparta {ventana}».
    """
    settings = config.settings
    bus = bus or EventBus()
    machine = StateMachine()
    speaker = Speaker(
        synthesizer=adapters.synthesizer,
        player=adapters.player,
        bus=bus,
        clock=adapters.clock,
        settings=settings.tts,
    )
    workdir = Workdir(home or Path.home())
    router = IntentRouter(
        settings.router, config.aliases, workdir=workdir, now=adapters.clock.now,
        windows=windows,
    )
    sessions = SessionManager(adapters.database, adapters.clock, bus)
    orchestrator = Orchestrator(
        machine=machine,
        bus=bus,
        clock=adapters.clock,
        config=config,
        router=router,
        speaker=speaker,
        sessions=sessions,
        database=adapters.database,
        platform=adapters.platform,
        workdir=workdir,
        modules=[sessions, *(create() for create in ACTION_MODULES)],
        reload_config=reload_config,
        on_exit=on_exit,
        scheduler=adapters.scheduler or ClockScheduler(adapters.clock),
    )
    return App(config, bus, machine, router, sessions, speaker, orchestrator, adapters, workdir)


# --- Arranque real ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="jarvis_assistant", description="Asistente personal")
    parser.add_argument("--log-level", choices=LEVELS, help="nivel del registro de diagnóstico")
    parser.add_argument(
        "--preview", action="store_true",
        help="interfaz con eventos simulados, sin voz ni modelos",
    )
    parser.add_argument("--ui-debug", action="store_true", help="contador de frames")
    return parser.parse_args(argv)


def create_platform() -> PlatformAdapter:
    if sys.platform == "win32":
        from jarvis_assistant.os_adapters.windows import WindowsAdapter

        return WindowsAdapter()
    raise RuntimeError(f"Sistema no admitido todavía: {sys.platform}")


def real_adapters(
    config: Config, platform: PlatformAdapter, paths: AppPaths, clock: Clock
) -> Adapters:
    """Adaptadores reales. Abre la base de datos: debe llamarse en el hilo del núcleo."""
    from jarvis_assistant.speaker.piper_synth import PiperSynthesizer
    from jarvis_assistant.speaker.player import Player

    settings = config.settings
    database = Database(paths.db_path, now=clock.now)
    database.migrate()
    return Adapters(
        platform=platform,
        clock=clock,
        database=database,
        synthesizer=PiperSynthesizer(paths.models_dir, settings.tts.voice),
        player=Player(clock),
        scheduler=ApsScheduler(),
    )


class CoreThread:
    """Hilo del núcleo: bucle `asyncio` con el orquestador, la base de datos y la voz."""

    def __init__(
        self,
        config: Config,
        bus: EventBus,
        make_adapters: Callable[[], Adapters],
        on_exit: Callable[[], None],
        reload_config: Reload | None = None,
        windows: Sequence[str] = (),
    ) -> None:
        self._config = config
        self._windows = tuple(windows)
        self._bus = bus
        self._make_adapters = make_adapters
        self._on_exit = on_exit
        self._reload_config = reload_config
        self._thread = threading.Thread(target=self._main, name="nucleo", daemon=True)
        self.bound = threading.Event()  # el bus ya acepta `publish_threadsafe`
        self.app: App | None = None

    def start(self) -> None:
        self._thread.start()
        self.bound.wait()

    def join(self, timeout: float) -> bool:
        """Espera al fin del hilo. False si no ha terminado a tiempo."""
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        install_asyncio_handler(loop)
        self._bus.bind_loop(loop)
        self.bound.set()
        try:
            loop.run_until_complete(self._run())
        except Exception:
            logger.exception("El núcleo ha terminado con un error")
        finally:
            loop.close()
            self._on_exit()

    async def _run(self) -> None:
        started = time.monotonic()
        adapters = self._make_adapters()
        app = build_app(
            self._config, adapters, bus=self._bus, reload_config=self._reload_config,
            windows=self._windows,
        )
        self.app = app
        try:
            app.sessions.recover_interrupted()
            await app.speaker.preload()
            logger.info("Listo en %.1f s", time.monotonic() - started)
            if self._config.settings.startup.open_session_on_start:
                app.orchestrator.submit(fsm.OpenSessionRequested())
            await app.orchestrator.run()
        finally:
            app.speaker.close()
            adapters.database.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    platform = create_platform()
    paths = AppPaths.from_platform(platform)
    paths.ensure()
    setup_logging(paths.log_dir, args.log_level or "INFO")
    install_excepthooks()
    logger.info("Jarvis %s arranca", __version__)

    if args.preview:
        return _run_preview(args, paths)

    instance = acquire_single_instance(MUTEX_NAME)
    if instance is None:
        return 0
    try:
        return _run(args, platform, paths)
    finally:
        instance.close()
        logger.info("Jarvis termina")


def _load_config(args: argparse.Namespace, paths: AppPaths) -> Config:
    config_module.install_defaults(paths.config_dir)
    config, errors = config_module.load(paths.config_dir)
    for error in errors:
        logger.error("Configuración: %s, clave %s: %s", error.file, error.key, error.reason)
    if args.log_level is None:
        logging.getLogger().setLevel(config.settings.logging.level)
    return config


def report_missing_models(paths: AppPaths, voice: str) -> list[Path]:
    """Modelos que faltan, registrados con un mensaje claro (proceso.md). Vacía si están."""
    missing = missing_models(paths.models_dir, voice)
    if missing:
        names = ", ".join(str(path) for path in missing)
        logger.error(
            "Faltan modelos en %s: %s. Ejecute el guion de descarga de modelos de la instalación",
            paths.models_dir, names,
        )
    return missing


def _run_preview(args: argparse.Namespace, paths: AppPaths) -> int:
    """Vista previa de la interfaz: sin núcleo, voz, modelos ni instancia única."""
    from PySide6.QtGui import QGuiApplication

    from jarvis_assistant.ui.preview import run_preview

    config = _load_config(args, paths)
    QGuiApplication(sys.argv[:1])
    return run_preview(config.settings.ui, debug=args.ui_debug)


def _run(args: argparse.Namespace, platform: PlatformAdapter, paths: AppPaths) -> int:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from jarvis_assistant.configurator.window import ConfigWindow
    from jarvis_assistant.process.tray import TrayController
    from jarvis_assistant.ui.app import UiApp
    from jarvis_assistant.ui.bridge import UiBridge
    from jarvis_assistant.ui.workspace import WINDOWS

    config = _load_config(args, paths)

    qt_app = QApplication(sys.argv[:1])
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setApplicationName("Jarvis")

    bus = EventBus()
    bridge = UiBridge()

    def request_quit() -> None:
        """Salida ordenada con límite: pasado el plazo, el proceso termina igualmente."""
        watchdog = threading.Timer(SHUTDOWN_LIMIT_SECONDS, os._exit, args=(0,))
        watchdog.daemon = True
        watchdog.start()
        bus.publish_threadsafe(events.QuitRequested())

    tray = TrayController(
        publish=bus.publish_threadsafe,
        request_quit=request_quit,
        config_dir=paths.config_dir,
        log_dir=paths.log_dir,
    )

    if report_missing_models(paths, config.settings.tts.voice):
        tray.show()
        tray.notify("Jarvis no puede arrancar", "Faltan modelos. Ejecute la descarga de modelos.")
        QTimer.singleShot(_MISSING_MODELS_NOTICE_MS, qt_app.quit)
        qt_app.exec()
        return 1

    # La ventana de configuración solo se abre desde la pantalla dormida. Se crea al abrirla y
    # se destruye al cerrarla: durante la sesión no ocupa memoria ni hace trabajo. Mientras
    # está abierta no se puede iniciar sesión. Al guardar, el núcleo vuelve a cargar la
    # configuración (`ConfigSaved`).
    settings_window: list[ConfigWindow] = []
    # La ventana tiene su propia conexión a la base de datos (las contraseñas de los perfiles):
    # la del núcleo solo se usa en su hilo.
    settings_db: list[Database] = []

    def set_configuring(configuring: bool) -> None:
        ui.set_configuring(configuring)
        tray.set_configuring(configuring)

    def close_settings() -> None:
        if settings_window:
            window = settings_window.pop()
            # Se destruye en la siguiente vuelta del bucle, cuando QML ya no la está usando;
            # con ella, su motor QML y sus dos ventanas.
            QTimer.singleShot(0, lambda: window.deleteLater())
        while settings_db:
            settings_db.pop().close()
        set_configuring(False)

    def open_settings() -> None:
        if not settings_window:
            database = Database(paths.db_path)
            settings_db.append(database)
            window = ConfigWindow(
                paths.config_dir,
                on_saved=lambda: bus.publish_threadsafe(events.ConfigSaved()),
                owner=ui.screen,
                vault=ProfileVault(database),
            )
            window.closed.connect(close_settings)
            settings_window.append(window)
        set_configuring(True)
        settings_window[0].show()

    ui = UiApp(
        publish=bus.publish_threadsafe,
        settings=config.settings.ui,
        platform=platform,
        debug=args.ui_debug,
        output_lines=config.settings.commands.output_lines,
        profile_path=paths.data_dir / PROFILE_FILE_NAME,
        open_settings=open_settings,
    )

    def exit_ui() -> None:
        ui.shutdown()
        qt_app.quit()

    queued = Qt.ConnectionType.QueuedConnection
    bridge.eventReceived.connect(ui.on_event, queued)
    bridge.eventReceived.connect(tray.on_event, queued)
    bridge.levelReady.connect(lambda: ui.apply_level(bridge.take_level()), queued)
    bridge.exitRequested.connect(exit_ui, queued)
    bridge.attach(bus)
    qt_app.commitDataRequest.connect(lambda _manager: request_quit())

    clock = SystemClock()
    core = CoreThread(
        config,
        bus,
        make_adapters=lambda: real_adapters(config, platform, paths, clock),
        on_exit=bridge.exitRequested.emit,
        reload_config=lambda previous: config_module.load(paths.config_dir, previous=previous),
        windows=[spec.title for spec in WINDOWS],
    )
    core.start()
    tray.show()
    ui.start()
    qt_app.exec()

    tray.hide()
    if not core.join(SHUTDOWN_LIMIT_SECONDS):
        logger.warning("El núcleo no ha terminado a tiempo; la sesión se recuperará al arrancar")
    return 0
