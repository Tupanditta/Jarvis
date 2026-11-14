"""Segmentación de órdenes con secuencias sintéticas de bloques (captura-audio.md)."""
import numpy as np
import pytest

from jarvis_assistant.audio_capture.segmenter import BLOCK_SECONDS, Segmenter, SegmenterConfig

BLOCK = 1280
VOICE = np.full(BLOCK, 1000, dtype=np.int16)
QUIET = np.zeros(BLOCK, dtype=np.int16)


def blocks(seconds: float) -> int:
    return round(seconds / BLOCK_SECONDS)


class Feeder:
    """Alimenta el segmentador llevando la cuenta del tiempo."""

    def __init__(self, segmenter: Segmenter) -> None:
        self.segmenter = segmenter
        self.now = 100.0
        self.segments = []

    def feed(self, speech: bool, count: int) -> None:
        for _ in range(count):
            self.now += BLOCK_SECONDS
            segment = self.segmenter.feed(VOICE if speech else QUIET, speech, self.now)
            if segment is not None:
                self.segments.append(segment)

    def voice(self, seconds: float) -> None:
        self.feed(True, blocks(seconds))

    def quiet(self, seconds: float) -> None:
        self.feed(False, blocks(seconds))


def commands() -> Feeder:
    return Feeder(Segmenter(SegmenterConfig()))


def restricted() -> Feeder:
    return Feeder(Segmenter(SegmenterConfig(), restricted=True))


def test_sin_voz_no_hay_orden():
    feeder = commands()
    feeder.quiet(5)
    assert feeder.segments == []
    assert not feeder.segmenter.capturing


def test_una_orden_termina_tras_un_segundo_de_pausa():
    feeder = commands()
    feeder.quiet(1)
    feeder.voice(2)
    assert feeder.segmenter.capturing
    feeder.quiet(0.9)
    assert feeder.segments == []
    feeder.quiet(0.2)
    assert len(feeder.segments) == 1
    assert not feeder.segmenter.capturing
    assert not feeder.segments[0].restricted


def test_la_orden_incluye_los_400_ms_anteriores_a_la_voz():
    feeder = commands()
    feeder.quiet(1)
    start = feeder.now
    feeder.voice(1)
    feeder.quiet(1.1)
    segment = feeder.segments[0]
    preroll = blocks(0.4)
    assert segment.started_at == pytest.approx(start + BLOCK_SECONDS - 0.4)
    assert not segment.pcm[: preroll * BLOCK].any()
    assert segment.pcm[preroll * BLOCK : (preroll + blocks(1)) * BLOCK].all()
    assert segment.pcm.dtype == np.int16


def test_una_pausa_corta_no_parte_la_orden():
    feeder = commands()
    feeder.voice(1)
    feeder.quiet(0.5)
    feeder.voice(1)
    feeder.quiet(1.1)
    assert len(feeder.segments) == 1
    assert len(feeder.segments[0].pcm) >= blocks(2.5) * BLOCK


def test_una_orden_termina_a_los_quince_segundos():
    feeder = commands()
    feeder.voice(15.5)
    assert len(feeder.segments) == 1
    duration = len(feeder.segments[0].pcm) / 16000
    assert 14.9 <= duration <= 15.1


def test_menos_de_300_ms_de_voz_se_descarta_y_no_cuenta_como_voz():
    feeder = commands()
    feeder.voice(0.16)
    feeder.quiet(1.5)
    assert feeder.segments == []
    assert not feeder.segmenter.capturing


def test_tras_una_orden_se_captura_la_siguiente():
    feeder = commands()
    for _ in range(2):
        feeder.voice(1)
        feeder.quiet(1.2)
    assert len(feeder.segments) == 2
    assert feeder.segments[1].started_at >= feeder.segments[0].ended_at


def test_reset_abandona_la_orden_en_curso():
    feeder = commands()
    feeder.voice(1)
    feeder.segmenter.reset()
    feeder.quiet(1.5)
    assert feeder.segments == []


def test_restringido_entrega_una_frase_corta_marcada():
    feeder = restricted()
    feeder.quiet(1)
    feeder.voice(1.5)
    feeder.quiet(1.1)
    assert len(feeder.segments) == 1
    assert feeder.segments[0].restricted


def test_restringido_descarta_un_segmento_de_menos_de_medio_segundo():
    feeder = restricted()
    feeder.voice(0.4)
    feeder.quiet(1.2)
    assert feeder.segments == []


def test_restringido_abandona_al_superar_tres_segundos_y_medio():
    feeder = restricted()
    feeder.voice(3.7)
    assert not feeder.segmenter.capturing
    feeder.voice(20)  # la conversación sigue: no se vuelve a capturar
    feeder.quiet(0.5)
    feeder.voice(2)
    assert not feeder.segmenter.capturing
    feeder.quiet(1.1)
    assert feeder.segments == []


def test_restringido_vuelve_a_capturar_tras_el_silencio_que_sigue_al_abandono():
    feeder = restricted()
    feeder.voice(5)
    feeder.quiet(3)
    feeder.voice(1.5)
    feeder.quiet(1.1)
    assert len(feeder.segments) == 1


def test_restringido_entrega_como_maximo_un_segmento_cada_dos_segundos():
    config = SegmenterConfig(end_of_speech_seconds=0.24)
    feeder = Feeder(Segmenter(config, restricted=True))
    feeder.voice(0.6)
    feeder.quiet(0.3)
    feeder.voice(0.6)
    feeder.quiet(0.3)
    assert len(feeder.segments) == 1
    feeder.quiet(2)
    feeder.voice(0.6)
    feeder.quiet(0.3)
    assert len(feeder.segments) == 2
