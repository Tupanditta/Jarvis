"""Puente del bus a Qt: los manejadores corren en el hilo del núcleo y solo emiten señales,
que Qt entrega en el hilo de la interfaz (conexión en cola)."""
from PySide6.QtCore import QObject, Signal

from jarvis_assistant.core import events
from jarvis_assistant.core.event_bus import EventBus

UI_EVENTS: tuple[type[events.Event], ...] = (
    events.SessionOpened,
    events.SessionChanged,
    events.ListeningResumed,
    events.RestEntered,
    events.SessionClosed,
    events.AssistantActivityChanged,
    events.CommandReceived,
    events.SpeechStarted,
    events.ShowScreenRequested,
)


class UiBridge(QObject):
    eventReceived = Signal(object)
    exitRequested = Signal()

    def attach(self, bus: EventBus) -> None:
        """Suscribe el puente a los eventos que muestra la interfaz."""
        for event_type in UI_EVENTS:
            bus.subscribe(event_type, self.eventReceived.emit)
