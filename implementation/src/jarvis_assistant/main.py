"""Composición y arranque del proceso (proceso.md).

`build_app` construye y conecta todos los componentes sin lanzar hilos ni abrir dispositivos.
`main` añade lo real: carpetas, registro, instancia única, modelos, Qt, el hilo del núcleo y
el hilo de audio.
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
from typing import Any

from jarvis_assistant import __version__
from jarvis_assistant import config as config_module
from jarvis_assistant.action_modules.session_manager import SessionManager
from jarvis_assistant.audio_capture.processor import AudioProcessor
from jarvis_assistant.audio_capture.types import MicrophoneSource, VoiceDetector, WakeWordDetector
from jarvis_assistant.config import Config
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.clock import Clock, SystemClock
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.orchestrator import CaptureController, Orchestrator
from jarvis_assistant.core.state_machine import StateMachine
from jarvis_assistant.intent_router.router import IntentRouter
from jarvis_assistant.paths import AppPaths, missing_models
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
from jarvis_assistant.transcriber import Transcriber

logger = logging.getLogger(__name__)

MUTEX_NAME = "Local\\JarvisAssistant"
SHUTDOWN_LIMIT_SECONDS = 3.0
_MISSING_MODELS_NOTICE_MS = 6000

# Módulos de acción registrados. Añadir un módulo es añadir aquí su instancia.
ACTION_MODULES: list[Any] = []


@dataclass
class Adapters:
    """Todo lo que toca hardware, modelos, reloj o sistema operativo (RES-47)."""

    platform: Any
    clock: Clock
    database: Database
    microphone: MicrophoneSource
    wakeword: WakeWordDetector
    vad: VoiceDetector
    transcriber: Transcriber
    synthesizer: Synthesizer
    player: AudioPlayer


@dataclass
class App:
    config: Config
    bus: EventBus
    machine: StateMachine
    router: IntentRouter
    sessions: SessionManager
    speaker: Speaker
    capture: AudioProcessor
    orchestrator: Orchestrator
    adapters: Adapters


def build_app(
    config: Config,
    adapters: Adapters,
    *,
    bus: EventBus | None = None,
    on_exit: Callable[[], None] = lambda: None,
) -> App:
    """Construye el grafo completo sin lanzar hilos ni abrir dispositivos."""
    settings = config.settings
    bus = bus or EventBus()
    machine = StateMachine()
    capture = AudioProcessor(
        microphone=adapters.microphone,
        wakeword=adapters.wakeword,
        vad=adapters.vad,
        settings=settings.audio,
        deliver=lambda entry: orchestrator.submit(entry),
        monotonic=adapters.clock.monotonic,
        can_refresh=lambda: not speaker.speaking,
    )
    capture_controller = CaptureController(capture, machine, adapters.clock, settings.audio)
    speaker = Speaker(
        synthesizer=adapters.synthesizer,
        player=adapters.player,
        bus=bus,
        clock=adapters.clock,
        settings=settings.tts,
        capture_gate=capture_controller,
    )
    router = IntentRouter(settings.router, config.aliases)
    sessions = SessionManager(adapters.database, adapters.clock, bus)
    orchestrator = Orchestrator(
        machine=machine,
        bus=bus,
        clock=adapters.clock,
        config=config,
        router=router,
        transcriber=adapters.transcriber,
        speaker=speaker,
        capture=capture,
        capture_controller=capture_controller,
        sessions=sessions,
        on_exit=on_exit,
    )
    return App(config, bus, machine, router, sessions, speaker, capture, orchestrator, adapters)


# --- Arranque real ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="jarvis_assistant", description="Asistente de voz")
    parser.add_argument("--log-level", choices=LEVELS, help="nivel del registro de diagnóstico")
    return parser.parse_args(argv)


def create_platform() -> Any:
    if sys.platform == "win32":
        from jarvis_assistant.os_adapters.windows import WindowsAdapter

        return WindowsAdapter()
    raise RuntimeError(f"Sistema no admitido todavía: {sys.platform}")


def real_adapters(config: Config, platform: Any, paths: AppPaths, clock: Clock) -> Adapters:
    """Adaptadores reales. Abre la base de datos: debe llamarse en el hilo del núcleo."""
    from jarvis_assistant.audio_capture.microphone import Microphone
    from jarvis_assistant.audio_capture.vad import SileroVad
    from jarvis_assistant.audio_capture.wakeword import OpenWakeWordDetector
    from jarvis_assistant.speaker.piper_synth import PiperSynthesizer
    from jarvis_assistant.speaker.player import Player
    from jarvis_assistant.transcriber.whisper_transcriber import WhisperTranscriber

    settings = config.settings
    database = Database(paths.db_path, now=clock.now)
    database.migrate()
    return Adapters(
        platform=platform,
        clock=clock,
        database=database,
        microphone=Microphone(settings.audio),
        wakeword=OpenWakeWordDetector(
            paths.models_dir,
            verifier_path=paths.verifier_path,
            use_verifier=settings.audio.wakeword_verifier,
            verifier_gate=settings.audio.wakeword_verifier_gate,
        ),
        vad=SileroVad(paths.models_dir),
        transcriber=WhisperTranscriber(paths.models_dir, settings.stt),
        synthesizer=PiperSynthesizer(paths.models_dir, settings.tts.voice),
        player=Player(clock),
    )


class CoreThread:
    """Hilo del núcleo: bucle `asyncio` con el orquestador, la base de datos y la voz."""

    def __init__(
        self,
        config: Config,
        bus: EventBus,
        make_adapters: Callable[[], Adapters],
        on_exit: Callable[[], None],
    ) -> None:
        self._config = config
        self._bus = bus
        self._make_adapters = make_adapters
        self._on_exit = on_exit
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
        app = build_app(self._config, adapters, bus=self._bus)
        self.app = app
        try:
            app.sessions.recover_interrupted()
            app.capture.start()  # el hilo de audio carga sus modelos mientras se carga la voz
            await app.speaker.preload()
            logger.info("Listo en %.1f s", time.monotonic() - started)
            if self._config.settings.startup.open_session_on_start:
                app.orchestrator.submit(fsm.OpenSessionRequested())
            await app.orchestrator.run()
        finally:
            app.capture.stop()
            app.speaker.close()
            close = getattr(adapters.transcriber, "close", None)
            if close is not None:
                close()
            adapters.database.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    platform = create_platform()
    paths = AppPaths.from_platform(platform)
    paths.ensure()
    setup_logging(paths.log_dir, args.log_level or "INFO")
    install_excepthooks()
    logger.info("Jarvis %s arranca", __version__)

    instance = acquire_single_instance(MUTEX_NAME)
    if instance is None:
        return 0
    try:
        return _run(args, platform, paths)
    finally:
        instance.close()
        logger.info("Jarvis termina")


def _run(args: argparse.Namespace, platform: Any, paths: AppPaths) -> int:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from jarvis_assistant.process.tray import TrayController
    from jarvis_assistant.ui.bridge import UiBridge
    from jarvis_assistant.ui.status_window import StatusWindow

    config_module.install_defaults(paths.config_dir)
    config, errors = config_module.load(paths.config_dir)
    for error in errors:
        logger.error("Configuración: %s, clave %s: %s", error.file, error.key, error.reason)
    if args.log_level is None:
        logging.getLogger().setLevel(config.settings.logging.level)

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

    missing = missing_models(paths.models_dir, config.settings.stt.model, config.settings.tts.voice)
    if missing:
        names = ", ".join(str(path) for path in missing)
        logger.error(
            "Faltan modelos en %s: %s. Ejecute el guion de descarga de modelos de la instalación",
            paths.models_dir, names,
        )
        tray.show()
        tray.notify("Jarvis no puede arrancar", "Faltan modelos. Ejecute la descarga de modelos.")
        QTimer.singleShot(_MISSING_MODELS_NOTICE_MS, qt_app.quit)
        qt_app.exec()
        return 1

    window = StatusWindow()
    bridge.eventReceived.connect(window.on_event, Qt.ConnectionType.QueuedConnection)
    bridge.eventReceived.connect(tray.on_event, Qt.ConnectionType.QueuedConnection)
    bridge.exitRequested.connect(qt_app.quit, Qt.ConnectionType.QueuedConnection)
    bridge.attach(bus)
    qt_app.commitDataRequest.connect(lambda _manager: request_quit())

    clock = SystemClock()
    core = CoreThread(
        config,
        bus,
        make_adapters=lambda: real_adapters(config, platform, paths, clock),
        on_exit=bridge.exitRequested.emit,
    )
    core.start()
    tray.show()
    qt_app.exec()

    tray.hide()
    if not core.join(SHUTDOWN_LIMIT_SECONDS):
        logger.warning("El núcleo no ha terminado a tiempo; la sesión se recuperará al arrancar")
    return 0
