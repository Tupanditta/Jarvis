"""Salud de la señal del micrófono y trazas para calibrar (captura-audio.md).

Nada de esto guarda audio: solo acumula números. Sirve para distinguir en el registro
«no llega audio», «llega muy bajo» y «llega bien pero no se detecta».
"""
import logging
import math
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

FULL_SCALE = 32767
SILENCE_DBFS = -120.0
MUTE_PEAK = 3
MUTE_SECONDS = 5.0
REPORT_SECONDS = 5.0
NEAR_MISS_FLOOR = 0.15
NEAR_MISS_WINDOW_SECONDS = 2.0
NEAR_MISS_INTERVAL_SECONDS = 5.0
_LEVEL_FLOOR_DBFS = -50.0
_LEVEL_CEILING_DBFS = -10.0


def peak_of(block: np.ndarray) -> int:
    return int(np.abs(block.astype(np.int32)).max()) if block.size else 0


def rms_of(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block.astype(np.float64))))) if block.size else 0.0


def dbfs(value: float) -> float:
    """Nivel respecto al fondo de escala de 16 bits; el silencio digital da −120."""
    return SILENCE_DBFS if value <= 0 else max(SILENCE_DBFS, 20 * math.log10(value / FULL_SCALE))


def level_of(block: np.ndarray) -> float:
    """Nivel del bloque entre 0 y 1 para la interfaz (RF-83)."""
    span = _LEVEL_CEILING_DBFS - _LEVEL_FLOOR_DBFS
    return min(1.0, max(0.0, (dbfs(rms_of(block)) - _LEVEL_FLOOR_DBFS) / span))


class SignalTelemetry:
    """Pico, RMS y ritmo de bloques; una línea `DEBUG` cada 5 s."""

    def __init__(self) -> None:
        self._since: float | None = None
        self._reset()

    def _reset(self) -> None:
        self._blocks = 0
        self._peak = 0
        self._squares = 0.0
        self._samples = 0

    def add(self, block: np.ndarray, now: float, dropped: int = 0) -> str | None:
        """Acumula un bloque. Devuelve la línea escrita cuando toca informar."""
        if self._since is None:
            self._since = now
        self._blocks += 1
        self._peak = max(self._peak, peak_of(block))
        self._squares += float(np.sum(np.square(block.astype(np.float64))))
        self._samples += block.size
        elapsed = now - self._since
        if elapsed < REPORT_SECONDS:
            return None
        rms = math.sqrt(self._squares / self._samples) if self._samples else 0.0
        line = (
            f"Señal: pico {dbfs(self._peak):.1f} dBFS, RMS {dbfs(rms):.1f} dBFS, "
            f"{self._blocks / elapsed:.1f} bloques/s, {dropped} descartados"
        )
        logger.debug(line)
        self._since = now
        self._reset()
        return line


class MuteDetector:
    """Silencio digital: el pico no pasa de 3 durante 5 s seguidos con el flujo abierto."""

    def __init__(self) -> None:
        self.muted = False
        self._quiet_since: float | None = None

    def update(self, peak: int, now: float) -> Literal["muted", "recovered"] | None:
        if peak > MUTE_PEAK:
            self._quiet_since = None
            if self.muted:
                self.muted = False
                return "recovered"
            return None
        if self._quiet_since is None:
            self._quiet_since = now
        if not self.muted and now - self._quiet_since >= MUTE_SECONDS:
            self.muted = True
            return "muted"
        return None

    def restart(self) -> None:
        """El flujo se ha reabierto: la cuenta de silencio empieza de nuevo."""
        self._quiet_since = None


class NearMissTracker:
    """Casi detecciones: el máximo de una ventana de 2 s quedó entre 0,15 y el umbral."""

    def __init__(self, threshold: float) -> None:
        self._threshold = threshold
        self._window_start: float | None = None
        self._window_max = 0.0
        self._last_report: float | None = None

    def update(self, score: float, now: float) -> float | None:
        """Devuelve la puntuación de la casi detección cuando hay que registrarla."""
        if self._window_start is None:
            self._window_start = now
        self._window_max = max(self._window_max, score)
        if now - self._window_start < NEAR_MISS_WINDOW_SECONDS:
            return None
        best, self._window_max, self._window_start = self._window_max, 0.0, now
        if not NEAR_MISS_FLOOR <= best < self._threshold:
            return None
        last = self._last_report
        if last is not None and now - last < NEAR_MISS_INTERVAL_SECONDS:
            return None
        self._last_report = now
        return best
