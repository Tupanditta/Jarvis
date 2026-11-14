"""Dobles de la captura de audio: micrófono, palabra de activación y detección de voz."""
from collections import deque

import numpy as np

from jarvis_assistant.audio_capture.types import CaptureMode, MicrophoneError

BLOCK = 1280


def tone(amplitude: int = 1000) -> np.ndarray:
    return np.full(BLOCK, amplitude, dtype=np.int16)


def silence() -> np.ndarray:
    return np.zeros(BLOCK, dtype=np.int16)


class FakeMicrophone:
    """Entrega los bloques encolados; `fail_open` simula un micrófono ausente."""

    def __init__(self) -> None:
        self.blocks: deque[np.ndarray] = deque()
        self.fail_open = False
        self.opened = 0
        self.closed = 0
        self.refreshed = 0
        self.dropped = 0

    def open(self) -> None:
        if self.fail_open:
            raise MicrophoneError("sin micrófono")
        self.opened += 1

    def read(self, timeout: float) -> np.ndarray | None:
        return self.blocks.popleft() if self.blocks else None

    def close(self) -> None:
        self.closed += 1

    def refresh(self) -> None:
        self.refreshed += 1

    def take_dropped(self) -> int:
        dropped, self.dropped = self.dropped, 0
        return dropped


class FakeWakeWord:
    """Devuelve `score` en cada bloque y guarda los bloques que recibe."""

    def __init__(self, score: float = 0.0, verifier_active: bool = False) -> None:
        self.score = score
        self.verifier_active = verifier_active
        self.seen: list[np.ndarray] = []
        self.resets = 0
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def predict(self, block: np.ndarray) -> float:
        self.seen.append(block)
        return self.score

    def reset(self) -> None:
        self.resets += 1


class FakeVad:
    """Hay voz en los bloques que no son silencio digital."""

    def __init__(self) -> None:
        self.seen = 0
        self.resets = 0
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def predict(self, block: np.ndarray) -> float:
        self.seen += 1
        return 1.0 if block.any() else 0.0

    def reset(self) -> None:
        self.resets += 1


class FakeCapture:
    """Doble de `AudioProcessor` para el núcleo: solo registra los modos que se le fijan."""

    def __init__(self) -> None:
        self.mode = CaptureMode.WAKE_ONLY
        self.modes: list[tuple[CaptureMode, float | None]] = []
        self.epoch = 0
        self.level = 0.0
        self.capturing = False
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def set_mode(self, mode: CaptureMode, *, reopen_at: float | None = None) -> None:
        self.mode = mode
        self.modes.append((mode, reopen_at))

    def current_level(self) -> float:
        return self.level
