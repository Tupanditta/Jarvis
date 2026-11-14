"""Reglas de calibración de «Hey Jarvis» y de diagnóstico del micrófono (captura-audio.md).

Funciones puras que usan `scripts/calibrate_wakeword.py` y `scripts/diagnose_mic.py`. Nada
escribe audio en disco ni modifica la configuración.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from jarvis_assistant.audio_capture.device_selection import WINDOWS_API_PREFERENCE
from jarvis_assistant.audio_capture.segmenter import BLOCK_SAMPLES
from jarvis_assistant.audio_capture.telemetry import MUTE_PEAK

LOW_VOICE_DBFS = -30.0
TARGET_VOICE_DBFS = -15.0
MAX_GAIN = 8.0
REQUIRED_DETECTIONS = 9
MIN_RECOMMENDED_THRESHOLD = 0.3
VERIFIER_FLOOR = 0.2


def recommend_gain(voice_peak_dbfs: float, current_gain: float = 1.0) -> float | None:
    """Ganancia que lleva la voz a −15 dBFS si queda por debajo de −30; None si no hace falta."""
    if voice_peak_dbfs >= LOW_VOICE_DBFS:
        return None
    gain = current_gain * 10 ** ((TARGET_VOICE_DBFS - voice_peak_dbfs) / 20)
    return min(MAX_GAIN, round(gain, 1))


@dataclass(frozen=True)
class Verdict:
    kind: Literal["ok", "threshold", "verifier", "hopeless"]
    detections: int
    threshold: float | None = None  # valor recomendado de `audio.wakeword_threshold`


def verdict(scores: Sequence[float], threshold: float) -> Verdict:
    """Veredicto de la medida a partir de la puntuación máxima de cada repetición."""
    detections = sum(score >= threshold for score in scores)
    if detections >= REQUIRED_DETECTIONS:
        return Verdict("ok", detections)
    if max(scores, default=0.0) < VERIFIER_FLOOR:
        return Verdict("hopeless", detections)
    ranked = sorted(scores, reverse=True)
    if len(ranked) >= REQUIRED_DETECTIONS:
        candidate = int(ranked[REQUIRED_DETECTIONS - 1] * 100) / 100  # redondeo hacia abajo
        if candidate >= MIN_RECOMMENDED_THRESHOLD:
            return Verdict("threshold", detections, candidate)
    return Verdict("verifier", detections)


def verifier_passes(detected: int, false_activations: int) -> bool:
    """El verificador se guarda solo si detecta 9 o más de 10 y no salta durante la lectura."""
    return detected >= REQUIRED_DETECTIONS and false_activations == 0


def blocks_of(pcm: np.ndarray) -> list[np.ndarray]:
    """Bloques completos de 1280 muestras."""
    count = len(pcm) // BLOCK_SAMPLES
    return [pcm[i * BLOCK_SAMPLES : (i + 1) * BLOCK_SAMPLES] for i in range(count)]


def collect_features(model: Any, name: str, pcm: np.ndarray, minimum: float) -> list[np.ndarray]:
    """Características de `openwakeword` de las ventanas con puntuación ≥ `minimum`."""
    model.reset()
    features = []
    for block in blocks_of(pcm):
        if model.predict(block)[name] >= minimum:
            features.append(model.preprocessor.get_features(model.model_inputs[name]))
    return features


def verified_scores(
    model: Any, name: str, verifier: Any, pcm: np.ndarray, gate: float
) -> list[float]:
    """Puntuación por bloque como la dará el asistente con el verificador cargado."""
    model.reset()
    scores = []
    for block in blocks_of(pcm):
        score = float(model.predict(block)[name])
        if score >= gate:
            features = model.preprocessor.get_features(model.model_inputs[name])
            score = float(verifier.predict_proba(features)[0][-1])
        scores.append(score)
    return scores


def count_activations(scores: Sequence[float], threshold: float, debounce_blocks: int = 13) -> int:
    """Activaciones con el antirrebote de 1 s."""
    count, last = 0, -debounce_blocks
    for index, score in enumerate(scores):
        if score >= threshold and index - last >= debounce_blocks:
            count, last = count + 1, index
    return count


# --- Diagnóstico del micrófono ---------------------------------------------------------------

InputClass = Literal["muda", "con señal", "detecta"]


@dataclass(frozen=True)
class InputResult:
    name: str
    hostapi: str
    peak: int
    score: float
    kind: InputClass


def classify_input(peak: int, score: float, threshold: float) -> InputClass:
    if peak <= MUTE_PEAK:
        return "muda"
    return "detecta" if score >= threshold else "con señal"


def recommend_input(results: Sequence[InputResult]) -> InputResult | None:
    """La mejor entrada: las que detectan antes que las que solo tienen señal; nunca una muda."""
    usable = [result for result in results if result.kind != "muda"]
    if not usable:
        return None

    def rank(result: InputResult) -> tuple:
        api = (
            WINDOWS_API_PREFERENCE.index(result.hostapi)
            if result.hostapi in WINDOWS_API_PREFERENCE
            else len(WINDOWS_API_PREFERENCE)
        )
        return (result.kind != "detecta", -round(result.score, 2), api, -result.peak)

    return min(usable, key=rank)
