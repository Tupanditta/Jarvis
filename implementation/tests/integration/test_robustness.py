"""Robustez (T-7.3): el asistente arranca y atiende con cada fallo del entorno.

Cada caso monta el grafo real de `build_app` con el fallo y recorre una sesión entera:
«Hey Jarvis», una orden y «Buenas noches Jarvis». Los fallos y su comportamiento:

- Altavoz ausente (sintetizador.md): la frase se da por dicha tras su duración y se registra.
- Base de datos dañada (persistencia.md): se aparta, se crea otra y se registra.
- Configuración inválida al arrancar (configuracion.md): los predeterminados de ese archivo.
- Falta de un modelo (proceso.md): el proceso sale con un mensaje claro en el registro.

La recarga de una configuración inválida al abrir sesión la cubre `test_orders.py`.
"""
import asyncio
import logging

from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from fakes.voice import FakePlayer, FakeSynthesizer
from jarvis_assistant import config as config_module
from jarvis_assistant.config import Config
from jarvis_assistant.core import events
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.repositories import SessionRepository
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.main import Adapters, build_app, report_missing_models
from jarvis_assistant.paths import AppPaths, required_models
from jarvis_assistant.speaker.player import Player

S = AssistantState


async def settle() -> None:
    for _ in range(30):
        await asyncio.sleep(0)


async def full_session(tmp_path, *, database=None, player=None, config=None) -> tuple:
    """Abre sesión, le pone nombre, cierra y devuelve lo dicho y la sesión guardada."""
    clock = FakeClock()
    if database is None:
        database = Database(":memory:")
        database.migrate()
    adapters = Adapters(
        platform=FakePlatform(tmp_path),
        clock=clock,
        database=database,
        synthesizer=FakeSynthesizer(),
        player=player(clock) if player else FakePlayer(clock),
    )
    app = build_app(config or Config(), adapters)
    spoken: list[str] = []
    app.bus.subscribe(events.SpeechStarted, lambda event: spoken.append(event.text))
    await app.speaker.preload()
    task = asyncio.ensure_future(app.orchestrator.run())

    async def write(text: str) -> None:
        app.bus.publish(events.TextSubmitted(text))
        await settle()
        for _ in range(16):  # deja sonar la respuesta según el reloj falso
            clock.advance(0.25)
            await settle()

    try:
        await settle()
        await write("Hey Jarvis")
        assert app.machine.state is S.LISTENING_COMMAND
        await write("llama a la sesión prueba")  # una actividad: la sesión se guarda
        assert app.machine.state is S.LISTENING_COMMAND
        await write("Buenas noches Jarvis")
        assert app.machine.state is S.DORMIDO
        sessions = SessionRepository(database)
        stored = sessions.get(1)
    finally:
        task.cancel()
        app.speaker.close()
        database.close()
    return spoken, stored


async def test_sin_altavoz_la_sesion_funciona_y_se_registra(tmp_path, caplog):
    def no_device(**_kwargs):
        raise RuntimeError("no hay dispositivo de salida")

    with caplog.at_level(logging.WARNING):
        spoken, stored = await full_session(
            tmp_path, player=lambda clock: Player(clock, no_device)
        )
    assert len(spoken) >= 3  # apertura, respuesta a la orden y cierre, en los subtítulos
    assert stored.close_reason is not None
    assert "No se puede abrir el dispositivo de salida" in caplog.text


async def test_con_la_base_danada_se_aparta_y_el_asistente_arranca(tmp_path, caplog):
    path = tmp_path / "datos" / "jarvis.db"
    path.parent.mkdir()
    path.write_bytes(b"no es una base de datos" * 200)
    with caplog.at_level(logging.ERROR):
        database = Database(path)
        database.migrate()
        _spoken, stored = await full_session(tmp_path, database=database)
    assert stored.close_reason is not None
    assert [file.name.split("-")[0] for file in path.parent.glob("jarvis.db.corrupt-*")] == [
        "jarvis.db.corrupt"
    ]
    assert "dañada" in caplog.text


async def test_con_la_configuracion_invalida_arranca_con_los_predeterminados(tmp_path):
    folder = tmp_path / "config"
    folder.mkdir()
    (folder / "settings.toml").write_text(
        "[input]\ninactivity_to_idle_seconds = 1\n", encoding="utf-8"
    )
    (folder / "protocols.toml").write_text("[[protocol\n", encoding="utf-8")
    config, errors = config_module.load(folder)
    assert {error.file for error in errors} == {"settings.toml", "protocols.toml"}
    defaults = config_module.default_config()
    assert config.settings == defaults.settings and config.protocols == defaults.protocols
    _spoken, stored = await full_session(tmp_path, config=config)
    assert stored.close_reason is not None


def test_sin_un_modelo_el_mensaje_del_registro_dice_cual_y_como_resolverlo(tmp_path, caplog):
    paths = AppPaths(
        data_dir=tmp_path / "datos", config_dir=tmp_path / "config",
        log_dir=tmp_path / "registro", models_dir=tmp_path / "models",
    )
    with caplog.at_level(logging.ERROR):
        missing = report_missing_models(paths, "es_ES-davefx-medium")
    assert missing == list(required_models("es_ES-davefx-medium"))
    assert "Faltan modelos" in caplog.text and "descarga de modelos" in caplog.text
    assert str(missing[0]) in caplog.text


def test_con_los_modelos_no_se_registra_nada(tmp_path, caplog):
    models = tmp_path / "models"
    for relative in required_models("es_ES-davefx-medium"):
        (models / relative).parent.mkdir(parents=True, exist_ok=True)
        (models / relative).write_bytes(b"modelo")
    paths = AppPaths(
        data_dir=tmp_path, config_dir=tmp_path, log_dir=tmp_path, models_dir=models
    )
    with caplog.at_level(logging.ERROR):
        assert report_missing_models(paths, "es_ES-davefx-medium") == []
    assert caplog.text == ""
