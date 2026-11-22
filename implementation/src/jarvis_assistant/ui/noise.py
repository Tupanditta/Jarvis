"""Ruido ambiente en decibelios, en tiempo real, para el medidor de ruido.

El medidor ayuda a medir la concentración: cuánto ruido hay alrededor. Forma parte de la
pantalla de sesión, como el de recursos: un anillo fijo en una esquina inferior. De fábrica
empieza oculto; se muestra u oculta con su botón del selector (`toggle`) y un triple clic lo
pasa a la otra esquina inferior (`switchCorner`). Al abrir sesión, la plantilla del perfil dice
si se ve y los permisos si el perfil puede usarlo (`ui/meter.py`).

Solo capta el nivel de entrada del micrófono predeterminado: no graba ni guarda el audio.
Cada intervalo calcula la energía media (RMS) de lo captado y la pasa a decibelios.

Lo que se muestra es el ruido de fondo: la mediana de las medidas de los últimos
`WINDOW_MS`. Un golpe o una voz de un par de segundos no lo mueven; solo cuenta un ruido que
dure más de media ventana. Una media (sobre todo la de energía) la dispararía cualquier pico.

El micrófono da el nivel relativo a su máximo (dBFS, siempre negativo). Para mostrar una cifra
comparable a la de un sonómetro se le suma `CALIBRATION_DB`. Sin calibrar cada micrófono, la
cifra es aproximada: sirve para comparar momentos, no como medida exacta.

El modelo solo abre el micrófono mientras alguna vista lo observa (`watch`/`unwatch`): con el
medidor oculto no capta nada.
"""
import logging
import math
import statistics
import threading
from collections import deque
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from jarvis_assistant.ui.meter import MeterModel

logger = logging.getLogger(__name__)

SAMPLE_MS = 300
WINDOW_MS = 30_000  # ventana del ruido de fondo
CALIBRATION_DB = 94.0  # dBFS → dB aproximados: 0 dBFS de un micrófono típico ≈ 94 dB
MAX_DB = 120.0
# Niveles del medidor, de menos a más ruido: (id, rótulo, por debajo de cuántos dB). El último
# no tiene tope. QML pinta cada uno de su color (`NoiseMeter.qml`).
TIERS: tuple[tuple[str, str, float], ...] = (
    ("silencio", "SILENCIO", 10.0),
    ("alta", "CONCENTRACIÓN ALTA", 30.0),
    ("media", "CONCENTRACIÓN MEDIA", 65.0),
    ("baja", "CONCENTRACIÓN BAJA", math.inf),
)
UNAVAILABLE_TIER = ("sin_microfono", "SIN MICRÓFONO")

Block = Callable[[np.ndarray], None]


class InputStream(Protocol):
    def stop(self) -> None: ...
    def close(self) -> None: ...


def open_input(on_block: Block) -> InputStream:
    """Abre y arranca el micrófono predeterminado en mono; `on_block` recibe cada bloque de
    muestras (`float32`, entre -1 y 1) en el hilo de audio."""
    import sounddevice  # importarlo inicia PortAudio: solo cuando hace falta

    def callback(data: np.ndarray, frames: int, time: Any, status: Any) -> None:
        on_block(data[:, 0])

    stream = sounddevice.InputStream(channels=1, dtype="float32", callback=callback)
    stream.start()
    return stream


def to_db(rms: float) -> float:
    """Energía media (0-1) → decibelios aproximados, entre 0 y `MAX_DB`."""
    if rms <= 0:
        return 0.0
    return max(0.0, min(MAX_DB, 20 * math.log10(rms) + CALIBRATION_DB))


class NoiseModel(MeterModel):
    """El ruido de fondo de los últimos `WINDOW_MS`, refrescado cada `SAMPLE_MS` mientras hay
    alguna vista."""

    changed = Signal()

    def __init__(
        self,
        open_stream: Callable[[Block], InputStream] | None = None,
        parent: QObject | None = None,
        interval_ms: int = SAMPLE_MS,
    ) -> None:
        super().__init__(False, parent)
        self._open_stream = open_stream
        self._stream: InputStream | None = None
        self._lock = threading.Lock()
        self._energy = 0.0  # suma de cuadrados desde la última medida
        self._samples = 0
        self._readings: deque[float] = deque(maxlen=max(1, round(WINDOW_MS / interval_ms)))
        self._level = 0.0
        self._available = True
        self._watchers = 0
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.refresh)

    @Slot()
    def watch(self) -> None:
        """Una vista empieza a mostrar el ruido: abre el micrófono y mide cada intervalo."""
        self._watchers += 1
        if self._watchers == 1:
            self._open()
            self._timer.start()

    @Slot()
    def unwatch(self) -> None:
        self._watchers = max(0, self._watchers - 1)
        if self._watchers == 0:
            self._timer.stop()
            self.close()

    def close(self) -> None:
        """Suelta el micrófono."""
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:
            logger.warning("No se ha podido cerrar el micrófono", exc_info=True)

    def _open(self) -> None:
        opener = self._open_stream or open_input
        with self._lock:
            self._energy, self._samples = 0.0, 0
        self._readings.clear()  # cada vez que se mira, una ventana nueva
        try:
            self._stream = opener(self._on_block)
        except Exception as error:
            logger.warning("No se puede abrir el micrófono: %s", error)
            self._set(0.0, available=False)
            return
        self._set(self._level, available=True)

    def _on_block(self, samples: np.ndarray) -> None:
        """En el hilo de audio: solo acumula."""
        energy = float(np.dot(samples, samples))
        with self._lock:
            self._energy += energy
            self._samples += len(samples)

    @Slot()
    def refresh(self) -> None:
        with self._lock:
            energy, samples = self._energy, self._samples
            self._energy, self._samples = 0.0, 0
        if samples == 0:
            return  # aún no ha llegado audio: se queda la última medida
        self._readings.append(to_db(math.sqrt(energy / samples)))
        self._set(round(statistics.median(self._readings), 1), available=True)

    def _set(self, level: float, available: bool) -> None:
        if (level, available) != (self._level, self._available):
            self._level, self._available = level, available
            self.changed.emit()

    @property
    def watching(self) -> bool:
        return self._timer.isActive()

    @Property(float, notify=changed)
    def level(self) -> float:
        """Ruido de fondo en decibelios aproximados, 0-`MAX_DB`."""
        return self._level

    @Property(bool, notify=changed)
    def available(self) -> bool:
        """Falso si no se ha podido abrir el micrófono."""
        return self._available

    def _tier(self) -> tuple[str, str]:
        if not self._available:
            return UNAVAILABLE_TIER
        return next((key, text) for key, text, below in TIERS if self._level < below)

    @Property(str, notify=changed)
    def tier(self) -> str:
        """Nivel del ruido (`TIERS`): `silencio`, `alta`, `media` o `baja`; sin micrófono,
        `sin_microfono`."""
        return self._tier()[0]

    @Property(str, notify=changed)
    def focusText(self) -> str:
        """Lo que el ruido deja concentrarse, para el rótulo del medidor."""
        return self._tier()[1]
