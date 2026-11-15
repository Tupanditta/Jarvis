"""Nivel de un bloque de audio entre 0 y 1, para la interfaz (RF-83)."""
import math

import numpy as np

FULL_SCALE = 32767
SILENCE_DBFS = -120.0
_LEVEL_FLOOR_DBFS = -50.0
_LEVEL_CEILING_DBFS = -10.0


def rms_of(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block.astype(np.float64))))) if block.size else 0.0


def dbfs(value: float) -> float:
    """Nivel respecto al fondo de escala de 16 bits; el silencio digital da −120."""
    return SILENCE_DBFS if value <= 0 else max(SILENCE_DBFS, 20 * math.log10(value / FULL_SCALE))


def level_of(block: np.ndarray) -> float:
    """Nivel del bloque entre 0 y 1."""
    span = _LEVEL_CEILING_DBFS - _LEVEL_FLOOR_DBFS
    return min(1.0, max(0.0, (dbfs(rms_of(block)) - _LEVEL_FLOOR_DBFS) / span))
