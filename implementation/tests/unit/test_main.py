"""Composición y arranque (proceso.md)."""
import threading
import time

import pytest

from fakes.audio import FakeMicrophone, FakeVad, FakeWakeWord
from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from fakes.voice import FakePlayer, FakeSynthesizer, FakeTranscriber
from jarvis_assistant import main as main_module
from jarvis_assistant.audio_capture.types import CaptureMode
from jarvis_assistant.config import Config
from jarvis_assistant.core import events
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.repositories import SessionRepository
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.main import ACTION_MODULES, CoreThread, build_app, parse_args
from jarvis_assistant.os_adapters.windows import WindowsAdapter


def fake_adapters(tmp_path, database=None):
    clock = FakeClock()
    if database is None:
        database = Database(":memory:")
        database.migrate()
    return main_module.Adapters(
        platform=FakePlatform(tmp_path),
        clock=clock,
        database=database,
        microphone=FakeMicrophone(),
        wakeword=FakeWakeWord(),
        vad=FakeVad(),
        transcriber=FakeTranscriber(),
        synthesizer=FakeSynthesizer(),
        player=FakePlayer(clock),
    )


def test_build_app_construye_el_grafo_completo_sin_hilos_ni_dispositivos(tmp_path):
    adapters = fake_adapters(tmp_path)
    threads = threading.active_count()
    app = build_app(Config(), adapters)
    assert threading.active_count() == threads
    assert app.machine.state is AssistantState.DORMIDO
    assert app.capture.mode is CaptureMode.WAKE_ONLY
    assert app.orchestrator.state is AssistantState.DORMIDO
    assert adapters.microphone.opened == 0
    assert not adapters.synthesizer.loaded and not adapters.transcriber.loaded
    assert not adapters.player.is_open
    assert app.sessions.current is None
    assert ACTION_MODULES == []  # todavía no hay módulos de acción que registrar
    app.speaker.close()
    adapters.database.close()


def test_build_app_usa_el_bus_que_se_le_pasa(tmp_path):
    bus = EventBus()
    adapters = fake_adapters(tmp_path)
    app = build_app(Config(), adapters, bus=bus)
    assert app.bus is bus
    app.speaker.close()
    adapters.database.close()


def test_argumentos():
    assert parse_args([]).log_level is None
    assert parse_args(["--log-level", "DEBUG"]).log_level == "DEBUG"
    with pytest.raises(SystemExit):
        parse_args(["--log-level", "RUIDOSO"])


def test_carpetas_de_windows(tmp_path):
    adapter = WindowsAdapter(
        {"LOCALAPPDATA": str(tmp_path / "Local"), "APPDATA": str(tmp_path / "Roaming")}
    )
    assert adapter.data_dir() == tmp_path / "Local" / "Jarvis" / "data"
    assert adapter.log_dir() == tmp_path / "Local" / "Jarvis" / "logs"
    assert adapter.config_dir() == tmp_path / "Roaming" / "Jarvis" / "config"
    bare = WindowsAdapter({}, home=tmp_path)
    assert bare.data_dir() == tmp_path / "AppData" / "Local" / "Jarvis" / "data"
    assert bare.config_dir() == tmp_path / "AppData" / "Roaming" / "Jarvis" / "config"


def test_una_segunda_instancia_sale_sin_efectos(tmp_path, monkeypatch):
    platform = FakePlatform(tmp_path)
    monkeypatch.setattr(main_module, "create_platform", lambda: platform)
    monkeypatch.setattr(main_module, "acquire_single_instance", lambda name: None)
    monkeypatch.setattr(main_module, "setup_logging", lambda *args: None)
    monkeypatch.setattr(main_module, "install_excepthooks", lambda: None)
    monkeypatch.setattr(main_module, "_run", lambda *args: pytest.fail("no debe arrancar"))
    assert main_module.main([]) == 0
    assert not (platform.data_dir() / "jarvis.db").exists()


def test_el_nucleo_recupera_al_arrancar_y_al_salir_deja_la_sesion_cerrada(tmp_path):
    path = tmp_path / "jarvis.db"
    seed = Database(path)
    seed.migrate()
    orphan = SessionRepository(seed).create("huérfana", FakeClock().now())
    seed.close()
    made = {}

    def make_adapters():
        database = Database(path)
        database.migrate()
        made["adapters"] = fake_adapters(tmp_path, database)
        return made["adapters"]

    bus = EventBus()
    exited = threading.Event()
    core = CoreThread(Config(), bus, make_adapters, exited.set)
    core.start()
    bus.publish_threadsafe(events.OpenSessionRequested())
    assert _until(lambda: core.app is not None and core.app.speaker.speaking)
    adapters = made["adapters"]
    assert adapters.synthesizer.loaded
    assert _until(lambda: adapters.wakeword.loaded)  # el hilo de audio está en marcha
    bus.publish_threadsafe(events.QuitRequested())
    # La frase de apertura suena según el reloj falso: se deja terminar.
    core.app.orchestrator._loop.call_soon_threadsafe(adapters.clock.advance, 1.0)
    assert exited.wait(3)
    assert core.join(3)

    check = Database(path)
    sessions = SessionRepository(check)
    reasons = [sessions.get(session_id).close_reason for session_id in (orphan, orphan + 1)]
    check.close()
    assert reasons == ["interrumpida", "salida"]


def test_un_fallo_al_arrancar_el_nucleo_termina_el_proceso(caplog):
    def broken():
        raise RuntimeError("base de datos inaccesible")

    exited = threading.Event()
    core = CoreThread(Config(), EventBus(), broken, exited.set)
    core.start()
    assert exited.wait(3) and core.join(3)
    assert "El núcleo ha terminado con un error" in caplog.text


def _until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.005)
    return False
