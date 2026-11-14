"""Detección de voz con Silero VAD, tal como lo empaqueta `openwakeword`."""
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

_FRAME_SAMPLES = 640  # dos tramas por bloque de 1280 muestras


def _default_factory(model_path: str) -> Any:
    from openwakeword.vad import VAD

    return VAD(model_path=model_path, n_threads=1)


class SileroVad:
    def __init__(self, models_dir: Path, vad_factory: Callable[[str], Any] = _default_factory):
        self._path = models_dir / "openwakeword" / "silero_vad.onnx"
        self._factory = vad_factory
        self._vad: Any = None

    def load(self) -> None:
        self._vad = self._factory(str(self._path))

    def predict(self, block: np.ndarray) -> float:
        """Probabilidad media de voz del bloque (0-1)."""
        return float(self._vad.predict(block, frame_size=_FRAME_SAMPLES))

    def reset(self) -> None:
        if self._vad is not None:
            self._vad.reset_states()
