"""CU-03, CU-04 y CU-05 completos con dobles, con sus alternativas (T-1.7).

El grafo es el de `build_app`: FSM, enrutador, sesión, sintetizador y orquestador reales;
micrófono, modelos, voz, reloj y base de datos, dobles.
"""
import asyncio
import dataclasses
from types import SimpleNamespace

import numpy as np
import pytest

from fakes.audio import FakeMicrophone, FakeVad, FakeWakeWord
from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from fakes.voice import FakePlayer, FakeSynthesizer, FakeTranscriber
from jarvis_assistant.audio_capture.types import CaptureMode, Utterance, WakeWordDetected
from jarvis_assistant.config import Config, Settings
from jarvis_assistant.core import events
from jarvis_assistant.core import state_machine as fsm
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.main import Adapters, build_app

S = AssistantState
PCM = np.full(16000, 500, dtype=np.int16)
RECORDED = (
    events.SessionOpened, events.ListeningResumed, events.RestEntered, events.SessionClosed,
    events.AssistantActivityChanged, events.MicStatusChanged, events.AudioLevel,
    events.TranscriptReady, events.SpeechStarted, events.SpeechFinished, events.SessionChanged,
)


async def settle() -> None:
    for _ in range(30):
        await asyncio.sleep(0)


class Rig:
    def __init__(self, tmp_path, settings: Settings | None = None) -> None:
        self.clock = FakeClock()
        self.database = Database(":memory:")
        self.database.migrate()
        self.transcriber = FakeTranscriber()
        self.player = FakePlayer(self.clock)
        self.exited = []
        adapters = Adapters(
            platform=FakePlatform(tmp_path),
            clock=self.clock,
            database=self.database,
            microphone=FakeMicrophone(),
            wakeword=FakeWakeWord(),
            vad=FakeVad(),
            transcriber=self.transcriber,
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

    async def wake(self) -> None:
        self.app.orchestrator.submit(WakeWordDetected(self.clock.monotonic()))
        await settle()

    async def say(self, text: str, *, restricted: bool = False, epoch: int | None = None) -> None:
        self.transcriber.texts.append(text)
        now = self.clock.monotonic()
        epoch = self.app.orchestrator.epoch if epoch is None else epoch
        self.app.orchestrator.submit(Utterance(PCM, now - 1, now, epoch, restricted))
        await settle()

    async def open_session(self) -> None:
        await self.wake()
        await self.advance(1.0)

    # --- Lo que se observa ---

    @property
    def state(self) -> AssistantState:
        return self.app.machine.state

    @property
    def mode(self) -> CaptureMode:
        return self.app.capture.mode

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


async def test_cu03_arranca_dormido_atendiendo_solo_la_palabra_de_activacion(rig):
    assert rig.state is S.DORMIDO
    assert rig.mode is CaptureMode.WAKE_ONLY
    assert rig.activities() == [Activity.DORMIDO]
    assert not rig.player.is_open
    assert not rig.transcriber.loaded


async def test_cu03_flujo_principal(rig):
    await rig.wake()
    # Pasos 2 y 3: sesión creada, frase de apertura sonando, transcriptor cargándose.
    assert rig.state is S.LISTENING_COMMAND
    (session,) = rig.sessions.find_open()
    assert session.name == rig.clock.now().astimezone().date().isoformat()
    assert not session.is_important
    assert rig.player.is_open
    assert rig.transcriber.loaded
    assert rig.spoken() == ["Sesión iniciada. Le escucho."]
    assert rig.mode is CaptureMode.MUTED
    assert rig.of(events.SessionOpened) == [events.SessionOpened(session.id, session.name)]
    assert rig.of(events.SessionChanged) == [events.SessionChanged(session.id, session.name, False)]
    assert rig.activities()[-1] is Activity.HABLANDO
    # La transición se publica en el mismo instante en que empieza el audio (RNF-22).
    both = events.SpeechStarted | events.SessionOpened
    order = [type(e) for e in rig.events if isinstance(e, both)]
    assert order == [events.SpeechStarted, events.SessionOpened]

    await rig.advance(1.0)
    # Paso 5: escucha de órdenes, con la captura reabierta 0,3 s después de la frase.
    assert rig.activities()[-1] is Activity.ESCUCHANDO
    assert rig.mode is CaptureMode.COMMANDS
    assert rig.app.capture._mode_state[1] == pytest.approx(rig.clock.monotonic() + 0.3)
    assert rig.sessions.get(session.id).closed_at is None


async def test_cu03_el_nivel_del_microfono_se_publica_a_20_hz_mientras_escucha(rig):
    await rig.open_session()
    rig.clear()
    rig.app.capture._level = 0.4
    await rig.advance(1.0)
    levels = rig.of(events.AudioLevel)
    assert 19 <= len(levels) <= 21
    assert set(levels) == {events.AudioLevel(0.4, "mic")}


async def test_cu03_durante_la_frase_se_publica_el_nivel_de_la_voz(rig):
    await rig.wake()
    await rig.advance(0.5)
    assert events.AudioLevel(0.5, "assistant") in rig.of(events.AudioLevel)


async def test_cu03_a1_hey_jarvis_en_reposo_vuelve_a_escucha_sin_sesion_nueva(rig):
    await rig.open_session()
    await rig.say("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.wake()
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == ["Le escucho."]
    assert rig.of(events.ListeningResumed) == [events.ListeningResumed(silent=False)]
    assert rig.of(events.SessionOpened) == []
    assert len(rig.sessions.find_open()) == 1
    await rig.advance(1.0)
    assert rig.mode is CaptureMode.COMMANDS
    await rig.advance(30.0)  # la cuenta de silencio vuelve a empezar al terminar la frase
    assert rig.state is S.IDLE


async def test_cu03_a2_hey_jarvis_con_la_escucha_activa_se_ignora_y_reinicia_la_cuenta(rig):
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


@pytest.mark.parametrize("text", ["gracias jarvis", "buenas noches jarvis", "jarvis", "hola"])
async def test_cu03_a3_otra_frase_en_modo_dormido_no_tiene_efecto(rig, text):
    await rig.say(text)
    await rig.say(text, restricted=True)
    assert rig.state is S.DORMIDO
    assert rig.transcriber.calls == []
    assert rig.spoken() == []
    assert rig.sessions.find_open() == []


async def test_cu03_a4_durante_la_frase_de_apertura_no_se_atiende_al_microfono(rig):
    await rig.wake()
    assert rig.mode is CaptureMode.MUTED
    await rig.advance(0.5)
    assert rig.mode is CaptureMode.MUTED
    await rig.advance(0.5)
    assert rig.mode is CaptureMode.COMMANDS
    await rig.say("gracias jarvis")  # al terminar, se atiende con normalidad
    assert rig.state is S.IDLE


async def test_cu03_a5_hey_jarvis_tras_el_cierre_abre_una_sesion_nueva_al_instante(rig):
    await rig.open_session()
    first = rig.sessions.find_open()[0].id
    await rig.say("buenas noches jarvis")
    assert rig.state is S.DORMIDO  # de inmediato, sin esperar a la frase
    await rig.wake()  # llega mientras suena la frase de cierre
    await rig.advance(1.0)
    assert rig.state is S.LISTENING_COMMAND
    (second,) = rig.sessions.find_open()
    assert second.id != first
    assert rig.spoken()[-2:] == ["Buenas noches. Sesión cerrada.", "Sesión iniciada. Le escucho."]
    assert rig.player.is_open and rig.transcriber.loaded


async def test_cu03_a6_apertura_desde_la_bandeja(rig):
    rig.app.bus.publish(events.OpenSessionRequested())
    await settle()
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == ["Sesión iniciada. Le escucho."]
    rig.app.bus.publish(events.OpenSessionRequested())  # con sesión: sin efecto
    await rig.advance(1.0)
    assert len(rig.sessions.find_open()) == 1


async def test_cu03_a7_microfono_no_disponible(rig):
    rig.app.orchestrator.submit(events.MicStatusChanged(False))
    await settle()
    assert rig.of(events.MicStatusChanged) == [events.MicStatusChanged(False)]
    rig.app.bus.publish(events.OpenSessionRequested())
    await rig.advance(1.0)
    assert rig.state is S.LISTENING_COMMAND


# --- CU-04. Pasar a reposo -------------------------------------------------------------------


async def test_cu04_flujo_principal(rig):
    await rig.open_session()
    session = rig.sessions.find_open()[0]
    rig.clear()
    await rig.say("Gracias, Jarvis.")
    assert rig.state is S.IDLE
    assert rig.transcriber.calls == [False]
    assert rig.of(events.TranscriptReady) == [events.TranscriptReady("Gracias, Jarvis.", True)]
    assert rig.spoken() == ["A su disposición."]
    assert rig.of(events.RestEntered) == [events.RestEntered()]
    assert Activity.PROCESANDO in rig.activities()
    assert rig.mode is CaptureMode.MUTED
    await rig.advance(1.0)
    assert rig.activities()[-1] is Activity.REPOSO
    assert rig.mode is CaptureMode.WAKE_AND_CLOSING
    assert rig.sessions.find_open() == [session]  # la sesión no cambia
    assert rig.transcriber.loaded  # en reposo sigue cargado
    assert rig.player.is_open
    rig.clear()
    await rig.advance(2.0)
    assert rig.of(events.AudioLevel) == [events.AudioLevel(0.0, "none")]  # y deja de publicarse


async def test_cu04_a1_treinta_segundos_sin_voz(rig):
    await rig.open_session()
    await rig.advance(29.5)
    assert rig.state is S.LISTENING_COMMAND
    await rig.advance(1.0)
    assert rig.state is S.IDLE
    assert rig.spoken()[-1] == "A su disposición."
    assert rig.of(events.RestEntered) == [events.RestEntered()]


async def test_cu04_a1_con_voz_en_curso_no_pasa_a_reposo(rig):
    await rig.open_session()
    rig.app.capture._segmenter = SimpleNamespace(capturing=True)
    await rig.advance(31.0)
    assert rig.state is S.LISTENING_COMMAND
    rig.app.capture._segmenter = SimpleNamespace(capturing=False)
    await rig.advance(30.5)
    assert rig.state is S.IDLE


async def test_cu04_a2_frase_parecida_se_ignora_y_reinicia_la_cuenta(rig):
    await rig.open_session()
    await rig.advance(20.0)
    rig.clear()
    await rig.say("Muchas gracias Jarvis por todo")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.TranscriptReady) == [
        events.TranscriptReady("Muchas gracias Jarvis por todo", False)
    ]
    assert rig.activities()[-1] is Activity.ESCUCHANDO
    await rig.advance(20.0)
    assert rig.state is S.LISTENING_COMMAND
    await rig.advance(10.5)
    assert rig.state is S.IDLE


async def test_cu04_una_transcripcion_vacia_cuenta_como_voz_y_no_se_muestra(rig):
    await rig.open_session()
    await rig.advance(20.0)
    rig.clear()
    await rig.say("")
    assert rig.of(events.TranscriptReady) == []
    await rig.advance(20.0)
    assert rig.state is S.LISTENING_COMMAND


async def test_cu04_en_reposo_solo_se_atiende_la_frase_de_cierre(rig):
    await rig.open_session()
    await rig.say("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.say("abre el navegador", restricted=True)
    await rig.say("gracias jarvis", restricted=True)
    assert rig.state is S.IDLE
    assert rig.spoken() == [] and rig.of(events.TranscriptReady) == []
    assert rig.transcriber.calls[-2:] == [True, True]  # búsqueda voraz


async def test_una_orden_de_una_epoca_anterior_se_descarta_sin_transcribir(rig):
    await rig.open_session()
    old_epoch = rig.app.orchestrator.epoch
    await rig.say("gracias jarvis")
    await rig.advance(1.0)
    assert rig.app.orchestrator.epoch == old_epoch + 1
    assert rig.app.capture.epoch == old_epoch + 1
    calls = len(rig.transcriber.calls)
    await rig.say("buenas noches jarvis", restricted=True, epoch=old_epoch)
    assert rig.state is S.IDLE
    assert len(rig.transcriber.calls) == calls


# --- CU-05. Cerrar sesión --------------------------------------------------------------------


async def test_cu05_flujo_principal(rig):
    await rig.open_session()
    session = rig.sessions.find_open()[0]
    pending = ActivityRepository(rig.database).add(session.id, "comandos", "gcc", rig.clock.now())
    rig.clear()
    await rig.say("Buenas noches, Jarvis.")
    assert rig.state is S.DORMIDO
    closed = rig.sessions.get(session.id)
    assert closed.closed_at == rig.clock.now() and closed.close_reason == "voz"
    (activity,) = ActivityRepository(rig.database).of_session(session.id)
    assert activity.id == pending and activity.status == "error"
    assert rig.spoken() == ["Buenas noches. Sesión cerrada."]
    assert rig.of(events.SessionClosed) == [events.SessionClosed()]
    assert rig.mode is CaptureMode.MUTED
    await rig.advance(1.0)
    assert rig.activities()[-1] is Activity.DORMIDO
    assert rig.mode is CaptureMode.WAKE_ONLY
    assert not rig.transcriber.loaded and rig.transcriber.unloads == 1
    assert not rig.player.is_open
    assert rig.exited == []  # cerrar la sesión nunca termina el proceso
    assert not rig.task.done()
    rig.clear()
    await rig.advance(40.0)
    assert rig.of(events.RestEntered) == [] and rig.spoken() == []


async def test_cu05_a1_cierre_desde_reposo(rig):
    await rig.open_session()
    await rig.say("gracias jarvis")
    await rig.advance(1.0)
    await rig.say("buenas noches jarvis", restricted=True)
    assert rig.state is S.DORMIDO
    assert rig.sessions.find_open() == []
    assert rig.spoken()[-1] == "Buenas noches. Sesión cerrada."
    assert rig.transcriber.calls[-1] is True


async def test_cu05_a2_escucha_restringida_desactivada(tmp_path):
    settings = Settings()
    audio = dataclasses.replace(settings.audio, closing_phrase_in_idle=False)
    rig = Rig(tmp_path, dataclasses.replace(settings, audio=audio))
    await rig.start()
    try:
        await rig.open_session()
        await rig.say("gracias jarvis")
        await rig.advance(1.0)
        assert rig.mode is CaptureMode.WAKE_ONLY
        await rig.wake()
        await rig.advance(1.0)
        await rig.say("buenas noches jarvis")
        assert rig.state is S.DORMIDO
    finally:
        await rig.stop()


async def test_cu05_a4_buenas_noches_sin_jarvis_se_ignora(rig):
    await rig.open_session()
    await rig.say("buenas noches")
    assert rig.state is S.LISTENING_COMMAND
    await rig.say("gracias jarvis")
    await rig.advance(1.0)
    await rig.say("buenas noches", restricted=True)
    assert rig.state is S.IDLE
    assert len(rig.sessions.find_open()) == 1


@pytest.mark.parametrize("resting", [False, True])
async def test_cu05_a5_salir_desde_la_bandeja_cierra_sin_frase_y_termina(rig, resting):
    await rig.open_session()
    session = rig.sessions.find_open()[0]
    if resting:
        await rig.say("gracias jarvis")
        await rig.advance(1.0)
    rig.clear()
    rig.app.bus.publish(events.QuitRequested())
    await settle()
    assert rig.sessions.get(session.id).close_reason == "salida"
    assert rig.spoken() == []
    assert rig.of(events.SessionClosed) == [events.SessionClosed()]
    assert rig.exited == [True]
    assert rig.task.done()
    assert not rig.transcriber.loaded and not rig.player.is_open


async def test_salir_en_dormido_termina_el_proceso(rig):
    rig.app.orchestrator.submit(fsm.ShutdownRequested())
    await settle()
    assert rig.exited == [True] and rig.task.done()
    assert rig.sessions.find_open() == []


async def test_un_error_al_atender_una_entrada_no_detiene_el_nucleo(rig, caplog):
    async def broken(pcm, *, restricted=False):
        raise RuntimeError("fallo del modelo")

    await rig.open_session()
    rig.transcriber.transcribe = broken
    await rig.say("lo que sea")
    assert "No se ha podido transcribir la orden" in caplog.text
    assert not rig.task.done()
    await rig.advance(30.5)  # la cuenta de silencio sigue en marcha
    assert rig.state is S.IDLE


async def test_una_entrada_desconocida_se_registra_y_se_ignora(rig, caplog):
    rig.app.orchestrator.submit(object())
    await settle()
    assert "Entrada desconocida" in caplog.text
    await rig.open_session()
    assert rig.state is S.LISTENING_COMMAND
