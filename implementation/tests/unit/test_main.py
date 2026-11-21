"""Composición y arranque (proceso.md)."""
import dataclasses
import threading
import time

import pytest

from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from fakes.voice import FakePlayer, FakeSynthesizer
from jarvis_assistant import main as main_module
from jarvis_assistant.config import Config
from jarvis_assistant.core import events
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository
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
        synthesizer=FakeSynthesizer(),
        player=FakePlayer(clock),
    )


def test_build_app_construye_el_grafo_completo_sin_hilos_ni_dispositivos(tmp_path):
    adapters = fake_adapters(tmp_path)
    threads = threading.active_count()
    app = build_app(Config(), adapters)
    assert threading.active_count() == threads
    assert app.machine.state is AssistantState.DORMIDO
    assert app.orchestrator.state is AssistantState.DORMIDO
    assert not adapters.synthesizer.loaded
    assert not adapters.player.is_open
    assert app.sessions.current is None
    assert [module.name for module in ACTION_MODULES] == [
        "comandos", "apertura", "busqueda", "creacion", "historial", "recordatorio",
        "protocolos", "catalogo", "permisos", "credenciales", "perfiles",
    ]  # fmt: skip
    assert set(app.orchestrator.modules) == {
        "sesion", "comandos", "apertura", "busqueda", "creacion", "historial", "recordatorio",
        "protocolos", "catalogo", "permisos", "credenciales", "perfiles",
    }  # fmt: skip
    assert app.orchestrator.modules["sesion"] is app.sessions
    app.speaker.close()
    adapters.database.close()


def test_build_app_usa_el_bus_que_se_le_pasa(tmp_path):
    bus = EventBus()
    adapters = fake_adapters(tmp_path)
    app = build_app(Config(), adapters, bus=bus)
    assert app.bus is bus
    app.speaker.close()
    adapters.database.close()


def test_el_proceso_no_tiene_entrada_por_voz(tmp_path):
    fields = {field.name for field in dataclasses.fields(main_module.Adapters)}
    assert fields == {"platform", "clock", "database", "synthesizer", "player", "scheduler"}
    assert not hasattr(main_module.App, "capture")


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


def test_el_nucleo_recupera_al_arrancar_y_no_guarda_las_sesiones_vacias(tmp_path):
    path = tmp_path / "jarvis.db"
    seed = Database(path)
    seed.migrate()
    now = FakeClock().now()
    seeded = SessionRepository(seed)
    empty_closed = seeded.create("vacía y cerrada", now)  # guardada antes de esta regla
    seeded.close(empty_closed, now, "voz")
    orphan = seeded.create("huérfana", now)
    ActivityRepository(seed).add(orphan, "comandos", "ls", now)
    seeded.create("vacía y abierta", now)
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
    bus.publish_threadsafe(events.TextSubmitted("Hey Jarvis"))  # como lo envía la ventana
    assert _until(lambda: core.app is not None and core.app.speaker.speaking)
    adapters = made["adapters"]
    assert adapters.synthesizer.loaded
    bus.publish_threadsafe(events.QuitRequested())
    # La frase de apertura suena según el reloj falso: se deja terminar.
    core.app.orchestrator._loop.call_soon_threadsafe(adapters.clock.advance, 1.0)
    assert exited.wait(3)
    assert core.join(3)

    check = Database(path)
    sessions = SessionRepository(check).visible_history(None)
    stored = [(s.id, s.name, s.close_reason) for s in sessions]
    activities = ActivityRepository(check).of_session(1)
    check.close()
    # Solo queda la huérfana con su actividad, renumerada a la 1. Las vacías (la cerrada, la
    # abierta y la de esta ejecución, que se cierra al salir sin actividades) no se guardan.
    assert stored == [(1, "huérfana", "interrumpida")]
    assert [a.module for a in activities] == ["comandos"]


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


def test_argumentos_de_la_interfaz():
    assert not parse_args([]).preview and not parse_args([]).ui_debug
    args = parse_args(["--preview", "--ui-debug"])
    assert args.preview and args.ui_debug


def test_la_vista_previa_no_arranca_el_nucleo_ni_toma_la_instancia(tmp_path, monkeypatch):
    platform = FakePlatform(tmp_path)
    started = []
    monkeypatch.setattr(main_module, "create_platform", lambda: platform)
    monkeypatch.setattr(main_module, "setup_logging", lambda *args: None)
    monkeypatch.setattr(main_module, "install_excepthooks", lambda: None)
    monkeypatch.setattr(
        main_module, "acquire_single_instance", lambda name: pytest.fail("sin instancia única")
    )
    monkeypatch.setattr(main_module, "_run", lambda *args: pytest.fail("sin núcleo"))
    monkeypatch.setattr(main_module, "_run_preview", lambda args, paths: started.append(args) or 0)
    assert main_module.main(["--preview"]) == 0
    assert started and started[0].preview
    assert not (platform.data_dir() / "jarvis.db").exists()


def test_reiniciar_al_acedor_lo_desactiva_y_conserva_las_contrasenas(tmp_path, capsys):
    from jarvis_assistant import main as main_module
    from jarvis_assistant.core.custody import generate_keys
    from jarvis_assistant.core.database import Database
    from jarvis_assistant.core.security import (
        AccessOrigin,
        AttemptOutcome,
        ProfileVault,
        hash_password,
    )
    from jarvis_assistant.paths import AppPaths

    paths = AppPaths(tmp_path / "datos", tmp_path / "config", tmp_path / "log", tmp_path / "m")
    paths.ensure()
    db = Database(paths.db_path)
    db.migrate()
    vault = ProfileVault(db)
    vault.install_admin(hash_password("maestra-1234"), *generate_keys("maestra-1234"))
    vault.set_password_hash("trabajo", hash_password("clave-trabajo"))
    db.close()

    assert main_module.parse_args(["--reiniciar-acedor"]).reset_admin
    assert main_module.reset_admin(paths) == 0
    assert "Acedor reiniciado" in capsys.readouterr().out

    db = Database(paths.db_path)
    vault = ProfileVault(db)
    assert not vault.admin_active()
    assert vault.attempt("trabajo", "clave-trabajo", AccessOrigin.LOGIN) is (
        AttemptOutcome.GRANTED
    )
    db.close()
