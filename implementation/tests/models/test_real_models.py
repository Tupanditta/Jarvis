r"""Modelo real de la voz (marcador `models`; a demanda).

    .\.venv\Scripts\python.exe -m pytest -m models tests\models
"""
import time

import numpy as np
import pytest

from jarvis_assistant.paths import models_dir
from jarvis_assistant.speaker.piper_synth import PiperSynthesizer

pytestmark = [pytest.mark.models, pytest.mark.timeout(180)]


def test_la_sintesis_de_una_frase_corta_tarda_menos_de_medio_segundo():
    synthesizer = PiperSynthesizer(models_dir(), "es_ES-davefx-medium")
    synthesizer.load()
    synthesizer.synthesize("Le escucho.")  # primera llamada: calienta el modelo
    started = time.perf_counter()
    pcm = synthesizer.synthesize("A su disposición.")
    elapsed = time.perf_counter() - started
    assert pcm.dtype == np.int16 and len(pcm) > synthesizer.sample_rate // 2
    assert elapsed < 0.5
