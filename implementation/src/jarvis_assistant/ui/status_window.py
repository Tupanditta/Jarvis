"""Ventana mínima: el estado en texto y la caja donde el usuario escribe sus órdenes.

Es la entrada del asistente mientras no existe la interfaz completa (entrada-texto.md). Está
visible desde el arranque, también en modo dormido; cerrarla solo la oculta.
"""
import time
from collections.abc import Callable

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget

from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity

ACTIVITY_LABELS = {
    Activity.DORMIDO: "Dormido",
    Activity.REPOSO: "En reposo",
    Activity.ESCUCHANDO: "Escuchando",
    Activity.PROCESANDO: "Procesando",
    Activity.HABLANDO: "Hablando",
    Activity.ESPERANDO: "Esperando",
}

PLACEHOLDER_ASLEEP = "Escriba «Hey Jarvis» para iniciar la sesión"
PLACEHOLDER_RESTING = "En reposo. Escriba «Hey Jarvis»"
PLACEHOLDER_ATTENDING = "Escriba una orden"
_PLACEHOLDERS = {"DORMIDO": PLACEHOLDER_ASLEEP, "IDLE": PLACEHOLDER_RESTING}

TYPING_INTERVAL_SECONDS = 1.0

# Colores de software/Interfaz/README.md.
STYLE = """
QWidget { background-color: #05070B; color: #E6F1F8; }
QLabel#session, QLabel#text { color: #8FA6B8; }
QLineEdit {
    background-color: #0C121C; color: #E6F1F8;
    border: 1px solid #1B2A3A; border-radius: 6px; padding: 8px;
    selection-background-color: #0E7490;
}
QLineEdit:focus { border-color: #2A4560; }
"""


class StatusWindow(QWidget):
    def __init__(
        self,
        publish: Callable[[events.Event], None] = lambda _event: None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self._publish = publish
        self._monotonic = monotonic
        self._last_typing: float | None = None
        self.setWindowTitle("Jarvis")
        self.setMinimumSize(480, 260)
        self.setStyleSheet(STYLE)
        self.session_label = QLabel("")
        self.session_label.setObjectName("session")
        self.state_label = QLabel(ACTIVITY_LABELS[Activity.DORMIDO])
        self.text_label = QLabel("")
        self.text_label.setObjectName("text")
        self.text_label.setWordWrap(True)
        font = self.state_label.font()
        font.setPointSize(22)
        self.state_label.setFont(font)
        self.input = QLineEdit()
        self.input.setPlaceholderText(PLACEHOLDER_ASLEEP)
        self.input.returnPressed.connect(self._submit)
        self.input.textEdited.connect(self._typing)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        for label in (self.session_label, self.state_label, self.text_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        layout.addWidget(self.input)

    def show_and_focus(self) -> None:
        """Muestra la ventana, la trae al frente y deja el foco en la caja."""
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cerrar la ventana la oculta: el proceso sigue en la bandeja."""
        event.ignore()
        self.hide()

    def _submit(self) -> None:
        text = self.input.text()
        self.input.clear()
        self._last_typing = None
        if text.strip():
            self._publish(events.TextSubmitted(text))

    def _typing(self, _text: str) -> None:
        now = self._monotonic()
        if self._last_typing is None or now - self._last_typing >= TYPING_INTERVAL_SECONDS:
            self._last_typing = now
            self._publish(events.UserTyping())

    @Slot(object)
    def on_event(self, event: object) -> None:
        if isinstance(event, events.SessionOpened):
            self.session_label.setText(f"Sesión {event.session_id}: {event.name}")
            self.show_and_focus()
        elif isinstance(event, events.SessionChanged):
            self.session_label.setText(f"Sesión {event.session_id}: {event.name}")
        elif isinstance(event, events.SessionClosed):
            self.session_label.setText("")
        elif isinstance(event, events.AssistantActivityChanged):
            self.state_label.setText(ACTIVITY_LABELS[event.activity])
            self.input.setPlaceholderText(_PLACEHOLDERS.get(event.state, PLACEHOLDER_ATTENDING))
        elif isinstance(event, events.CommandReceived):
            suffix = "" if event.recognized else " (no reconocido)"
            self.text_label.setText(f"«{event.text}»{suffix}")
        elif isinstance(event, events.SpeechStarted):
            self.text_label.setText(event.text)
        elif isinstance(event, events.ShowScreenRequested) and event.visible:
            self.show_and_focus()
