"""Ventanas flotantes de la pantalla de sesión: cuáles hay, dónde están y cuáles se ven.

Cada módulo tiene una ventana. El registro `WINDOWS` es el único sitio donde se declara una:
añadir la ventana de un módulo nuevo es añadir aquí su `WindowSpec` y su archivo en
`qml/panels/`. `WorkspaceModel` guarda la disposición (abierta o cerrada, posición, tamaño y
orden de apilado) y la expone a QML; `LayoutStore` la conserva entre ejecuciones.

La posición y el tamaño son fracciones del área de trabajo, no píxeles: la disposición vale
igual en cualquier resolución. QML aplica los tamaños mínimos, que sí son píxeles.
"""
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QTimer,
    Signal,
    Slot,
)

from jarvis_assistant.core import events

logger = logging.getLogger(__name__)

SAVE_DELAY_MS = 400
MIN_FRACTION = 0.08  # ninguna ventana ocupa menos que esto del área, en ancho o en alto

_Index = QModelIndex | QPersistentModelIndex


@dataclass(frozen=True)
class WindowSpec:
    """Ventana flotante: qué muestra y su disposición inicial."""

    id: str  # el nombre de su panel: `PanelActivated(id)` la abre y la trae al frente
    title: str
    icon: str
    component: str  # archivo de `qml/panels/`
    x: float
    y: float
    width: float
    height: float
    open: bool = False  # abierta en la disposición inicial
    min_width: int = 300  # píxeles
    min_height: int = 220
    style: str = "round"  # forma del marco y textura del fondo: una de `FRAME_STYLES`


# Formas de marco que sabe dibujar `qml/components/outline.js`.
FRAME_STYLES = ("round", "cut", "leaf", "bracket")


# Disposición inicial: columnas a los lados del orbe, que ocupa el centro.
WINDOWS: tuple[WindowSpec, ...] = (
    WindowSpec("actividad", "Actividad", "tarea", "ActivityPanel.qml",
               0.015, 0.03, 0.21, 0.55, open=True),
    WindowSpec("comandos", "Comandos", "comandos", "CommandsPanel.qml",
               0.765, 0.03, 0.22, 0.55, style="cut"),
    WindowSpec("aperturas", "Aperturas", "apertura", "OpenedPanel.qml",
               0.765, 0.60, 0.22, 0.38, style="leaf"),
    WindowSpec("busqueda", "Búsqueda", "busqueda", "SearchPanel.qml",
               0.015, 0.60, 0.21, 0.38, style="leaf"),
    WindowSpec("historial", "Historial", "historial", "HistoryPanel.qml",
               0.24, 0.03, 0.17, 0.42, style="cut"),
    WindowSpec("ayuda", "Ayuda", "ayuda", "HelpPanel.qml",
               0.59, 0.03, 0.16, 0.42, style="bracket"),
    WindowSpec("recordatorios", "Recordatorios", "recordatorio", "RemindersPanel.qml",
               0.24, 0.60, 0.19, 0.38),
    WindowSpec("protocolo", "Protocolo", "protocolo", "ProtocolPanel.qml",
               0.57, 0.60, 0.18, 0.38, style="cut"),
)  # fmt: skip


@dataclass(frozen=True)
class Placement:
    """Disposición actual de una ventana."""

    open: bool
    x: float
    y: float
    width: float
    height: float
    order: int  # apilado: la mayor queda encima

    def bounded(self) -> "Placement":
        """La misma disposición, dentro del área de trabajo."""
        width = min(1.0, max(MIN_FRACTION, self.width))
        height = min(1.0, max(MIN_FRACTION, self.height))
        return replace(
            self,
            width=width,
            height=height,
            x=min(1.0 - width, max(0.0, self.x)),
            y=min(1.0 - height, max(0.0, self.y)),
        )


class LayoutStore:
    """Disposición guardada en un archivo JSON. Un archivo ilegible se ignora."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, Mapping[str, Any]]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            logger.warning("No se ha podido leer la disposición de las ventanas: %s", self._path)
            return {}
        windows = data.get("windows") if isinstance(data, dict) else None
        if not isinstance(windows, dict):
            return {}
        return {key: value for key, value in windows.items() if isinstance(value, dict)}

    def save(self, placements: Mapping[str, Placement]) -> None:
        data = {"windows": {key: asdict(placement) for key, placement in placements.items()}}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            logger.warning("No se ha podido guardar la disposición de las ventanas: %s", self._path)


def _restored(spec: WindowSpec, order: int, saved: Mapping[str, Any] | None) -> Placement:
    """La disposición guardada de la ventana si es válida; si no, la inicial."""
    initial = Placement(spec.open, spec.x, spec.y, spec.width, spec.height, order)
    if saved is None:
        return initial
    try:
        return Placement(
            bool(saved["open"]),
            float(saved["x"]), float(saved["y"]), float(saved["width"]), float(saved["height"]),
            int(saved["order"]),
        ).bounded()  # fmt: skip
    except (KeyError, TypeError, ValueError):
        return initial


class WorkspaceModel(QAbstractListModel):
    """Las ventanas flotantes, en el orden del registro. No contiene reglas de negocio."""

    changed = Signal()

    ROLES = ("windowId", "title", "icon", "component", "open", "fx", "fy", "fw", "fh",
             "order", "focused", "minWidth", "minHeight", "style")  # fmt: skip
    _FIRST_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        specs: Sequence[WindowSpec] = WINDOWS,
        store: LayoutStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._specs = tuple(specs)
        self._rows = {spec.id: row for row, spec in enumerate(self._specs)}
        self._store = store
        saved = store.load() if store is not None else {}
        self._placements = {
            spec.id: _restored(spec, row, saved.get(spec.id))
            for row, spec in enumerate(self._specs)
        }
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self.save)

    # --- Modelo ------------------------------------------------------------------------------

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self._FIRST_ROLE + i: QByteArray(name.encode()) for i, name in enumerate(self.ROLES)
        }

    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._specs)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._specs):
            return None
        spec = self._specs[index.row()]
        placement = self._placements[spec.id]
        name = self.ROLES[role - self._FIRST_ROLE] if role >= self._FIRST_ROLE else ""
        match name:
            case "windowId":
                return spec.id
            case "title" | "icon" | "component" | "style":
                return getattr(spec, name)
            case "open":
                return placement.open
            case "fx":
                return placement.x
            case "fy":
                return placement.y
            case "fw":
                return placement.width
            case "fh":
                return placement.height
            case "order":
                return placement.order
            case "focused":
                return placement.open and spec.id == self._front()
            case "minWidth":
                return spec.min_width
            case "minHeight":
                return spec.min_height
        return None

    def placement(self, window_id: str) -> Placement:
        return self._placements[window_id]

    def _front(self) -> str | None:
        """La ventana abierta que queda encima de las demás."""
        opened = [(p.order, key) for key, p in self._placements.items() if p.open]
        return max(opened)[1] if opened else None

    def _set(self, window_id: str, placement: Placement, *, everything: bool = False) -> None:
        if self._placements[window_id] == placement:
            return
        self._placements[window_id] = placement
        if everything:  # cambia qué ventana está encima: afecta a todas las filas
            self.dataChanged.emit(self.index(0), self.index(len(self._specs) - 1))
        else:
            index = self.index(self._rows[window_id])
            self.dataChanged.emit(index, index)
        self.changed.emit()
        if self._store is not None:
            self._save_timer.start()

    def _top(self) -> int:
        return max(placement.order for placement in self._placements.values()) + 1

    # --- Eventos del núcleo ------------------------------------------------------------------

    def apply(self, event: object) -> None:
        """Un módulo que muestra algo abre su ventana y la trae al frente."""
        if isinstance(event, events.PanelActivated) and event.panel in self._rows:
            self.show(event.panel)

    # --- Acciones del usuario ----------------------------------------------------------------

    @Slot(str)
    def show(self, window_id: str) -> None:
        """Abre la ventana, si no lo está, y la pone encima."""
        current = self._placements.get(window_id)
        if current is None:
            return
        if current.open and window_id == self._front():
            return
        self._set(window_id, replace(current, open=True, order=self._top()), everything=True)

    @Slot(str)
    def close(self, window_id: str) -> None:
        current = self._placements.get(window_id)
        if current is not None:
            self._set(window_id, replace(current, open=False), everything=True)

    @Slot(str)
    def toggle(self, window_id: str) -> None:
        """Botón del selector: abre la ventana, la trae al frente o, si ya lo está, la cierra."""
        current = self._placements.get(window_id)
        if current is None:
            return
        if current.open and window_id == self._front():
            self.close(window_id)
        else:
            self.show(window_id)

    @Slot(str, float, float)
    def move(self, window_id: str, x: float, y: float) -> None:
        current = self._placements.get(window_id)
        if current is not None:
            self._set(window_id, replace(current, x=x, y=y).bounded())

    @Slot(str, float, float, float, float)
    def resize(self, window_id: str, x: float, y: float, width: float, height: float) -> None:
        current = self._placements.get(window_id)
        if current is not None:
            self._set(window_id, replace(current, x=x, y=y, width=width, height=height).bounded())

    @Slot()
    def reset(self) -> None:
        """Vuelve a la disposición inicial."""
        self.beginResetModel()
        self._placements = {
            spec.id: _restored(spec, row, None) for row, spec in enumerate(self._specs)
        }
        self.endResetModel()
        self.changed.emit()
        if self._store is not None:
            self._save_timer.start()

    @Slot(str, result=str)
    def component(self, window_id: str) -> str:
        """Archivo QML del panel; vacío si no hay ninguno con ese nombre."""
        row = self._rows.get(window_id)
        return "" if row is None else self._specs[row].component

    def save(self) -> None:
        """Guarda la disposición ahora (también al salir, si había un guardado pendiente)."""
        self._save_timer.stop()
        if self._store is not None:
            self._store.save(self._placements)

    @Property(int, notify=changed)
    def openCount(self) -> int:
        return sum(placement.open for placement in self._placements.values())
