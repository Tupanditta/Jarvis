"""Cola de locuciones e interrupción (sintetizador.md)."""
import asyncio
import logging
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from jarvis_assistant.config import TtsSettings
from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.core.clock import Clock
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import SilenceRequested, SpeechFinished, SpeechStarted
from jarvis_assistant.speaker.phrases import PRELOADED_IDS, advance, render, variants
from jarvis_assistant.speaker.piper_synth import Synthesizer
from jarvis_assistant.speaker.player import AudioPlayer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeechOutcome:
    interrupted: bool


class Speaker:
    def __init__(
        self,
        *,
        synthesizer: Synthesizer,
        player: AudioPlayer,
        bus: EventBus,
        clock: Clock,
        settings: TtsSettings,
        executor: Executor | None = None,
    ) -> None:
        self._synthesizer = synthesizer
        self._player = player
        self._bus = bus
        self._clock = clock
        self._settings = settings
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts")
        self._preloaded: dict[str, np.ndarray] = {}
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._lock = asyncio.Lock()
        self._generation = 0  # cambia en cada `stop`: las frases en cola se descartan
        self._speaking = False
        self._interruptible = False
        self._last_phrase: Phrase | None = None
        bus.subscribe(SilenceRequested, lambda _event: self.stop())

    @property
    def speaking(self) -> bool:
        return self._speaking

    @property
    def last_phrase(self) -> Phrase | None:
        """Última frase dicha que no es del ciclo de vida (RF-94)."""
        return self._last_phrase

    async def preload(self) -> None:
        """Carga la voz y sintetiza las frases del ciclo de vida y las más usadas."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._synthesizer.load)
        for phrase_id in PRELOADED_IDS:
            for text in variants(phrase_id):  # sin parámetros: la plantilla es el texto
                if text not in self._preloaded:
                    self._preloaded[text] = await self._synthesize(text)

    def open_output(self) -> None:
        self._player.open(self._synthesizer.sample_rate)

    def close_output(self) -> None:
        self._player.close()

    async def say(
        self,
        phrase: Phrase,
        *,
        lifecycle: bool = False,
        on_start: Callable[[], None] | None = None,
    ) -> SpeechOutcome:
        """Dice la frase cuando le llega el turno. Termina cuando acaba de sonar o se corta."""
        generation = self._generation
        text = render(phrase)
        async with self._lock:
            if generation != self._generation:
                return SpeechOutcome(interrupted=True)
            pcm = await self._audio(text)
            if generation != self._generation:
                return SpeechOutcome(interrupted=True)

            began = False

            def started() -> None:
                nonlocal began
                began = True
                advance(phrase.id)  # la próxima vez se dice la siguiente variante
                logger.debug("Inicio del audio de %s: %.3f", phrase.id, self._clock.monotonic())
                self._bus.publish(SpeechStarted(text, interruptible=not lifecycle))
                if on_start is not None:
                    on_start()

            self._speaking, self._interruptible = True, not lifecycle
            completed = cancelled = False
            try:
                completed = await self._player.play(pcm, started)
            except asyncio.CancelledError:
                cancelled = True
                self._player.stop()  # el turno se ha cancelado: la frase se corta
                raise
            finally:
                self._speaking = False
                if not lifecycle:
                    self._last_phrase = phrase
                if began or not cancelled:
                    # También si se cancela: la interfaz no debe quedarse en «hablando».
                    self._bus.publish(SpeechFinished(interrupted=not completed))
            return SpeechOutcome(interrupted=not completed)

    def stop(self) -> None:
        """Interrumpe la locución en curso, si se puede, y vacía la cola."""
        self._generation += 1
        if self._speaking and self._interruptible:
            self._player.stop()

    def current_level(self) -> float:
        return self._player.current_level()

    def close(self) -> None:
        self._player.close()
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def _audio(self, text: str) -> np.ndarray:
        if text in self._preloaded:
            return self._preloaded[text]
        if text in self._cache:
            self._cache.move_to_end(text)
            return self._cache[text]
        pcm = await self._synthesize(text)
        self._cache[text] = pcm
        while len(self._cache) > self._settings.cache_size:
            self._cache.popitem(last=False)
        return pcm

    async def _synthesize(self, text: str) -> np.ndarray:
        loop = asyncio.get_running_loop()
        pcm = await loop.run_in_executor(self._executor, self._synthesizer.synthesize, text)
        if self._settings.volume != 1.0:
            pcm = np.clip(np.round(pcm * self._settings.volume), -32768, 32767).astype(np.int16)
        return pcm
