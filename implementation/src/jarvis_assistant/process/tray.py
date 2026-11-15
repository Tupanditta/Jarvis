"""Icono de la bandeja: estado y menú (proceso.md)."""
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, Qt, QUrl, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity

# Cuatro variantes (Interfaz, sección 9), con colores de los tokens del tema.
ICON_VARIANTS = {
    "dormido": "#5B7083",  # text.muted: gris
    "reposo": "#0E7490",  # primary.dim: cian tenue
    "activo": "#22D3EE",  # primary: cian
    "esperando": "#F5B544",  # status.pending: ámbar
}

ICON_VARIANT_OF = {
    Activity.DORMIDO: "dormido",
    Activity.REPOSO: "reposo",
    Activity.ESCUCHANDO: "activo",
    Activity.PROCESANDO: "activo",
    Activity.HABLANDO: "activo",
    Activity.ESPERANDO: "esperando",
}

ICON_SIZES = (16, 20, 24, 32, 48)

STATE_TEXT = {
    Activity.DORMIDO: "dormido",
    Activity.REPOSO: "en reposo",
    Activity.ESCUCHANDO: "escuchando",
    Activity.PROCESANDO: "procesando",
    Activity.HABLANDO: "hablando",
    Activity.ESPERANDO: "esperando",
}


def tooltip(activity: Activity, session_name: str | None) -> str:
    text = f"Jarvis: {STATE_TEXT[activity]}"
    return f"{text}\n{session_name}" if session_name else text


def make_icon(color: str) -> QIcon:
    """Un círculo con un anillo, de 16 a 48 px."""
    icon = QIcon()
    for size in ICON_SIZES:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        stroke = max(1.0, size / 12)
        painter.setPen(QPen(QColor(color), stroke))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = stroke / 2 + size * 0.04
        painter.drawEllipse(QRectF(inset, inset, size - 2 * inset, size - 2 * inset))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        core = size * 0.42
        painter.drawEllipse(QRectF((size - core) / 2, (size - core) / 2, core, core))
        painter.end()
        icon.addPixmap(pixmap)
    return icon


class TrayController(QObject):
    def __init__(
        self,
        *,
        publish: Callable[[events.Event], None],
        request_quit: Callable[[], None],
        config_dir: Path,
        log_dir: Path,
        open_folder: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__()
        self._publish = publish
        self._open_folder = open_folder or _open_in_file_manager
        self._activity = Activity.DORMIDO
        self._session_name: str | None = None
        self._icons = {key: make_icon(color) for key, color in ICON_VARIANTS.items()}

        self.icon = QSystemTrayIcon()
        self.menu = QMenu()
        self.open_action = self._add("Abrir sesión", lambda: publish(events.OpenSessionRequested()))
        self.show_action = self._add(
            "Mostrar pantalla", lambda: publish(events.ShowScreenRequested())
        )
        self.menu.addSeparator()
        self.config_action = self._add("Abrir configuración", lambda: self._open_folder(config_dir))
        self.log_action = self._add("Abrir registro", lambda: self._open_folder(log_dir))
        self.menu.addSeparator()
        self.quit_action = self._add("Salir", request_quit)
        self.icon.setContextMenu(self.menu)
        self._update()

    def _add(self, text: str, handler: Callable[[], None]) -> QAction:
        action = self.menu.addAction(text)
        action.triggered.connect(lambda _checked=False: handler())
        return action

    def show(self) -> None:
        self.icon.show()

    def hide(self) -> None:
        self.icon.hide()

    def notify(self, title: str, message: str) -> None:
        self.icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning)

    @Slot(object)
    def on_event(self, event: object) -> None:
        if isinstance(event, events.AssistantActivityChanged):
            self._activity = event.activity
        elif isinstance(event, events.SessionOpened | events.SessionChanged):
            self._session_name = event.name
        elif isinstance(event, events.SessionClosed):
            self._session_name = None
        else:
            return
        self._update()

    def _update(self) -> None:
        asleep = self._session_name is None
        self.open_action.setVisible(asleep)
        self.variant = ICON_VARIANT_OF[self._activity]
        self.icon.setIcon(self._icons[self.variant])
        self.icon.setToolTip(tooltip(self._activity, self._session_name))


def _open_in_file_manager(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
