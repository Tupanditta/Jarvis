"""CU-03, CU-04 y CU-05 completos con dobles, con sus alternativas (T-1.7).

El grafo es el de `build_app`: FSM, enrutador, sesión, sintetizador y orquestador reales;
modelo de voz, reproductor, reloj y base de datos, dobles. El usuario escribe: cada orden
entra como el evento `TextSubmitted` que publica la caja de texto.
"""
import asyncio
import dataclasses

import pytest

from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from fakes.voice import FakePlayer, FakeSynthesizer
from jarvis_assistant.config import Config, Settings
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.main import Adapters, build_app
from jarvis_assistant.speaker.phrases import PHRASES

APERTURA = PHRASES["ciclo.apertura"][0]
ESCUCHA = PHRASES["ciclo.escucha"][0]
REPOSO = PHRASES["ciclo.reposo"][0]
CIERRE = PHRASES["ciclo.cierre"][0]

S = AssistantState
RECORDED = (
    events.SessionOpened, events.ListeningResumed, events.RestEntered, events.SessionClosed,
    events.AssistantActivityChanged, events.AudioLevel, events.CommandReceived,
    events.SpeechStarted, events.SpeechFinished, events.SessionChanged,
    events.ShowScreenRequested,
)


async def settle() -> None:
    for _ in range(30):
        await asyncio.sleep(0)


class Rig:
    def __init__(self, tmp_path, settings: Settings | None = None) -> None:
        self.clock = FakeClock()
        self.database = Database(":memory:")
        self.database.migrate()
        self.player = FakePlayer(self.clock)
        self.exited = []
        adapters = Adapters(
            platform=FakePlatform(tmp_path),
            clock=self.clock,
            database=self.database,
            synthesizer=FakeSynthesizer(),
            player=self.player,
        )
        config = Config(settings=settings or Settings())
        self.app = build_app(config, adapters, on_exit=lambda: self.exited.append(True))
        self.events: list[events.Event] = []
        for event_type in RECORDED:
            self.app.bus.subscribe(event_type, self.events.append)
        self.sessions = SessionRepository(self.database)
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        await self.app.speaker.preload()
        self.task = asyncio.ensure_future(self.app.orchestrator.run())
        await settle()

    async def stop(self) -> None:
        if self.task is not None and not self.task.done():
            self.task.cancel()
        self.app.speaker.close()
        self.database.close()

    # --- Lo que hace el usuario ---

    async def advance(self, seconds: float) -> None:
        """Avanza el reloj en pasos cortos, dejando correr el núcleo entre ellos."""
        steps = max(1, round(seconds / 0.25))
        for _ in range(steps):
            self.clock.advance(seconds / steps)
            await settle()

    async def write(self, text: str) -> None:
        """El usuario escribe `text` en la caja y pulsa Enter."""
        self.app.bus.publish(events.TextSubmitted(text))
        await settle()

    async def keystroke(self) -> None:
        self.app.bus.publish(events.UserTyping())
        await settle()

    async def wake(self) -> None:
        await self.write("Hey Jarvis")

    async def open_session(self) -> None:
        await self.wake()
        await self.advance(1.0)

    # --- Lo que se observa ---

    @property
    def state(self) -> AssistantState:
        return self.app.machine.state

    def of(self, kind: type) -> list:
        return [event for event in self.events if isinstance(event, kind)]

    def spoken(self) -> list[str]:
        return [event.text for event in self.of(events.SpeechStarted)]

    def activities(self) -> list[Activity]:
        return [event.activity for event in self.of(events.AssistantActivityChanged)]

    def clear(self) -> None:
        self.events.clear()


@pytest.fixture
async def rig(tmp_path):
    rig = Rig(tmp_path)
    await rig.start()
    yield rig
    await rig.stop()


# --- CU-03. Abrir sesión ---------------------------------------------------------------------


async def test_cu03_arranca_dormido(rig):
    assert rig.state is S.DORMIDO
    assert rig.activities() == [Activity.DORMIDO]
    assert not rig.player.is_open


async def test_cu03_flujo_principal(rig):
    await rig.wake()
    # Pasos 2 y 3: sesión creada y frase de apertura sonando.
    assert rig.state is S.LISTENING_COMMAND
    (session,) = rig.sessions.find_open()
    assert session.name == rig.clock.now().astimezone().date().isoformat()
    assert not session.is_important
    assert rig.player.is_open
    assert rig.spoken() == [APERTURA]
    assert rig.of(events.CommandReceived) == [events.CommandReceived("Hey Jarvis", True)]
    assert rig.of(events.SessionOpened) == [events.SessionOpened(session.id, session.name)]
    assert rig.of(events.SessionChanged) == [events.SessionChanged(session.id, session.name, False)]
    assert rig.activities()[-1] is Activity.HABLANDO
    # La transición se publica en el mismo instante en que empieza el audio (RNF-22).
    both = events.SpeechStarted | events.SessionOpened
    order = [type(e) for e in rig.events if isinstance(e, both)]
    assert order == [events.SpeechStarted, events.SessionOpened]

    await rig.advance(1.0)
    # Paso 5: escucha de órdenes.
    assert rig.activities()[-1] is Activity.ESCUCHANDO
    assert rig.sessions.get(session.id).closed_at is None


@pytest.mark.parametrize("text", ["hey jarvis", "Hey, Jarvis.", "hey jarbis", "jarvis"])
async def test_cu03_la_frase_de_activacion_admite_variantes_y_erratas(rig, text):
    await rig.write(text)
    assert rig.state is S.LISTENING_COMMAND
    assert len(rig.sessions.find_open()) == 1


async def test_cu03_durante_la_frase_se_publica_el_nivel_de_la_voz(rig):
    await rig.wake()
    await rig.advance(0.5)
    assert events.AudioLevel(0.5, "assistant") in rig.of(events.AudioLevel)


async def test_cu03_mientras_escucha_no_se_publica_ningun_nivel(rig):
    await rig.open_session()
    await rig.advance(1.0)
    rig.clear()
    await rig.advance(2.0)
    assert rig.of(events.AudioLevel) == []


async def test_cu03_a1_hey_jarvis_en_reposo_vuelve_a_escucha_sin_sesion_nueva(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.wake()
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == [ESCUCHA]
    assert rig.of(events.ListeningResumed) == [events.ListeningResumed(silent=False)]
    assert rig.of(events.SessionOpened) == []
    assert len(rig.sessions.find_open()) == 1
    await rig.advance(1.0)
    await rig.advance(30.0)  # la cuenta de inactividad vuelve a empezar al terminar la frase
    assert rig.state is S.IDLE


async def test_cu03_a2_hey_jarvis_con_la_escucha_activa_no_habla_y_reinicia_la_cuenta(rig):
    await rig.open_session()
    await rig.advance(20.0)
    rig.clear()
    await rig.wake()
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.ListeningResumed) == []
    await rig.advance(20.0)
    assert rig.state is S.LISTENING_COMMAND  # 40 s desde la apertura, 20 desde «Hey Jarvis»
    await rig.advance(10.5)
    assert rig.state is S.IDLE


@pytest.mark.parametrize(
    "text", ["gracias jarvis", "buenas noches jarvis", "hola", "abre el navegador", "", "   "]
)
async def test_cu03_a3_otra_frase_en_modo_dormido_no_tiene_efecto(rig, text):
    await rig.write(text)
    assert rig.state is S.DORMIDO
    assert rig.spoken() == []
    assert rig.of(events.CommandReceived) == []
    assert rig.sessions.find_open() == []


async def test_cu03_a4_lo_escrito_durante_la_frase_de_apertura_se_atiende_al_terminar(rig):
    await rig.wake()
    await rig.write("gracias jarvis")  # la frase de apertura sigue sonando
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == [APERTURA]
    await rig.advance(1.0)
    assert rig.state is S.IDLE
    assert rig.spoken() == [APERTURA, REPOSO]


async def test_cu03_a5_hey_jarvis_tras_el_cierre_abre_una_sesion_nueva_al_instante(rig):
    await rig.open_session()
    first = rig.sessions.find_open()[0].id
    await rig.write("buenas noches jarvis")
    assert rig.state is S.DORMIDO  # de inmediato, sin esperar a la frase
    await rig.wake()  # llega mientras suena la frase de cierre
    await rig.advance(1.0)
    assert rig.state is S.LISTENING_COMMAND
    (second,) = rig.sessions.find_open()
    assert second.id != first
    assert rig.spoken()[-2:] == [CIERRE, APERTURA]
    assert rig.player.is_open


async def test_cu03_a6_apertura_desde_la_bandeja(rig):
    rig.app.bus.publish(events.OpenSessionRequested())
    await settle()
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == [APERTURA]
    rig.app.bus.publish(events.OpenSessionRequested())  # con sesión: sin efecto
    await rig.advance(1.0)
    assert len(rig.sessions.find_open()) == 1


# --- CU-04. Pasar a reposo -------------------------------------------------------------------


async def test_cu04_flujo_principal(rig):
    await rig.open_session()
    session = rig.sessions.find_open()[0]
    rig.clear()
    await rig.write("Gracias, Jarvis.")
    assert rig.state is S.IDLE
    assert rig.of(events.CommandReceived) == [events.CommandReceived("Gracias, Jarvis.", True)]
    assert rig.spoken() == [REPOSO]
    assert rig.of(events.RestEntered) == [events.RestEntered()]
    await rig.advance(1.0)
    assert rig.activities()[-1] is Activity.REPOSO
    assert rig.sessions.find_open() == [session]  # la sesión no cambia
    assert rig.player.is_open
    rig.clear()
    await rig.advance(2.0)
    assert rig.of(events.AudioLevel) == [events.AudioLevel(0.0, "none")]  # y deja de publicarse


async def test_cu04_a1_treinta_segundos_sin_escribir(rig):
    await rig.open_session()
    await rig.advance(29.5)
    assert rig.state is S.LISTENING_COMMAND
    await rig.advance(1.0)
    assert rig.state is S.IDLE
    assert rig.spoken()[-1] == REPOSO
    assert rig.of(events.RestEntered) == [events.RestEntered()]


async def test_cu04_a1_el_plazo_de_inactividad_es_configurable(tmp_path):
    settings = Settings()
    settings = dataclasses.replace(
        settings, input=dataclasses.replace(settings.input, inactivity_to_idle_seconds=10.0)
    )
    rig = Rig(tmp_path, settings)
    await rig.start()
    try:
        await rig.open_session()
        await rig.advance(9.5)
        assert rig.state is S.LISTENING_COMMAND
        await rig.advance(1.0)
        assert rig.state is S.IDLE
    finally:
        await rig.stop()


async def test_cu04_a1_teclear_reinicia_la_cuenta(rig):
    await rig.open_session()
    await rig.advance(20.0)
    await rig.keystroke()
    await rig.advance(20.0)
    assert rig.state is S.LISTENING_COMMAND
    await rig.advance(10.5)
    assert rig.state is S.IDLE


async def test_cu04_teclear_en_reposo_o_en_dormido_no_tiene_efecto(rig):
    await rig.keystroke()
    await rig.advance(40.0)
    assert rig.state is S.DORMIDO and rig.spoken() == []
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.keystroke()
    await rig.advance(40.0)
    assert rig.state is S.IDLE and rig.spoken() == []


async def test_cu04_a2_frase_parecida_se_muestra_como_no_reconocida_y_reinicia_la_cuenta(rig):
    await rig.open_session()
    await rig.advance(20.0)
    rig.clear()
    await rig.write("Muchas gracias Jarvis por todo")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.CommandReceived) == [
        events.CommandReceived("Muchas gracias Jarvis por todo", False)
    ]
    assert rig.activities() == []  # sigue escuchando: la actividad no cambia
    await rig.advance(20.0)
    assert rig.state is S.LISTENING_COMMAND
    await rig.advance(10.5)
    assert rig.state is S.IDLE


@pytest.mark.parametrize("text", ["", "   ", "\t"])
async def test_cu04_un_envio_vacio_no_se_muestra_ni_reinicia_la_cuenta(rig, text):
    await rig.open_session()
    await rig.advance(20.0)
    rig.clear()
    await rig.write(text)
    assert rig.of(events.CommandReceived) == []
    await rig.advance(10.5)
    assert rig.state is S.IDLE


async def test_cu04_en_reposo_gracias_jarvis_y_cancelar_no_tienen_efecto(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.write("gracias jarvis")
    await rig.write("cancelar")
    await rig.write("   ")
    assert rig.state is S.IDLE
    assert rig.spoken() == [] and rig.of(events.CommandReceived) == []


async def test_cu04_en_reposo_una_orden_despierta_en_silencio_y_se_ejecuta(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.write("muestra la pantalla")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.ListeningResumed) == [events.ListeningResumed(silent=True)]
    assert rig.of(events.ShowScreenRequested) == [events.ShowScreenRequested(visible=True)]
    await rig.advance(30.5)
    assert rig.state is S.IDLE


async def test_cu04_en_reposo_un_texto_no_reconocido_despierta_y_se_muestra(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.write("qué tiempo hace hoy")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.CommandReceived) == [
        events.CommandReceived("qué tiempo hace hoy", recognized=False)
    ]


# --- CU-05. Cerrar sesión --------------------------------------------------------------------


async def test_cu05_flujo_principal(rig):
    await rig.open_session()
    session = rig.sessions.find_open()[0]
    pending = ActivityRepository(rig.database).add(session.id, "comandos", "gcc", rig.clock.now())
    rig.clear()
    await rig.write("Buenas noches, Jarvis.")
    assert rig.state is S.DORMIDO
    closed = rig.sessions.get(session.id)
    assert closed.closed_at == rig.clock.now() and closed.close_reason == "voz"
    (activity,) = ActivityRepository(rig.database).of_session(session.id)
    assert activity.id == pending and activity.status == "error"
    assert rig.spoken() == [CIERRE]
    assert rig.of(events.SessionClosed) == [events.SessionClosed()]
    await rig.advance(1.0)
    assert rig.activities()[-1] is Activity.DORMIDO
    assert not rig.player.is_open
    assert rig.exited == []  # cerrar la sesión nunca termina el proceso
    assert not rig.task.done()
    rig.clear()
    await rig.advance(40.0)
    assert rig.of(events.RestEntered) == [] and rig.spoken() == []


async def test_cu05_a1_cierre_desde_reposo(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    await rig.write("buenas noches jarvis")
    assert rig.state is S.DORMIDO
    assert rig.sessions.find_open() == []
    assert rig.spoken()[-1] == CIERRE


async def test_cu05_a4_buenas_noches_sin_jarvis_se_ignora(rig):
    await rig.open_session()
    await rig.write("buenas noches")
    assert rig.state is S.LISTENING_COMMAND
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    await rig.write("buenas noches")
    assert rig.state is S.LISTENING_COMMAND  # en reposo despierta como texto no reconocido
    assert len(rig.sessions.find_open()) == 1


@pytest.mark.parametrize("resting", [False, True])
async def test_cu05_a5_salir_desde_la_bandeja_cierra_sin_frase_y_termina(rig, resting):
    await rig.open_session()
    session = rig.sessions.find_open()[0]
    if resting:
        await rig.write("gracias jarvis")
        await rig.advance(1.0)
    rig.clear()
    rig.app.bus.publish(events.QuitRequested())
    await settle()
    assert rig.sessions.get(session.id).close_reason == "salida"
    assert rig.spoken() == []
    assert rig.of(events.SessionClosed) == [events.SessionClosed()]
    assert rig.exited == [True]
    assert rig.task.done()
    assert not rig.player.is_open


async def test_salir_en_dormido_termina_el_proceso(rig):
    rig.app.orchestrator.submit(fsm.ShutdownRequested())
    await settle()
    assert rig.exited == [True] and rig.task.done()
    assert rig.sessions.find_open() == []


# --- Robustez --------------------------------------------------------------------------------


async def test_un_error_al_atender_una_entrada_no_detiene_el_nucleo(rig, caplog):
    def broken(text, state, dialogue=None):
        raise RuntimeError("fallo del enrutador")

    await rig.open_session()
    rig.app.router.route = broken
    await rig.write("lo que sea")
    assert "Error al atender TextSubmitted" in caplog.text
    assert not rig.task.done()
    await rig.advance(30.5)  # la cuenta de inactividad sigue en marcha
    assert rig.state is S.IDLE


async def test_una_entrada_desconocida_se_registra_y_se_ignora(rig, caplog):
    rig.app.orchestrator.submit(object())
    await settle()
    assert "Entrada desconocida" in caplog.text
    await rig.open_session()
    assert rig.state is S.LISTENING_COMMAND


async def test_un_texto_muy_largo_o_con_saltos_de_linea_se_trata_como_no_reconocido(rig):
    await rig.open_session()
    rig.clear()
    await rig.write("qué tiempo\nhace hoy " * 500)
    assert rig.state is S.LISTENING_COMMAND
    assert len(rig.of(events.CommandReceived)) == 1
    assert not rig.of(events.CommandReceived)[0].recognized


# --- Intenciones del núcleo: mostrar y ocultar la pantalla (T-2.7) ---------------------------


async def test_muestra_y_oculta_la_pantalla_sin_voz_y_reiniciando_la_cuenta(rig):
    await rig.open_session()
    await rig.advance(20.0)
    rig.clear()
    await rig.write("oculta la pantalla")
    assert rig.of(events.ShowScreenRequested) == [events.ShowScreenRequested(False)]
    assert rig.of(events.CommandReceived) == [events.CommandReceived("oculta la pantalla", True)]
    await rig.write("muestra la pantalla")
    assert rig.of(events.ShowScreenRequested)[-1] == events.ShowScreenRequested(True)
    assert rig.spoken() == []  # sin voz
    await rig.advance(20.0)
    assert rig.state is S.LISTENING_COMMAND  # la orden cuenta como actividad
    await rig.advance(10.5)
    assert rig.state is S.IDLE
