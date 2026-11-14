"""Ventana mínima de estado: el estado en texto, mientras no existe la interfaz completa.

Solo recibe eventos. Se muestra al abrir la sesión y se oculta al volver a dormido.
"""
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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


class StatusWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Jarvis")
        self.setMinimumSize(420, 180)
        self.session_label = QLabel("")
        self.state_label = QLabel(ACTIVITY_LABELS[Activity.DORMIDO])
        self.text_label = QLabel("")
        self.text_label.setWordWrap(True)
        font = self.state_label.font()
        font.setPointSize(22)
        self.state_label.setFont(font)
        layout = QVBoxLayout(self)
        for label in (self.session_label, self.state_label, self.text_label):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

    @Slot(object)
    def on_event(self, event: object) -> None:
        if isinstance(event, events.SessionOpened):
            self.session_label.setText(f"Sesión {event.session_id}: {event.name}")
            self.text_label.setText("")
            self.show()
            self.raise_()
        elif isinstance(event, events.SessionChanged):
            self.session_label.setText(f"Sesión {event.session_id}: {event.name}")
        elif isinstance(event, events.AssistantActivityChanged):
            self.state_label.setText(ACTIVITY_LABELS[event.activity])
            if event.activity is Activity.DORMIDO:
                self.hide()
        elif isinstance(event, events.TranscriptReady):
            suffix = "" if event.recognized else " (no reconocido)"
            self.text_label.setText(f"«{event.text}»{suffix}")
        elif isinstance(event, events.SpeechStarted):
            self.text_label.setText(event.text)
        elif isinstance(event, events.ShowScreenRequested) and event.visible:
            self.showNormal()
            self.raise_()
