"""Síntesis con Piper y la voz local de `models/piper` (sintetizador.md)."""
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import numpy as np

logger = logging.getLogger(__name__)


class Synthesizer(Protocol):
    sample_rate: int

    def load(self) -> None: ...
    def synthesize(self, text: str) -> np.ndarray: ...  # int16, mono, a `sample_rate`


def _default_factory(model_path: Path, config_path: Path) -> Any:
    from piper import PiperVoice

    return PiperVoice.load(model_path, config_path, use_cuda=False)


class PiperSynthesizer:
    def __init__(
        self,
        models_dir: Path,
        voice: str,
        voice_factory: Callable[[Path, Path], Any] = _default_factory,
    ) -> None:
        self._model_path = models_dir / "piper" / f"{voice}.onnx"
        self._config_path = models_dir / "piper" / f"{voice}.onnx.json"
        self._factory = voice_factory
        self._voice: Any = None
        self.sample_rate = 22050

    def load(self) -> None:
        self._voice = self._factory(self._model_path, self._config_path)
        self.sample_rate = int(self._voice.config.sample_rate)

    def synthesize(self, text: str) -> np.ndarray:
        started = time.perf_counter()
        chunks = [chunk.audio_int16_array for chunk in self._voice.synthesize(text)]
        pcm = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)
        logger.info(
            "Síntesis de %.1f s de voz en %.2f s",
            len(pcm) / self.sample_rate, time.perf_counter() - started,
        )
        return pcm.astype(np.int16, copy=False)
