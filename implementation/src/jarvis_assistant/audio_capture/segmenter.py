"""Inicio y fin de cada orden hablada (captura-audio.md). Lógica pura, sin audio real.

Recibe bloques de 80 ms ya clasificados como voz o silencio y devuelve el segmento completo
cuando la orden termina. En modo restringido (reposo) solo entrega frases cortas.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16000
BLOCK_SAMPLES = 1280
BLOCK_SECONDS = BLOCK_SAMPLES / SAMPLE_RATE


@dataclass(frozen=True)
class SegmenterConfig:
    end_of_speech_seconds: float = 1.0
    max_utterance_seconds: float = 15.0
    preroll_seconds: float = 0.4
    min_speech_seconds: float = 0.3
    restricted_min_seconds: float = 0.5
    restricted_max_seconds: float = 3.5
    restricted_interval_seconds: float = 2.0


@dataclass(frozen=True, eq=False)
class Segment:
    pcm: np.ndarray  # int16, 16 kHz, mono
    started_at: float
    ended_at: float
    restricted: bool = False


def _blocks(seconds: float) -> int:
    """Bloques necesarios para cubrir `seconds`."""
    return max(1, int(np.ceil(seconds / BLOCK_SECONDS - 1e-9)))


class Segmenter:
    def __init__(self, config: SegmenterConfig, *, restricted: bool = False) -> None:
        self._config = config
        self._restricted = restricted
        self._end_blocks = _blocks(config.end_of_speech_seconds)
        self._max_blocks = _blocks(config.max_utterance_seconds)
        self._preroll: deque[np.ndarray] = deque(maxlen=_blocks(config.preroll_seconds))
        self._last_delivery: float | None = None
        self.reset()

    @property
    def capturing(self) -> bool:
        """Hay una orden en curso de captura."""
        return self._blocks is not None

    def reset(self) -> None:
        """Abandona la orden en curso y olvida el audio anterior."""
        self._preroll.clear()
        self._blocks: list[np.ndarray] | None = None
        self._started_at = 0.0
        self._voiced = 0  # bloques con voz
        self._span = 0  # bloques desde el primero con voz hasta el último con voz
        self._silence = 0  # bloques seguidos sin voz
        self._abandoned = False

    def feed(self, block: np.ndarray, is_speech: bool, now: float) -> Segment | None:
        """Procesa un bloque que empieza en `now`. Devuelve el segmento si la orden termina."""
        if self._abandoned:
            self._silence = 0 if is_speech else self._silence + 1
            if self._silence >= self._end_blocks:
                self.reset()
            return None
        if self._blocks is None:
            if not is_speech:
                self._preroll.append(block)
                return None
            self._started_at = now - len(self._preroll) * BLOCK_SECONDS
            self._blocks = [*self._preroll]
            self._preroll.clear()
        self._blocks.append(block)
        if is_speech:
            self._voiced += 1
            self._span += self._silence + 1
            self._silence = 0
        else:
            self._silence += 1
        if self._restricted and self._span * BLOCK_SECONDS > self._config.restricted_max_seconds:
            self.reset()
            self._abandoned = True
            return None
        if self._silence >= self._end_blocks or len(self._blocks) >= self._max_blocks:
            return self._finish(now + BLOCK_SECONDS)
        return None

    def _finish(self, ended_at: float) -> Segment | None:
        blocks, started_at = self._blocks or [], self._started_at
        voiced, span = self._voiced * BLOCK_SECONDS, self._span * BLOCK_SECONDS
        self.reset()
        if voiced < self._config.min_speech_seconds - 1e-9:
            return None
        if self._restricted:
            if span < self._config.restricted_min_seconds - 1e-9:
                return None
            last = self._last_delivery
            if last is not None and ended_at - last < self._config.restricted_interval_seconds:
                return None
            self._last_delivery = ended_at
        return Segment(np.concatenate(blocks), started_at, ended_at, self._restricted)
