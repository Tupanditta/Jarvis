"""Ventanas flotantes de la pantalla de sesión: cuáles hay, dónde están y cuáles se ven.

Cada módulo tiene una ventana. El registro `WINDOWS` es el único sitio donde se declara una:
añadir la ventana de un módulo nuevo es añadir aquí su `WindowSpec` y su archivo en
`qml/panels/`. `WorkspaceModel` guarda la disposición (abierta o cerrada, posición, tamaño y
orden de apilado) y la expone a QML, junto con la posición de las dos barras: el selector de
ventanas y la caja de texto.

Al abrir sesión, la disposición sale de la plantilla del perfil (`config.ScreenLayout`). En la
pantalla dormida, la del perfil elegido, para que la caja de texto ya esté en su sitio. Durante
la sesión el usuario mueve las ventanas libremente; eso no cambia la plantilla. El editor de
plantillas de la ventana de configuración usa este mismo modelo.

Una ventana abierta puede estar apartada: reducida a una pestaña con su título, pegada al
borde o la esquina más cercanos. Conserva su posición y su tamaño, a los que vuelve al
recuperarla. Dónde queda la pestaña lo calcula QML (`Workspace.qml`).

La posición y el tamaño son fracciones del área de trabajo, no píxeles: la disposición vale
igual en cualquier resolución. QML aplica los tamaños mínimos, que sí son píxeles.
"""
import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

from jarvis_assistant.config import (
    ADMIN_PROFILE_ID,
    FACTORY_LAYOUT,
    BarPosition,
    Config,
    ScreenLayout,
    WindowPlacement,
)
from jarvis_assistant.config.layouts import MIN_INPUT_WIDTH
from jarvis_assistant.core import events

logger = logging.getLogger(__name__)

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
    admin: bool = False  # solo en la sesión del Acedor


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
    # Las del Acedor.
    WindowSpec("permisos", "Permisos", "candado", "PermissionsPanel.qml",
               0.015, 0.03, 0.30, 0.60, open=True, min_width=420, admin=True),
    WindowSpec("credenciales", "Credenciales", "llave", "CredentialsPanel.qml",
               0.765, 0.03, 0.22, 0.45, style="cut", admin=True),
    WindowSpec("perfiles", "Perfiles", "sesion", "ProfilesPanel.qml",
               0.765, 0.52, 0.22, 0.42, style="leaf", admin=True),
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
    aside: bool = False  # apartada a un borde; al abrirla de nuevo deja de estarlo

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


def _initial(spec: WindowSpec, order: int, saved: WindowPlacement | None) -> Placement:
    """La disposición de la ventana en la plantilla o, si no la nombra, la de fábrica."""
    if saved is None:
        return Placement(spec.open, spec.x, spec.y, spec.width, spec.height, order)
    return Placement(
        saved.open, saved.x, saved.y, saved.width, saved.height, saved.order
    ).bounded()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


class WorkspaceModel(QAbstractListModel):
    """Las ventanas flotantes, en el orden del registro. No contiene reglas de negocio."""

    changed = Signal()
    barsChanged = Signal()

    ROLES = ("windowId", "title", "icon", "component", "open", "fx", "fy", "fw", "fh",
             "order", "focused", "aside", "minWidth", "minHeight", "style",
             "available")  # fmt: skip
    _FIRST_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        specs: Sequence[WindowSpec] = WINDOWS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._specs = tuple(specs)
        self._rows = {spec.id: row for row, spec in enumerate(self._specs)}
        self._config: Config | None = None
        self._in_session = False
        self._layout = FACTORY_LAYOUT
        self._dock = FACTORY_LAYOUT.dock
        self._input = FACTORY_LAYOUT.input
        self._input_width = FACTORY_LAYOUT.input_width
        # Ventanas que el perfil de la sesión no puede usar (`PermissionsApplied`): no se ven
        # ni se abren. Hasta saberlo, las del Acedor.
        self._hidden = frozenset(spec.id for spec in self._specs if spec.admin)
        self._placements = self._initial_placements(FACTORY_LAYOUT)

    def _initial_placements(self, layout: ScreenLayout) -> dict[str, Placement]:
        placements = {
            spec.id: _initial(spec, row, layout.windows.get(spec.id))
            for row, spec in enumerate(self._specs)
        }
        return {
            key: replace(p, open=False) if key in self._hidden else p
            for key, p in placements.items()
        }

    @property
    def specs(self) -> tuple[WindowSpec, ...]:
        return self._specs

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
            case "aside":
                return placement.aside
            case "minWidth":
                return spec.min_width
            case "minHeight":
                return spec.min_height
            case "available":
                return spec.id not in self._hidden
        return None

    def placement(self, window_id: str) -> Placement:
        return self._placements[window_id]

    def _front(self) -> str | None:
        """La ventana abierta, sin apartar, que queda encima de las demás."""
        opened = [
            (p.order, key) for key, p in self._placements.items() if p.open and not p.aside
        ]
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

    def _top(self) -> int:
        return max(placement.order for placement in self._placements.values()) + 1

    # --- Eventos del núcleo ------------------------------------------------------------------

    def apply(self, event: object) -> None:
        """Un módulo que muestra algo abre su ventana y la trae al frente. «Aparta …» aparta
        una ventana por su título o, sin título, todas; «desaparta …» las devuelve. Al abrir
        sesión se toma la plantilla de su perfil; dormido, la del perfil elegido."""
        if isinstance(event, events.ConfigApplied):
            self._config = event.config
        elif isinstance(event, events.ProfileSelected) and not self._in_session:
            self._apply_profile(event.profile_id)
        elif isinstance(event, events.SessionOpened):
            self._in_session = True
            self._apply_profile(event.profile_id)
        elif isinstance(event, events.SessionClosed):
            self._in_session = False
        elif isinstance(event, events.PermissionsApplied):
            self._set_hidden(event.hidden_panels)
        elif isinstance(event, events.PanelActivated) and event.panel in self._rows:
            self.show(event.panel)
        elif isinstance(event, events.WindowAsideRequested):
            if event.window is None:
                if event.aside:
                    self.set_aside_all()
                else:
                    self.restore_all()
                return
            window_id = self._find(event.window)
            if window_id is not None:
                if event.aside:
                    self.set_aside(window_id)
                else:
                    self.restore(window_id)

    def _apply_profile(self, profile_id: str) -> None:
        if self._config is None:
            return
        if profile_id == ADMIN_PROFILE_ID:
            self.apply_layout(self._config.layout(""))  # el Acedor usa la de fábrica
        else:
            self.apply_layout(self._config.layout(self._config.profile(profile_id).layout))

    def _set_hidden(self, hidden: frozenset[str]) -> None:
        hidden = frozenset(window for window in hidden if window in self._rows)
        if hidden == self._hidden:
            return
        self._hidden = hidden
        self._placements = {
            key: replace(p, open=False) if key in hidden else p
            for key, p in self._placements.items()
        }
        self.dataChanged.emit(self.index(0), self.index(len(self._specs) - 1))
        self.changed.emit()

    def apply_layout(self, layout: ScreenLayout) -> None:
        """Toma la disposición de la plantilla: ventanas y barras.

        Solo cambia los datos de las filas, sin reiniciar el modelo: así QML conserva las
        ventanas y sus paneles en lugar de destruirlos y crearlos de nuevo (unos 80 ms con
        todas abiertas, justo durante la animación de despertar). Sin cambios, no avisa."""
        self._layout = layout
        placements = self._initial_placements(layout)
        if placements != self._placements:
            self._placements = placements
            self.dataChanged.emit(self.index(0), self.index(len(self._specs) - 1))
            self.changed.emit()
        bars = (layout.dock, layout.input, layout.input_width)
        if bars != (self._dock, self._input, self._input_width):
            self._dock, self._input, self._input_width = bars
            self.barsChanged.emit()

    def to_layout(self, layout_id: str, name: str) -> ScreenLayout:
        """La disposición actual como plantilla: todas las ventanas, sin apartar, y las
        barras. La usa el editor de plantillas."""
        windows = {
            spec.id: WindowPlacement(p.open, p.x, p.y, p.width, p.height, p.order)
            for spec in self._specs
            for p in (self._placements[spec.id],)
        }
        return ScreenLayout(
            layout_id, name, self._dock, self._input, self._input_width, windows
        )

    def _find(self, name: str) -> str | None:
        """La ventana con ese título o ese identificador, sin distinguir mayúsculas."""
        wanted = name.casefold()
        return next(
            (spec.id for spec in self._specs if wanted in (spec.title.casefold(), spec.id)), None
        )

    # --- Acciones del usuario ----------------------------------------------------------------

    @Slot(str)
    def show(self, window_id: str) -> None:
        """Abre la ventana, si no lo está, la recupera si estaba apartada y la pone encima."""
        current = self._placements.get(window_id)
        if current is None or window_id in self._hidden:
            return
        if current.open and window_id == self._front():
            return
        self._set(
            window_id, replace(current, open=True, aside=False, order=self._top()), everything=True
        )

    @Slot(str)
    def raise_window(self, window_id: str) -> None:
        """Pone la ventana encima sin cambiar nada más: una apartada sigue apartada."""
        current = self._placements.get(window_id)
        if current is None or not current.open:
            return
        if not current.aside:
            self.show(window_id)
        elif current.order != self._top() - 1:
            self._set(window_id, replace(current, order=self._top()))

    @Slot(str)
    def close(self, window_id: str) -> None:
        """Cierra la ventana. Una apartada se desvanece como pestaña; al volver a abrirla ya
        no está apartada (`show`)."""
        current = self._placements.get(window_id)
        if current is not None:
            self._set(window_id, replace(current, open=False), everything=True)

    @Slot(str)
    def set_aside(self, window_id: str) -> None:
        """Aparta la ventana a un borde, si está abierta."""
        current = self._placements.get(window_id)
        if current is not None and current.open and not current.aside:
            self._set(window_id, replace(current, aside=True), everything=True)

    @Slot()
    def set_aside_all(self) -> None:
        """Aparta todas las ventanas abiertas."""
        for spec in self._specs:
            self.set_aside(spec.id)

    @Slot(str)
    def restore(self, window_id: str) -> None:
        """Recupera una ventana apartada: vuelve a su sitio y a su tamaño, encima."""
        current = self._placements.get(window_id)
        if current is not None and current.open and current.aside:
            self.show(window_id)

    @Slot()
    def restore_all(self) -> None:
        """Devuelve todas las apartadas. Conservan entre ellas su orden de apilado."""
        ordered = sorted(self._placements.items(), key=lambda item: item[1].order)
        for window_id, _placement in ordered:
            self.restore(window_id)

    @Slot()
    def toggle_aside_all(self) -> None:
        """Botón del selector: si hay más ventanas apartadas que a la vista, las devuelve;
        si no (también a la par), aparta las que están a la vista."""
        if self.asideCount > self.spreadCount:
            self.restore_all()
        else:
            self.set_aside_all()

    @Slot(str)
    def toggle(self, window_id: str) -> None:
        """Botón del selector: abre la ventana, la recupera si estaba apartada, la trae al
        frente o, si ya lo está, la cierra."""
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
        """Vuelve a la disposición de la plantilla."""
        self.apply_layout(self._layout)

    @Slot(str, bool)
    def set_open(self, window_id: str, opened: bool) -> None:
        """Abre o cierra la ventana sin cambiar nada más (editor de plantillas)."""
        current = self._placements.get(window_id)
        if current is None or (opened and window_id in self._hidden):
            return
        if current.open != opened:
            self._set(window_id, replace(current, open=opened, aside=False), everything=True)

    # --- Barras ------------------------------------------------------------------------------

    @Slot(float, float)
    def moveDock(self, x: float, y: float) -> None:
        """Centro del selector de ventanas, en fracciones de la pantalla."""
        self._dock = BarPosition(_clamp(x), _clamp(y))
        self.barsChanged.emit()

    @Slot(float, float, float)
    def placeInput(self, x: float, y: float, width: float) -> None:
        """Centro y ancho de la caja de texto, en fracciones de la pantalla."""
        self._input = BarPosition(_clamp(x), _clamp(y))
        self._input_width = _clamp(width, MIN_INPUT_WIDTH)
        self.barsChanged.emit()

    @Property(float, notify=barsChanged)
    def dockX(self) -> float:
        return self._dock.x

    @Property(float, notify=barsChanged)
    def dockY(self) -> float:
        return self._dock.y

    @Property(float, notify=barsChanged)
    def inputX(self) -> float:
        return self._input.x

    @Property(float, notify=barsChanged)
    def inputY(self) -> float:
        return self._input.y

    @Property(float, notify=barsChanged)
    def inputWidth(self) -> float:
        return self._input_width

    @Slot(str, result=str)
    def component(self, window_id: str) -> str:
        """Archivo QML del panel; vacío si no hay ninguno con ese nombre."""
        row = self._rows.get(window_id)
        return "" if row is None else self._specs[row].component

    @Property(int, notify=changed)
    def openCount(self) -> int:
        return sum(placement.open for placement in self._placements.values())

    @Property(int, notify=changed)
    def spreadCount(self) -> int:
        """Ventanas abiertas sin apartar."""
        return sum(p.open and not p.aside for p in self._placements.values())

    @Property(int, notify=changed)
    def asideCount(self) -> int:
        """Ventanas abiertas y apartadas."""
        return sum(p.open and p.aside for p in self._placements.values())
