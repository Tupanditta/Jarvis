"""Flujo de salida de audio y nivel de la voz (sintetizador.md).

El callback de PortAudio solo copia el siguiente bloque. Si el dispositivo de salida falla,
la frase se da por dicha tras su duración nominal y el asistente sigue funcionando.
"""
import asyncio
import logging
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

from jarvis_assistant.core.clock import Clock
from jarvis_assistant.speaker.level import level_of

logger = logging.getLogger(__name__)

FADE_SECONDS = 0.03
_STALL_MARGIN_SECONDS = 1.0


class AudioPlayer(Protocol):
    def prepare(self) -> None: ...
    def open(self, sample_rate: int) -> None: ...
    def close(self) -> None: ...
    async def play(self, pcm: np.ndarray, on_start: Callable[[], None] | None = None) -> bool: ...
    def stop(self) -> None: ...
    def current_level(self) -> float: ...


def _default_factory(**kwargs: Any) -> Any:
    import sounddevice

    return sounddevice.OutputStream(**kwargs)


class _Job:
    def __init__(self, pcm: np.ndarray, loop: asyncio.AbstractEventLoop,
                 on_start: Callable[[], None] | None) -> None:
        self.pcm = pcm
        self.loop = loop
        self.on_start = on_start
        self.done: asyncio.Future[bool] = loop.create_future()
        self.position = 0
        self.started = False
        self.finished = False
        self.stop_requested = False

    def notify_start(self) -> None:
        if not self.started:
            self.started = True
            if self.on_start is not None:
                self.on_start()

    def resolve(self, completed: bool) -> None:
        self.finished = True
        if not self.done.done():
            self.done.set_result(completed)


class Player:
    def __init__(self, clock: Clock, stream_factory: Callable[..., Any] = _default_factory):
        self._clock = clock
        self._factory = stream_factory
        self._stream: Any = None
        self._rate = 22050
        self._job: _Job | None = None
        self._level = 0.0

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    def prepare(self) -> None:
        """Carga la biblioteca de audio al arrancar (importar `sounddevice` inicia PortAudio y
        cuesta unos cientos de milisegundos): así no retrasa la apertura de la primera sesión.
        Un fallo no es fatal; `open` lo volverá a intentar."""
        if self._factory is not _default_factory:
            return
        try:
            import sounddevice  # noqa: F401
        except Exception as error:
            logger.warning("No se puede cargar la biblioteca de audio: %s", error)

    def open(self, sample_rate: int) -> None:
        """Abre el flujo en el dispositivo de salida predeterminado. Un fallo no es fatal."""
        self.close()
        self._rate = sample_rate
        try:
            stream = self._factory(
                samplerate=sample_rate, channels=1, dtype="int16", callback=self._callback
            )
            stream.start()
        except Exception as error:
            logger.warning("No se puede abrir el dispositivo de salida: %s", error)
            return
        self._stream = stream

    def close(self) -> None:
        stream, self._stream = self._stream, None
        self._level = 0.0
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:
            logger.debug("Error al cerrar el flujo de salida", exc_info=True)

    async def play(self, pcm: np.ndarray, on_start: Callable[[], None] | None = None) -> bool:
        """Reproduce `pcm`. True si sonó entera; False si se interrumpió."""
        job = _Job(pcm, asyncio.get_running_loop(), on_start)
        duration = len(pcm) / self._rate
        if self._stream is None:
            job.notify_start()
            timer = self._clock.call_later(duration, lambda: job.resolve(True))
        else:
            timer = self._clock.call_later(
                duration + _STALL_MARGIN_SECONDS, lambda: self._stalled(job)
            )
        self._job = job
        try:
            return await job.done
        finally:
            timer.cancel()
            job.finished = True
            self._level = 0.0
            if self._job is job:
                self._job = None

    def _stalled(self, job: _Job) -> None:
        if not job.finished:
            logger.warning("El dispositivo de salida no reproduce: la frase se da por dicha")
            job.notify_start()
            job.resolve(True)
            self.close()

    def stop(self) -> None:
        """Corta la locución en curso con un fundido de 30 ms."""
        job = self._job
        if job is None or job.finished:
            return
        if self._stream is None:
            job.resolve(False)
        else:
            job.stop_requested = True

    def current_level(self) -> float:
        return self._level

    def _callback(self, outdata: np.ndarray, frames: int, _time: object, _status: object) -> None:
        out = outdata[:, 0]
        job = self._job
        if job is None or job.finished:
            out[:] = 0
            self._level = 0.0
            return
        if not job.started:
            job.loop.call_soon_threadsafe(job.notify_start)
        chunk = job.pcm[job.position : job.position + frames]
        job.position += frames
        ended = job.position >= len(job.pcm)
        if job.stop_requested:
            fade = min(len(chunk), round(FADE_SECONDS * self._rate))
            faded = np.zeros(len(chunk), dtype=np.float64)
            faded[:fade] = chunk[:fade] * np.linspace(1.0, 0.0, fade, endpoint=False)
            chunk = faded.astype(np.int16)
        out[: len(chunk)] = chunk
        out[len(chunk) :] = 0
        self._level = level_of(chunk)
        if job.stop_requested or ended:
            job.finished = True
            job.loop.call_soon_threadsafe(job.resolve, not job.stop_requested)
