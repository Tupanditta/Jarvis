"""Modos de captura, ganancia, micrófono mudo y trazas, con dobles (captura-audio.md)."""
import dataclasses
import logging

import numpy as np
import pytest

from fakes.audio import FakeMicrophone, FakeVad, FakeWakeWord, silence, tone
from jarvis_assistant.audio_capture.processor import AudioProcessor
from jarvis_assistant.audio_capture.segmenter import BLOCK_SECONDS
from jarvis_assistant.audio_capture.types import CaptureMode, Utterance, WakeWordDetected
from jarvis_assistant.config import AudioSettings
from jarvis_assistant.core.events import MicStatusChanged


class Rig:
    def __init__(self, **settings) -> None:
        self.settings = dataclasses.replace(AudioSettings(), **settings)
        self.microphone = FakeMicrophone()
        self.wakeword = FakeWakeWord()
        self.vad = FakeVad()
        self.delivered: list[object] = []
        self.now = 50.0
        self.processor = AudioProcessor(
            microphone=self.microphone,
            wakeword=self.wakeword,
            vad=self.vad,
            settings=self.settings,
            deliver=self.delivered.append,
            monotonic=lambda: self.now,
        )

    def feed(self, block: np.ndarray, seconds: float) -> None:
        for _ in range(round(seconds / BLOCK_SECONDS)):
            self.now += BLOCK_SECONDS
            self.processor.process_block(block, self.now)

    def of(self, kind: type) -> list:
        return [item for item in self.delivered if isinstance(item, kind)]


@pytest.fixture
def rig():
    return Rig()


def test_wake_only_detecta_la_palabra_y_no_segmenta(rig):
    rig.wakeword.score = 0.9
    rig.feed(tone(), 0.08)
    assert rig.delivered == [WakeWordDetected(rig.now)]
    rig.wakeword.score = 0.0
    rig.feed(tone(), 3)
    rig.feed(silence(), 2)
    assert rig.of(Utterance) == []
    assert rig.vad.seen == 0
    assert rig.processor.current_level() == 0.0


def test_antirrebote_de_un_segundo(rig):
    rig.wakeword.score = 0.9
    rig.feed(tone(), 0.96)
    assert len(rig.of(WakeWordDetected)) == 1
    rig.feed(tone(), 0.16)
    assert len(rig.of(WakeWordDetected)) == 2


def test_por_debajo_del_umbral_no_hay_deteccion(rig):
    rig.wakeword.score = 0.49
    rig.feed(tone(), 2)
    assert rig.delivered == []


def test_commands_entrega_la_orden_con_la_epoca(rig):
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.processor.epoch = 7
    rig.feed(tone(), 1)
    assert rig.processor.capturing
    assert rig.processor.current_level() > 0
    rig.feed(silence(), 1.2)
    (utterance,) = rig.of(Utterance)
    assert utterance.epoch == 7
    assert not utterance.restricted
    assert utterance.pcm.any()
    assert rig.processor.current_level() == 0.0


def test_commands_tambien_detecta_la_palabra(rig):
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.wakeword.score = 0.8
    rig.feed(tone(), 0.08)
    assert len(rig.of(WakeWordDetected)) == 1


def test_wake_and_closing_entrega_segmentos_restringidos(rig):
    rig.processor.set_mode(CaptureMode.WAKE_AND_CLOSING)
    rig.feed(tone(), 1.5)
    rig.feed(silence(), 1.2)
    (utterance,) = rig.of(Utterance)
    assert utterance.restricted


def test_wake_and_closing_abandona_una_conversacion(rig):
    rig.processor.set_mode(CaptureMode.WAKE_AND_CLOSING)
    rig.feed(tone(), 6)
    rig.feed(silence(), 1.2)
    assert rig.of(Utterance) == []


def test_muted_no_entrega_nada_ni_consulta_los_detectores(rig):
    rig.processor.set_mode(CaptureMode.MUTED)
    rig.wakeword.score = 0.9
    rig.feed(tone(), 2)
    rig.feed(silence(), 2)
    assert rig.delivered == []
    assert rig.wakeword.seen == []
    assert rig.vad.seen == 0


def test_al_reabrir_se_descarta_lo_acumulado_y_se_reinician_los_detectores(rig):
    rig.processor.set_mode(CaptureMode.MUTED)
    rig.feed(tone(), 1)
    rig.processor.set_mode(CaptureMode.COMMANDS, reopen_at=rig.now + 0.3)
    rig.wakeword.score = 0.9
    rig.feed(tone(), 0.24)  # eco de la propia voz: todavía cerrado
    assert rig.delivered == []
    assert rig.wakeword.resets == rig.vad.resets == 0
    rig.wakeword.score = 0.0
    rig.feed(silence(), 0.16)
    assert rig.wakeword.resets == rig.vad.resets == 1
    rig.feed(tone(), 1)
    rig.feed(silence(), 1.2)
    assert len(rig.of(Utterance)) == 1
    assert rig.wakeword.resets == 1


def test_una_reapertura_pendiente_no_se_pierde_al_fijar_otro_modo(rig):
    rig.processor.set_mode(CaptureMode.MUTED)
    rig.processor.set_mode(CaptureMode.COMMANDS, reopen_at=rig.now + 0.3)
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.processor.set_mode(CaptureMode.WAKE_AND_CLOSING)
    rig.wakeword.score = 0.9
    rig.feed(tone(), 0.24)
    assert rig.delivered == []
    rig.feed(tone(), 0.16)
    assert len(rig.of(WakeWordDetected)) == 1
    assert rig.wakeword.resets == 1


def test_cambiar_de_modo_abandona_la_orden_en_curso(rig):
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.feed(tone(), 1)
    rig.processor.set_mode(CaptureMode.WAKE_AND_CLOSING)
    rig.feed(silence(), 1.5)
    assert rig.of(Utterance) == []


def test_repetir_el_mismo_modo_no_abandona_la_orden(rig):
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.feed(tone(), 1)
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.feed(silence(), 1.2)
    assert len(rig.of(Utterance)) == 1


def test_la_ganancia_se_aplica_antes_de_los_detectores_y_satura():
    rig = Rig(input_gain=4.0)
    rig.processor.set_mode(CaptureMode.COMMANDS)
    rig.feed(tone(1000), 0.08)
    assert rig.wakeword.seen[0][0] == 4000
    rig.feed(tone(20000), 0.08)
    rig.feed(tone(-20000), 0.08)
    assert rig.wakeword.seen[1][0] == 32767
    assert rig.wakeword.seen[2][0] == -32768
    assert rig.wakeword.seen[1].dtype == np.int16


def test_microfono_mudo_aviso_unico_y_recuperacion(rig, caplog):
    caplog.set_level(logging.INFO)
    rig.feed(silence(), 4.9)
    assert rig.of(MicStatusChanged) == []
    rig.feed(silence(), 10)
    assert rig.of(MicStatusChanged) == [MicStatusChanged(False)]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "silencio digital" in warnings[0].getMessage()
    rig.feed(tone(40), 0.08)
    assert rig.of(MicStatusChanged) == [MicStatusChanged(False), MicStatusChanged(True)]


def test_una_habitacion_en_silencio_no_es_silencio_digital(rig):
    rig.feed(tone(4), 20)
    assert rig.of(MicStatusChanged) == []


def test_casi_deteccion_se_registra_como_maximo_cada_cinco_segundos(rig, caplog):
    caplog.set_level(logging.INFO)
    rig.wakeword.score = 0.3
    rig.feed(tone(), 11)
    near = [r for r in caplog.records if "Casi detección" in r.getMessage()]
    assert len(near) == 2  # ventanas de 2 s: a los 2 s y, pasados 5 s, a los 8 s
    assert "0.30" in near[0].getMessage()


@pytest.mark.parametrize("score", [0.1, 0.6])
def test_fuera_del_intervalo_no_es_casi_deteccion(rig, caplog, score):
    caplog.set_level(logging.INFO)
    rig.wakeword.score = score
    rig.feed(tone(), 6)
    assert not [r for r in caplog.records if "Casi detección" in r.getMessage()]


def test_la_deteccion_registra_la_puntuacion_y_el_verificador(rig, caplog):
    caplog.set_level(logging.INFO)
    rig.wakeword.score, rig.wakeword.verifier_active = 0.72, True
    rig.feed(tone(), 0.08)
    (record,) = [r for r in caplog.records if "detectada" in r.getMessage()]
    assert "0.72" in record.getMessage()
    assert "con verificador" in record.getMessage()


def test_el_hilo_reintenta_y_avisa_cuando_no_hay_microfono():
    rig = Rig(mic_retry_seconds=0.01)
    rig.microphone.fail_open = True
    rig.processor.start()
    try:
        _wait(lambda: rig.of(MicStatusChanged) == [MicStatusChanged(False)])
        _wait(lambda: rig.microphone.refreshed >= 1)
        rig.microphone.fail_open = False
        _wait(lambda: rig.of(MicStatusChanged)[-1] == MicStatusChanged(True))
    finally:
        rig.processor.stop()
    assert rig.wakeword.loaded and rig.vad.loaded
    assert rig.microphone.closed >= 1


def _wait(condition, timeout: float = 2.0) -> None:
    import time

    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condición no alcanzada"
        time.sleep(0.005)
