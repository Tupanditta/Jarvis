"""Icono de la bandeja: estado y menú (proceso.md)."""
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity

ICON_COLORS = {
    Activity.DORMIDO.value: "#5a6270",
    Activity.REPOSO.value: "#2f6f9f",
    Activity.ESCUCHANDO.value: "#35c2ff",
    Activity.PROCESANDO.value: "#f2b632",
    Activity.HABLANDO.value: "#4fd68a",
    Activity.ESPERANDO.value: "#f2b632",
}

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
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(6, 6, 52, 52)
    painter.end()
    return QIcon(pixmap)


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
        self._icons = {key: make_icon(color) for key, color in ICON_COLORS.items()}

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
        self.icon.setIcon(self._icons[self._activity.value])
        self.icon.setToolTip(tooltip(self._activity, self._session_name))


def _open_in_file_manager(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
