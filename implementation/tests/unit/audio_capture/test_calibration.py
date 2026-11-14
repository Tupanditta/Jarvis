"""Reglas puras de calibración y de diagnóstico (captura-audio.md)."""
from types import SimpleNamespace

import numpy as np
import pytest

from jarvis_assistant.audio_capture.calibration import (
    InputResult,
    Verdict,
    blocks_of,
    classify_input,
    collect_features,
    count_activations,
    recommend_gain,
    recommend_input,
    verdict,
    verified_scores,
    verifier_passes,
)

NAME = "hey_jarvis_v0.1"


def test_la_ganancia_solo_se_recomienda_con_la_voz_por_debajo_de_menos_30():
    assert recommend_gain(-30.0) is None
    assert recommend_gain(-12.0) is None
    assert recommend_gain(-35.0) == 8.0
    assert recommend_gain(-31.0) == pytest.approx(6.3)
    assert recommend_gain(-60.0) == 8.0  # máximo
    assert recommend_gain(-31.0, current_gain=0.5) == pytest.approx(3.2)


def test_veredicto_sin_cambios_con_nueve_de_diez():
    scores = [0.9] * 9 + [0.1]
    assert verdict(scores, 0.5) == Verdict("ok", 9)


def test_veredicto_recomienda_el_umbral_que_daria_nueve():
    scores = [0.8] * 6 + [0.45, 0.41, 0.387, 0.1]
    assert verdict(scores, 0.5) == Verdict("threshold", 6, 0.38)


def test_veredicto_recomienda_el_verificador_si_el_umbral_bajaria_de_03():
    scores = [0.8] * 5 + [0.28, 0.27, 0.26, 0.25, 0.1]
    assert verdict(scores, 0.5) == Verdict("verifier", 5)


def test_veredicto_sin_remedio_si_ninguna_llega_a_02():
    assert verdict([0.19] * 10, 0.5) == Verdict("hopeless", 0)
    assert verdict([], 0.5).kind == "hopeless"


def test_validacion_del_verificador():
    assert verifier_passes(9, 0) and verifier_passes(10, 0)
    assert not verifier_passes(8, 0)
    assert not verifier_passes(10, 1)


class FakeModel:
    """Puntúa cada bloque con su primera muestra dividida entre 100."""

    def __init__(self):
        self.model_inputs = {NAME: 16}
        self.resets = 0
        self.last = None
        self.preprocessor = SimpleNamespace(get_features=lambda size: (self.last, size))

    def reset(self):
        self.resets += 1

    def predict(self, block):
        self.last = int(block[0])
        return {NAME: block[0] / 100}


def audio(*scores):
    return np.concatenate([np.full(1280, round(s * 100), dtype=np.int16) for s in scores])


def test_bloques_completos():
    assert len(blocks_of(np.zeros(1280 * 3 + 500, dtype=np.int16))) == 3


def test_caracteristicas_de_las_ventanas_que_superan_la_puerta():
    model = FakeModel()
    features = collect_features(model, NAME, audio(0.1, 0.25, 0.6, 0.19), 0.2)
    assert features == [(25, 16), (60, 16)]
    assert model.resets == 1
    assert len(collect_features(model, NAME, audio(0.1, 0.6), 0.0)) == 2


def test_puntuacion_con_verificador_como_la_dara_el_asistente():
    verifier = SimpleNamespace(predict_proba=lambda features: [[0.1, features[0] / 50]])
    scores = verified_scores(FakeModel(), NAME, verifier, audio(0.1, 0.25, 0.4), 0.2)
    assert scores == pytest.approx([0.1, 0.5, 0.8])


def test_activaciones_con_antirrebote():
    assert count_activations([0.1, 0.9, 0.9, 0.9, 0.1], 0.5) == 1
    assert count_activations([0.9] + [0.0] * 12 + [0.9], 0.5) == 2
    assert count_activations([0.4] * 50, 0.5) == 0


def test_clasificacion_y_recomendacion_de_entradas():
    assert classify_input(0, 0.0, 0.5) == "muda"
    assert classify_input(3, 0.9, 0.5) == "muda"
    assert classify_input(900, 0.2, 0.5) == "con señal"
    assert classify_input(900, 0.7, 0.5) == "detecta"

    def result(name, api, peak, score):
        return InputResult(name, api, peak, score, classify_input(peak, score, 0.5))

    mute = result("Mic", "MME", 0, 0.0)
    signal = result("Mic", "Windows WASAPI", 9000, 0.3)
    detects_ds = result("Mic", "Windows DirectSound", 5000, 0.8)
    detects_mme = result("Mic", "MME", 4000, 0.8)
    assert recommend_input([mute]) is None
    assert recommend_input([mute, signal]) == signal
    assert recommend_input([mute, signal, detects_ds]) == detects_ds
    assert recommend_input([detects_ds, detects_mme, signal]) == detects_mme
