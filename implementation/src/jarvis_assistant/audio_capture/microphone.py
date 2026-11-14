"""Flujo de entrada del micrófono: apertura, remuestreo y ganancia (captura-audio.md).

`sounddevice` se importa al usarlo y se puede sustituir por un doble. El callback de
PortAudio solo copia el bloque a una cola acotada.
"""
import contextlib
import logging
import queue
import sys
from math import gcd
from typing import Any

import numpy as np

from jarvis_assistant.audio_capture.device_selection import (
    WINDOWS_API_PREFERENCE,
    from_sounddevice,
    select_input_device,
)
from jarvis_assistant.audio_capture.segmenter import BLOCK_SAMPLES, BLOCK_SECONDS, SAMPLE_RATE
from jarvis_assistant.audio_capture.types import MicrophoneError
from jarvis_assistant.config import AudioSettings

logger = logging.getLogger(__name__)

QUEUE_SECONDS = 2.0
STALL_SECONDS = 2.0  # sin bloques durante este tiempo, el flujo se da por caído


def apply_gain(block: np.ndarray, gain: float) -> np.ndarray:
    """Aplica la ganancia con saturación a 16 bits."""
    if gain == 1.0:
        return block
    scaled = np.round(block.astype(np.float64) * gain)
    return np.clip(scaled, -32768, 32767).astype(np.int16)


def resample_to_16k(samples: np.ndarray, rate: int) -> np.ndarray:
    """Remuestreo polifásico a 16 kHz, ajustado a un bloque de 1280 muestras."""
    from scipy.signal import resample_poly

    divisor = gcd(SAMPLE_RATE, rate)
    resampled = resample_poly(samples.astype(np.float64), SAMPLE_RATE // divisor, rate // divisor)
    fitted = np.zeros(BLOCK_SAMPLES, dtype=np.float64)
    size = min(BLOCK_SAMPLES, resampled.size)
    fitted[:size] = resampled[:size]
    return np.clip(np.round(fitted), -32768, 32767).astype(np.int16)


class Microphone:
    """Entrega bloques de 1280 muestras a 16 kHz, mono, int16, sin ganancia."""

    def __init__(self, settings: AudioSettings, sd: Any = None) -> None:
        self._settings = settings
        self._sd = sd
        self._queue: queue.Queue[np.ndarray] = queue.Queue(
            maxsize=round(QUEUE_SECONDS / BLOCK_SECONDS)
        )
        self._stream: Any = None
        self._rate = SAMPLE_RATE
        self._dropped = 0
        self._stalled = 0.0
        self._warned = False

    def _library(self) -> Any:
        if self._sd is None:
            import sounddevice

            self._sd = sounddevice
        return self._sd

    def open(self) -> None:
        sd = self._library()
        try:
            devices = from_sounddevice(sd.query_devices(), sd.query_hostapis())
        except Exception as error:
            raise MicrophoneError(f"No se pueden listar los dispositivos: {error}") from error
        choice = select_input_device(
            devices,
            wanted_name=self._settings.input_device,
            wanted_hostapi=self._settings.input_hostapi,
            api_preference=WINDOWS_API_PREFERENCE if sys.platform == "win32" else (),
        )
        if choice.warning and not self._warned:
            logger.warning(choice.warning)
            self._warned = True
        device = choice.device
        index = None if device is None else device.index
        native = SAMPLE_RATE if device is None else round(device.samplerate)
        self._drain()
        self._stalled = 0.0
        try:
            self._start(sd, index, SAMPLE_RATE)
        except Exception as first_error:
            if native == SAMPLE_RATE:
                raise MicrophoneError(f"No se puede abrir el micrófono: {first_error}") from None
            try:
                self._start(sd, index, native)
            except Exception as error:
                raise MicrophoneError(f"No se puede abrir el micrófono: {error}") from error
        logger.info(
            "Micrófono abierto: %s, API %s, índice %s, %d Hz (%s)",
            "predeterminado" if device is None else device.name,
            "predeterminada" if device is None else device.hostapi,
            index,
            self._rate,
            "16 kHz directos" if self._rate == SAMPLE_RATE else "con remuestreo",
        )

    def _start(self, sd: Any, index: int | None, rate: int) -> None:
        stream = sd.InputStream(
            samplerate=rate,
            blocksize=round(BLOCK_SAMPLES * rate / SAMPLE_RATE),
            device=index,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        try:
            stream.start()
        except Exception:
            stream.close()
            raise
        self._stream, self._rate = stream, rate

    def _callback(self, indata: np.ndarray, _frames: int, _time: object, _status: object) -> None:
        block = indata[:, 0].copy()
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                self._queue.get_nowait()  # se descarta lo más antiguo
            self._dropped += 1
            with contextlib.suppress(queue.Full):
                self._queue.put_nowait(block)

    def read(self, timeout: float) -> np.ndarray | None:
        if self._stream is None:
            raise MicrophoneError("El micrófono no está abierto")
        try:
            block = self._queue.get(timeout=timeout)
        except queue.Empty:
            self._stalled += timeout
            if self._stalled >= STALL_SECONDS or not self._stream.active:
                raise MicrophoneError("El flujo del micrófono no entrega audio") from None
            return None
        self._stalled = 0.0
        return block if self._rate == SAMPLE_RATE else resample_to_16k(block, self._rate)

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:
            logger.debug("Error al cerrar el flujo del micrófono", exc_info=True)

    def refresh(self) -> None:
        """Reinicia PortAudio para que vea los dispositivos conectados después del arranque."""
        sd = self._library()
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            logger.debug("No se ha podido reiniciar PortAudio", exc_info=True)

    def take_dropped(self) -> int:
        dropped, self._dropped = self._dropped, 0
        if dropped:
            logger.warning("Cola del micrófono llena: %d bloques descartados", dropped)
        return dropped

    def _drain(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return
