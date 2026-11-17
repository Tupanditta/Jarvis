"""Consumo de CPU y RAM del asistente, en tiempo real, para el medidor de recursos.

El medidor forma parte de la pantalla de sesión: dos anillos fijos en una esquina inferior.
Se muestra u oculta con su botón del selector (`toggle`) y un triple clic lo pasa a la otra
esquina inferior (`switchCorner`). Ambas cosas duran lo que la ejecución.

Solo mide el proceso del asistente: las aplicaciones que abre se lanzan como procesos hijos
y, si se sumaran, el total sería el de esas aplicaciones, no el del asistente.

La CPU es la fracción del equipo entero (todos los núcleos son el 100 %), como en el
Administrador de tareas; la RAM, la memoria física que ocupa el proceso sobre la del equipo.

El modelo solo mide mientras alguna vista lo observa (`watch`/`unwatch`): con el medidor
oculto no gasta nada.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass

import psutil
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

logger = logging.getLogger(__name__)

SAMPLE_MS = 1000


@dataclass(frozen=True)
class Usage:
    cpu: float  # porcentaje del equipo, 0-100
    ram: float  # porcentaje de la memoria física del equipo, 0-100
    ram_bytes: int  # memoria física del proceso (RSS)
    total_bytes: int  # memoria física del equipo


class ProcessUsage:
    """Mide el consumo de un proceso; por defecto, el propio."""

    def __init__(self, process: psutil.Process | None = None) -> None:
        self._process = process or psutil.Process()
        self._cpus = psutil.cpu_count() or 1
        self._process.cpu_percent(None)  # la primera llamada solo fija el punto de partida

    def __call__(self) -> Usage:
        cpu = self._process.cpu_percent(None) / self._cpus
        ram_bytes = self._process.memory_info().rss
        total = psutil.virtual_memory().total
        return Usage(min(100.0, cpu), 100.0 * ram_bytes / total, ram_bytes, total)


def _size(value: int) -> str:
    """`262144000` → `250 MB`; a partir de 1 GB, con un decimal."""
    mb = value / 2**20
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"


class ResourcesModel(QObject):
    """La última medida, refrescada cada `SAMPLE_MS` mientras hay alguna vista."""

    changed = Signal()
    shownChanged = Signal()
    cornerChanged = Signal()

    def __init__(
        self,
        sample: Callable[[], Usage] | None = None,
        parent: QObject | None = None,
        interval_ms: int = SAMPLE_MS,
    ) -> None:
        super().__init__(parent)
        self._sample = sample
        self._usage = Usage(0.0, 0.0, 0, 0)
        self._watchers = 0
        self._shown = True
        self._corner = "right"
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.refresh)

    @Slot()
    def watch(self) -> None:
        """Una vista empieza a mostrar el consumo: mide ya y luego cada intervalo."""
        self._watchers += 1
        if self._watchers == 1:
            self.refresh()
            self._timer.start()

    @Slot()
    def unwatch(self) -> None:
        self._watchers = max(0, self._watchers - 1)
        if self._watchers == 0:
            self._timer.stop()

    @Slot()
    def refresh(self) -> None:
        if self._sample is None:
            self._sample = ProcessUsage()  # se crea al usarlo: sin vista, no mide nada
        try:
            usage = self._sample()
        except (psutil.Error, OSError):
            logger.warning("No se ha podido medir el consumo del asistente", exc_info=True)
            return
        if usage != self._usage:
            self._usage = usage
            self.changed.emit()

    @Slot()
    def toggle(self) -> None:
        """Botón del selector: muestra u oculta el medidor."""
        self._shown = not self._shown
        self.shownChanged.emit()

    @Slot()
    def switchCorner(self) -> None:
        """Triple clic: a la otra esquina inferior."""
        self._corner = "left" if self._corner == "right" else "right"
        self.cornerChanged.emit()

    @Property(bool, notify=shownChanged)
    def shown(self) -> bool:
        return self._shown

    @Property(str, notify=cornerChanged)
    def corner(self) -> str:
        """`left` o `right`: la esquina inferior donde está el medidor."""
        return self._corner

    @property
    def watching(self) -> bool:
        return self._timer.isActive()

    @Property(float, notify=changed)
    def cpu(self) -> float:
        return self._usage.cpu

    @Property(float, notify=changed)
    def ram(self) -> float:
        return self._usage.ram

    @Property(str, notify=changed)
    def ramText(self) -> str:
        return _size(self._usage.ram_bytes)

    @Property(str, notify=changed)
    def totalText(self) -> str:
        return _size(self._usage.total_bytes) if self._usage.total_bytes else ""

    @Property(int, constant=True)
    def cores(self) -> int:
        return psutil.cpu_count() or 1
