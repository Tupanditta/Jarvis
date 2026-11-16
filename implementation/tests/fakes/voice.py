"""Dobles de la voz: sintetizador y reproductor."""
import asyncio
from collections.abc import Callable

import numpy as np

from jarvis_assistant.core.clock import Clock

RATE = 1000  # muestras por segundo del sintetizador falso
PHRASE_SECONDS = 1.0


class FakeSynthesizer:
    """Cada frase dura un segundo. Guarda los textos sintetizados."""

    sample_rate = RATE

    def __init__(self) -> None:
        self.loaded = False
        self.texts: list[str] = []

    def load(self) -> None:
        self.loaded = True

    def synthesize(self, text: str) -> np.ndarray:
        self.texts.append(text)
        return np.full(round(RATE * PHRASE_SECONDS), 1000, dtype=np.int16)


class FakePlayer:
    """La frase suena durante su duración según el reloj falso; `stop` la corta."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self.is_open = False
        self.prepared = 0
        self.opened: list[int] = []
        self.closed = 0
        self.played: list[np.ndarray] = []
        self.level = 0.0
        self._done: asyncio.Future[bool] | None = None

    def prepare(self) -> None:
        self.prepared += 1

    def open(self, sample_rate: int) -> None:
        self.is_open = True
        self.opened.append(sample_rate)

    def close(self) -> None:
        self.is_open = False
        self.closed += 1

    async def play(self, pcm: np.ndarray, on_start: Callable[[], None] | None = None) -> bool:
        self.played.append(pcm)
        done: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._done = done
        if on_start is not None:
            on_start()
        self.level = 0.5
        timer = self._clock.call_later(
            len(pcm) / RATE, lambda: done.done() or done.set_result(True)
        )
        try:
            return await done
        finally:
            timer.cancel()
            self.level = 0.0

    def stop(self) -> None:
        if self._done is not None and not self._done.done():
            self._done.set_result(False)

    def current_level(self) -> float:
        return self.level
