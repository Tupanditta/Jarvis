"""Frases, reproductor y cola de locuciones con dobles (sintetizador.md)."""
import asyncio
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from fakes.clock import FakeClock
from fakes.voice import FakePlayer, FakeSynthesizer
from jarvis_assistant.config import TtsSettings
from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import SilenceRequested, SpeechFinished, SpeechStarted
from jarvis_assistant.speaker.phrases import (
    LIFECYCLE_IDS,
    PHRASES,
    PRELOADED_IDS,
    PhraseError,
    advance,
    parameters,
    render,
    variants,
)
from jarvis_assistant.speaker.piper_synth import PiperSynthesizer
from jarvis_assistant.speaker.player import Player
from jarvis_assistant.speaker.speaker import Speaker

SRC = Path(__file__).resolve().parents[3] / "src"


async def settle() -> None:
    for _ in range(20):
        await asyncio.sleep(0)


# --- Catálogo --------------------------------------------------------------------------------


def test_todas_las_frases_se_renderizan_con_parametros_de_ejemplo():
    for phrase_id in PHRASES:
        params = {name: "ejemplo" for name in parameters(phrase_id)}
        text = render(Phrase(phrase_id, params))
        assert text and "{" not in text


def test_frases_del_ciclo_de_vida():
    # El texto es del catálogo: aquí solo se comprueba que existen y no llevan parámetros.
    for phrase_id in LIFECYCLE_IDS:
        assert render(Phrase(phrase_id)) == PHRASES[phrase_id][0]
        assert parameters(phrase_id) == ()
    assert "settings.toml" in render(Phrase("config.error", {"archivo": "settings.toml"}))


def test_todas_las_variantes_de_una_frase_usan_los_mismos_parametros():
    from string import Formatter

    for phrase_id in PHRASES:
        assert variants(phrase_id), phrase_id
        names = {
            frozenset(name for _, name, _, _ in Formatter().parse(template) if name)
            for template in variants(phrase_id)
        }
        assert len(names) == 1, phrase_id


def test_las_variantes_se_usan_en_orden_y_vuelven_al_principio(monkeypatch):
    monkeypatch.setitem(PHRASES, "ciclo.escucha", ["Uno, señor.", "Dos, señor.", "Tres, señor."])
    dichas = []
    for _ in range(4):
        dichas.append(render(Phrase("ciclo.escucha")))
        advance("ciclo.escucha")
    assert dichas == ["Uno, señor.", "Dos, señor.", "Tres, señor.", "Uno, señor."]


def test_frase_desconocida_o_sin_parametro():
    with pytest.raises(PhraseError):
        render(Phrase("no.existe"))
    with pytest.raises(PhraseError):
        render(Phrase("config.error"))


def test_las_frases_presintetizadas_no_tienen_parametros():
    assert set(LIFECYCLE_IDS) <= set(PRELOADED_IDS)
    assert all(parameters(phrase_id) == () for phrase_id in PRELOADED_IDS)


def test_cada_identificador_usado_en_el_codigo_existe_en_el_catalogo():
    pattern = re.compile(r'"((?:ciclo|general|entidad|ruta)\.[a-z_]+|config\.error)"')
    used = set()
    for path in SRC.rglob("*.py"):
        if path.name != "phrases.py":
            used.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert set(LIFECYCLE_IDS) <= used
    assert used <= set(PHRASES)


# --- Sintetizador de Piper -------------------------------------------------------------------


def test_piper_carga_la_voz_local_y_une_los_fragmentos(tmp_path):
    seen = {}

    def factory(model_path, config_path):
        seen["paths"] = (model_path, config_path)
        chunk = SimpleNamespace(audio_int16_array=np.array([1, 2], dtype=np.int16))
        return SimpleNamespace(
            config=SimpleNamespace(sample_rate=22050), synthesize=lambda text: [chunk, chunk]
        )

    synthesizer = PiperSynthesizer(tmp_path, "es_ES-davefx-medium", factory)
    synthesizer.load()
    assert seen["paths"] == (
        tmp_path / "piper" / "es_ES-davefx-medium.onnx",
        tmp_path / "piper" / "es_ES-davefx-medium.onnx.json",
    )
    assert synthesizer.sample_rate == 22050
    assert synthesizer.synthesize("hola").tolist() == [1, 2, 1, 2]


# --- Reproductor -----------------------------------------------------------------------------


class FakeOutputStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = self.closed = False

    def start(self):
        self.started = True

    def stop(self):
        pass

    def close(self):
        self.closed = True

    def pull(self, frames):
        out = np.full((frames, 1), 77, dtype=np.int16)
        self.kwargs["callback"](out, frames, None, None)
        return out[:, 0]


def open_player(clock, rate=1000):
    streams = []

    def factory(**kwargs):
        streams.append(FakeOutputStream(**kwargs))
        return streams[-1]

    player = Player(clock, factory)
    player.open(rate)
    return player, streams[0]


async def test_reproduce_los_bloques_avisa_al_empezar_y_mide_el_nivel():
    player, stream = open_player(FakeClock())
    assert stream.kwargs["samplerate"] == 1000 and stream.kwargs["channels"] == 1
    assert not stream.pull(100).any()  # sin frase: silencio
    started = []
    task = asyncio.ensure_future(
        player.play(np.full(250, 8000, dtype=np.int16), lambda: started.append(True))
    )
    await settle()
    assert started == []
    assert stream.pull(100).tolist() == [8000] * 100
    await settle()
    assert started == [True]
    assert player.current_level() > 0
    stream.pull(100)
    last = stream.pull(100)
    assert last.tolist() == [8000] * 50 + [0] * 50
    assert await task is True
    assert player.current_level() == 0.0


async def test_stop_corta_con_fundido_de_30_ms():
    player, stream = open_player(FakeClock())
    task = asyncio.ensure_future(player.play(np.full(1000, 8000, dtype=np.int16)))
    await settle()
    stream.pull(100)
    player.stop()
    block = stream.pull(100)
    assert block[0] == 8000 and 0 < block[29] < block[1]
    assert not block[30:].any()
    assert await task is False
    assert not stream.pull(100).any()


async def test_sin_dispositivo_la_frase_se_da_por_dicha_tras_su_duracion(caplog):
    clock = FakeClock()

    def broken(**kwargs):
        raise RuntimeError("no hay salida")

    player = Player(clock, broken)
    player.open(1000)
    assert not player.is_open and "dispositivo de salida" in caplog.text
    started = []
    task = asyncio.ensure_future(
        player.play(np.zeros(2000, dtype=np.int16), lambda: started.append(True))
    )
    await settle()
    assert started == [True] and not task.done()
    clock.advance(2.0)
    assert await task is True


async def test_un_flujo_que_no_reproduce_no_bloquea_la_frase():
    clock = FakeClock()
    player, stream = open_player(clock)
    task = asyncio.ensure_future(player.play(np.zeros(1000, dtype=np.int16)))
    await settle()
    clock.advance(2.1)
    assert await task is True
    assert stream.closed and not player.is_open


# --- Speaker ---------------------------------------------------------------------------------


class Rig:
    def __init__(self, settings=None):
        self.clock = FakeClock()
        self.bus = EventBus()
        self.events = []
        self.bus.subscribe(SpeechStarted, self.events.append)
        self.bus.subscribe(SpeechFinished, self.events.append)
        self.synthesizer = FakeSynthesizer()
        self.player = FakePlayer(self.clock)
        self.speaker = Speaker(
            synthesizer=self.synthesizer, player=self.player, bus=self.bus, clock=self.clock,
            settings=settings or TtsSettings(),
        )

    async def advance(self, seconds):
        await settle()
        self.clock.advance(seconds)
        await settle()


@pytest.fixture
async def rig():
    rig = Rig()
    await rig.speaker.preload()
    yield rig
    rig.speaker.close()


async def test_preload_carga_la_voz_y_sintetiza_el_ciclo_de_vida(rig):
    assert rig.synthesizer.loaded
    # Se sintetizan todas las variantes de cada frase, una sola vez cada texto distinto.
    expected = list(dict.fromkeys(text for i in PRELOADED_IDS for text in variants(i)))
    assert rig.synthesizer.texts == expected
    task = asyncio.ensure_future(rig.speaker.say(Phrase("ciclo.apertura"), lifecycle=True))
    await rig.advance(1.0)
    assert not (await task).interrupted
    assert len(rig.synthesizer.texts) == len(expected)  # no se vuelve a sintetizar


async def test_frase_del_ciclo_de_vida_avisa_al_empezar(rig):
    started = []
    task = asyncio.ensure_future(
        rig.speaker.say(Phrase("ciclo.reposo"), lifecycle=True, on_start=lambda: started.append(1))
    )
    await settle()
    assert started == [1] and rig.speaker.speaking
    assert rig.events == [SpeechStarted(PHRASES["ciclo.reposo"][0], interruptible=False)]
    await rig.advance(1.0)
    assert not (await task).interrupted
    assert rig.events[-1] == SpeechFinished(interrupted=False)
    assert not rig.speaker.speaking
    assert rig.speaker.last_phrase is None


async def test_las_frases_se_dicen_de_una_en_una_y_en_orden(rig):
    first = asyncio.ensure_future(rig.speaker.say(Phrase("general.cancelado")))
    second = asyncio.ensure_future(rig.speaker.say(Phrase("general.error")))
    await settle()
    assert len(rig.player.played) == 1
    await rig.advance(1.0)
    assert first.done() and not second.done()
    assert len(rig.player.played) == 2
    await rig.advance(1.0)
    assert not (await second).interrupted
    texts = [e.text for e in rig.events if isinstance(e, SpeechStarted)]
    assert texts == [PHRASES["general.cancelado"][0], PHRASES["general.error"][0]]
    assert rig.speaker.last_phrase == Phrase("general.error")


async def test_stop_interrumpe_la_locucion_y_vacia_la_cola(rig):
    first = asyncio.ensure_future(rig.speaker.say(Phrase("general.cancelado")))
    second = asyncio.ensure_future(rig.speaker.say(Phrase("general.error")))
    await settle()
    rig.speaker.stop()
    await settle()
    assert (await first).interrupted and (await second).interrupted
    assert len(rig.player.played) == 1
    assert rig.events[-1] == SpeechFinished(interrupted=True)


async def test_el_boton_de_silencio_calla_la_locucion(rig):
    task = asyncio.ensure_future(rig.speaker.say(Phrase("general.error")))
    await settle()
    rig.bus.publish(SilenceRequested())
    assert (await task).interrupted


async def test_una_frase_del_ciclo_de_vida_no_se_interrumpe(rig):
    task = asyncio.ensure_future(rig.speaker.say(Phrase("ciclo.cierre"), lifecycle=True))
    await settle()
    rig.speaker.stop()
    await settle()
    assert not task.done()
    await rig.advance(1.0)
    assert not (await task).interrupted


async def test_cache_limitada_y_volumen(monkeypatch):
    # Una sola variante: la rotación no cambia el texto y la prueba no depende del catálogo.
    monkeypatch.setitem(PHRASES, "entidad.no_encontrado", ["No encuentro {nombre}, señor."])
    rig = Rig(TtsSettings(cache_size=1, volume=0.5))
    for name in ("a", "a", "b", "a"):
        task = asyncio.ensure_future(
            rig.speaker.say(Phrase("entidad.no_encontrado", {"nombre": name}))
        )
        while not rig.player.played or not rig.speaker.speaking:
            await asyncio.sleep(0.001)
        rig.clock.advance(1.0)
        await task
    said = [render(Phrase("entidad.no_encontrado", {"nombre": name})) for name in "aba"]
    assert rig.synthesizer.texts == said
    assert rig.player.played[0][0] == 500
    rig.speaker.close()


async def test_abre_y_cierra_la_salida_a_la_frecuencia_de_la_voz(rig):
    rig.speaker.open_output()
    assert rig.player.opened == [1000]
    rig.player.level = 0.4
    assert rig.speaker.current_level() == 0.4
    rig.speaker.close_output()
    assert rig.player.closed == 1


async def test_cada_vez_que_se_dice_una_frase_se_usa_la_siguiente_variante(rig, monkeypatch):
    monkeypatch.setitem(PHRASES, "general.error", ["Primera, señor.", "Segunda, señor."])
    for turn in range(1, 4):
        task = asyncio.ensure_future(rig.speaker.say(Phrase("general.error")))
        # Las variantes no están presintetizadas: se sintetizan en otro hilo. El reloj solo
        # avanza cuando la frase ya suena; si no, su temporizador nunca vencería.
        while len(rig.player.played) < turn:
            await asyncio.sleep(0.001)
        await rig.advance(1.0)
        await task
    texts = [e.text for e in rig.events if isinstance(e, SpeechStarted)]
    assert texts == ["Primera, señor.", "Segunda, señor.", "Primera, señor."]
