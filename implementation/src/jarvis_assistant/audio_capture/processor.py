"""Hilo de audio: palabra de activación, detección de voz y modos de captura.

No toca el estado del núcleo: entrega entradas inmutables con `deliver` (que el núcleo
envuelve con `loop.call_soon_threadsafe`) y lee el modo de captura en cada bloque.
`process_block` contiene toda la lógica y se prueba sin hilo, sin hardware y sin modelos.
"""
import logging
import threading
import time
from collections.abc import Callable

import numpy as np

from jarvis_assistant.audio_capture.microphone import apply_gain
from jarvis_assistant.audio_capture.segmenter import Segmenter, SegmenterConfig
from jarvis_assistant.audio_capture.telemetry import (
    MuteDetector,
    NearMissTracker,
    SignalTelemetry,
    level_of,
    peak_of,
)
from jarvis_assistant.audio_capture.types import (
    CaptureMode,
    MicrophoneError,
    MicrophoneSource,
    Utterance,
    VoiceDetector,
    WakeWordDetected,
    WakeWordDetector,
)
from jarvis_assistant.config import AudioSettings
from jarvis_assistant.core.events import MicStatusChanged

logger = logging.getLogger(__name__)

WAKEWORD_DEBOUNCE_SECONDS = 1.0
_READ_TIMEOUT_SECONDS = 0.5


class AudioProcessor:
    def __init__(
        self,
        *,
        microphone: MicrophoneSource,
        wakeword: WakeWordDetector,
        vad: VoiceDetector,
        settings: AudioSettings,
        deliver: Callable[[object], None],
        monotonic: Callable[[], float] = time.monotonic,
        can_refresh: Callable[[], bool] = lambda: True,
    ) -> None:
        self._microphone = microphone
        self._wakeword = wakeword
        self._vad = vad
        self._settings = settings
        self._deliver = deliver
        self._monotonic = monotonic
        self._can_refresh = can_refresh
        self.epoch = 0  # la fija el núcleo; viaja en cada orden entregada

        # (modo, reapertura, generación): una sola asignación, que el hilo lee en cada bloque.
        self._mode_state: tuple[CaptureMode, float | None, int] = (CaptureMode.WAKE_ONLY, None, 0)
        self._seen_generation = 0
        self._reset_detectors = False
        self._segmenter = self._new_segmenter(CaptureMode.WAKE_ONLY)
        self._level = 0.0
        self._last_detection: float | None = None
        self._second_start: float | None = None
        self._second_max = 0.0

        self._telemetry = SignalTelemetry()
        self._mute = MuteDetector()
        self._near_miss = NearMissTracker(settings.wakeword_threshold)
        self._available = True
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # --- Control desde el núcleo -------------------------------------------------------------

    def start(self) -> None:
        """Lanza el hilo de audio."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="audio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)

    def set_mode(self, mode: CaptureMode, *, reopen_at: float | None = None) -> None:
        """Fija el modo. Con `reopen_at`, la captura se reabre en ese instante del reloj
        monótono, descartando lo acumulado y reiniciando los detectores."""
        current, pending, generation = self._mode_state
        if reopen_at is None:
            if mode is current:
                return
            reopen_at = pending  # una reapertura pendiente no se pierde al cambiar de modo
        self._mode_state = (mode, reopen_at, generation + 1)

    @property
    def mode(self) -> CaptureMode:
        return self._mode_state[0]

    @property
    def capturing(self) -> bool:
        """Hay una orden en curso de captura."""
        return self._segmenter.capturing

    def current_level(self) -> float:
        """Último nivel del micrófono (0-1); 0 si no hay una orden en curso de captura."""
        return self._level

    # --- Un bloque ---------------------------------------------------------------------------

    def process_block(self, raw: np.ndarray, now: float) -> None:
        self._telemetry.add(raw, now, self._microphone.take_dropped())
        self._watch_mute(raw, now)
        block = apply_gain(raw, self._settings.input_gain)

        mode, reopen_at, generation = self._mode_state
        if generation != self._seen_generation:
            self._seen_generation = generation
            self._segmenter = self._new_segmenter(mode)
            self._reset_detectors = self._reset_detectors or reopen_at is not None
        if mode is CaptureMode.MUTED or (reopen_at is not None and now < reopen_at):
            self._level = 0.0
            return
        if self._reset_detectors:
            self._reset_detectors = False
            self._wakeword.reset()
            self._vad.reset()

        self._watch_wakeword(block, now)
        if mode is CaptureMode.WAKE_ONLY:
            self._level = 0.0
            return
        is_speech = self._vad.predict(block) >= self._settings.vad_threshold
        segment = self._segmenter.feed(block, is_speech, now)
        self._level = level_of(block) if self._segmenter.capturing else 0.0
        if segment is not None:
            self._deliver(
                Utterance(
                    segment.pcm, segment.started_at, segment.ended_at, self.epoch,
                    segment.restricted,
                )
            )

    def _new_segmenter(self, mode: CaptureMode) -> Segmenter:
        config = SegmenterConfig(
            end_of_speech_seconds=self._settings.end_of_speech_seconds,
            max_utterance_seconds=self._settings.max_utterance_seconds,
        )
        return Segmenter(config, restricted=mode is CaptureMode.WAKE_AND_CLOSING)

    def _watch_wakeword(self, block: np.ndarray, now: float) -> None:
        score = self._wakeword.predict(block)
        self._trace_second(score, now)
        near_miss = self._near_miss.update(score, now)
        if near_miss is not None:
            logger.info(
                "Casi detección de «Hey Jarvis»: puntuación %.2f (umbral %.2f)",
                near_miss, self._settings.wakeword_threshold,
            )
        if score < self._settings.wakeword_threshold:
            return
        last = self._last_detection
        if last is not None and now - last < WAKEWORD_DEBOUNCE_SECONDS:
            return
        self._last_detection = now
        logger.info(
            "«Hey Jarvis» detectada: puntuación %.2f, %s verificador",
            score, "con" if self._wakeword.verifier_active else "sin",
        )
        self._deliver(WakeWordDetected(now))

    def _trace_second(self, score: float, now: float) -> None:
        if self._second_start is None:
            self._second_start = now
        self._second_max = max(self._second_max, score)
        if now - self._second_start >= 1.0:
            logger.debug("Puntuación máxima de «Hey Jarvis» en 1 s: %.2f", self._second_max)
            self._second_start, self._second_max = now, 0.0

    def _watch_mute(self, raw: np.ndarray, now: float) -> None:
        change = self._mute.update(peak_of(raw), now)
        if change == "muted":
            logger.warning(
                "El micrófono entrega silencio digital: el dispositivo no da audio. "
                "Se reabrirá el flujo."
            )
            self._set_available(False)
        elif change == "recovered":
            logger.info("El micrófono vuelve a entregar audio")
            self._set_available(True)

    def _set_available(self, available: bool) -> None:
        if available != self._available:
            self._available = available
            logger.info("Micrófono %s", "disponible" if available else "no disponible")
            self._deliver(MicStatusChanged(available))

    # --- Hilo --------------------------------------------------------------------------------

    def _run(self) -> None:
        started = self._monotonic()
        self._wakeword.load()
        self._vad.load()
        logger.info("Detectores de audio cargados en %.1f s", self._monotonic() - started)
        is_open = False
        retrying = False
        last_reopen = self._monotonic()
        while not self._stop.is_set():
            if not is_open:
                try:
                    if retrying and self._can_refresh():
                        self._microphone.refresh()
                    self._microphone.open()
                except MicrophoneError as error:
                    if self._available:
                        logger.warning("Micrófono no disponible: %s", error)
                    self._set_available(False)
                    retrying = True
                    self._stop.wait(self._settings.mic_retry_seconds)
                    continue
                is_open = True
                last_reopen = self._monotonic()
                self._mute.restart()
                if not self._mute.muted:
                    self._set_available(True)
            try:
                raw = self._microphone.read(_READ_TIMEOUT_SECONDS)
            except MicrophoneError as error:
                logger.warning("Error del flujo del micrófono: %s", error)
                self._microphone.close()
                is_open, retrying = False, True
                self._set_available(False)
                continue
            if raw is None:
                continue
            now = self._monotonic()
            self.process_block(raw, now)
            if self._mute.muted and now - last_reopen >= self._settings.mic_retry_seconds:
                self._microphone.close()  # silencio digital: se reabre igual que si faltara
                is_open, retrying = False, True
        self._microphone.close()
