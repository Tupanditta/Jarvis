"""Transcripción con `faster-whisper` en CPU (transcriptor.md, AD-06).

El modelo se carga al abrir la sesión y se libera al cerrarla. Todo el trabajo corre en un
ejecutor de un solo hilo y con prioridad baja, así que las transcripciones son secuenciales.
"""
import asyncio
import logging
import sys
import time
from collections.abc import Callable, Sequence
from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from jarvis_assistant.config import SttSettings
from jarvis_assistant.transcriber.filters import filter_transcript
from jarvis_assistant.transcriber.vocabulary import render_prompt

logger = logging.getLogger(__name__)

_THREAD_PRIORITY_BELOW_NORMAL = -1


def default_threads(physical_cores: int | None) -> int:
    """`min(4, núcleos físicos − 1)`, con un mínimo de 1."""
    return max(1, min(4, (physical_cores or 2) - 1))


def lower_thread_priority() -> None:
    """Baja la prioridad del hilo actual para no restar CPU a la animación."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentThread.restype = ctypes.c_void_p
        kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
        kernel32.SetThreadPriority(kernel32.GetCurrentThread(), _THREAD_PRIORITY_BELOW_NORMAL)
    except Exception:
        logger.debug("No se ha podido bajar la prioridad del hilo", exc_info=True)


def _default_factory(model_dir: str, cpu_threads: int) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(
        model_dir, device="cpu", compute_type="int8", cpu_threads=cpu_threads,
        local_files_only=True,
    )


def _physical_cores() -> int | None:
    import psutil

    return psutil.cpu_count(logical=False)


class WhisperTranscriber:
    def __init__(
        self,
        models_dir: Path,
        settings: SttSettings,
        *,
        model_factory: Callable[[str, int], Any] = _default_factory,
        executor: Executor | None = None,
    ) -> None:
        self._model_dir = models_dir / f"faster-whisper-{settings.model}"
        self._settings = settings
        self._factory = model_factory
        self._executor = executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="stt", initializer=lower_thread_priority
        )
        self._model: Any = None
        self._loading: asyncio.Future[Any] | None = None
        self._generation = 0  # cambia en cada `unload`: una carga anterior se descarta
        self._terms: tuple[str, ...] = ()
        self._prompt = ""

    @property
    def loaded(self) -> bool:
        return self._model is not None

    async def load(self) -> None:
        """Carga el modelo si falta. Varias llamadas comparten la misma carga."""
        while self._model is None:
            if self._loading is None:
                loop = asyncio.get_running_loop()
                self._loading = loop.run_in_executor(self._executor, self._load_sync)
            generation, loading = self._generation, self._loading
            try:
                model = await asyncio.shield(loading)
            finally:
                if self._loading is loading:
                    self._loading = None
            if generation != self._generation:
                return  # se liberó mientras cargaba
            self._model = model

    def _load_sync(self) -> Any:
        started = time.perf_counter()
        threads = self._settings.cpu_threads or default_threads(_physical_cores())
        model = self._factory(str(self._model_dir), threads)
        logger.info(
            "Transcriptor cargado en %.2f s (%d hilos)", time.perf_counter() - started, threads
        )
        return model

    def unload(self) -> None:
        self._generation += 1
        self._model = None
        self._loading = None

    def set_vocabulary(self, terms: Sequence[str]) -> None:
        self._terms = tuple(terms)
        self._prompt = render_prompt(self._terms, self._settings.vocabulary_max_chars)

    async def transcribe(self, pcm: np.ndarray, *, restricted: bool = False) -> str:
        """Texto de la orden, o vacío si no hay voz. Espera a la carga si no ha terminado."""
        await self.load()
        model = self._model
        if model is None:
            return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._transcribe_sync, model, pcm, restricted, self._prompt,
            self._terms,
        )

    def _transcribe_sync(
        self, model: Any, pcm: np.ndarray, restricted: bool, prompt: str, terms: Sequence[str]
    ) -> str:
        started = time.perf_counter()
        audio = pcm.astype(np.float32) / 32768.0
        segments, _info = model.transcribe(
            audio,
            language="es",
            beam_size=1 if restricted else self._settings.beam_size,
            condition_on_previous_text=False,
            vad_filter=False,
            temperature=0,
            initial_prompt=prompt or None,
        )
        spoken = [
            segment.text
            for segment in segments
            if segment.no_speech_prob <= self._settings.no_speech_threshold
        ]
        text = filter_transcript(" ".join(spoken), terms)
        logger.info(
            "Transcripción de %.1f s de audio en %.2f s",
            len(pcm) / 16000, time.perf_counter() - started,
        )
        logger.debug("Texto transcrito: %r", text)  # RES-48: solo en DEBUG
        return text

    def close(self) -> None:
        self.unload()
        self._executor.shutdown(wait=False, cancel_futures=True)
