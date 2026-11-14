"""Tipos compartidos de la captura de audio: modos, entradas al núcleo y dependencias."""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np


class CaptureMode(Enum):
    """Qué se atiende del micrófono. Lo fija el núcleo; el hilo de audio lo lee en cada bloque."""

    WAKE_ONLY = "wake_only"
    WAKE_AND_CLOSING = "wake_and_closing"
    COMMANDS = "commands"
    MUTED = "muted"


@dataclass(frozen=True)
class WakeWordDetected:
    """«Hey Jarvis» aceptada."""

    at: float


@dataclass(frozen=True, eq=False)
class Utterance:
    """Orden hablada completa. El audio solo vive en memoria."""

    pcm: np.ndarray  # int16, 16 kHz, mono
    started_at: float
    ended_at: float
    epoch: int
    restricted: bool = False


class MicrophoneError(Exception):
    """El micrófono no está disponible o su flujo ha fallado."""


class MicrophoneSource(Protocol):
    def open(self) -> None: ...  # lanza MicrophoneError
    def read(self, timeout: float) -> np.ndarray | None: ...  # bloque de 1280 muestras o None
    def close(self) -> None: ...
    def refresh(self) -> None: ...  # reinicia la biblioteca de audio para ver dispositivos nuevos
    def take_dropped(self) -> int: ...  # bloques descartados desde la última consulta


class WakeWordDetector(Protocol):
    verifier_active: bool

    def load(self) -> None: ...
    def predict(self, block: np.ndarray) -> float: ...
    def reset(self) -> None: ...


class VoiceDetector(Protocol):
    def load(self) -> None: ...
    def predict(self, block: np.ndarray) -> float: ...
    def reset(self) -> None: ...
