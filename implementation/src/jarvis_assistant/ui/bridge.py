"""Puente del bus a Qt: los manejadores corren en el hilo del núcleo y solo emiten señales,
que Qt entrega en el hilo de la interfaz (conexión en cola).

Es el único punto de contacto de la interfaz con el backend (hud.md, sección 5). Para
`AudioLevel`, que llega a 20 Hz, solo conserva el último valor pendiente.
"""
import threading

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
    events.SpeechFinished,
    events.ShowScreenRequested,
    events.ShowHudRequested,
    events.TaskUpdated,
    events.OrderQueueChanged,
    events.DialogueOpened,
    events.DialogueClosed,
    events.PanelActivated,
    events.WindowAsideRequested,
    # Contenido de los paneles
    events.WorkdirChanged,
    events.DirectoryListed,
    events.DirectoryTreeBuilt,
    events.CommandOutputAppended,
    events.CommandPanelCleared,
    events.OpenedItemsChanged,
    events.LaunchTargetsChanged,
    events.SearchResultsReady,
    events.RemindersChanged,
    events.ProtocolStarted,
    events.ProtocolFinished,
    events.ProtocolsListed,
    events.HistoryShown,
    events.SessionActivitiesShown,
    events.HelpShown,
)


class UiBridge(QObject):
    eventReceived = Signal(object)
    levelReady = Signal()  # hay un nivel pendiente: se recoge con `take_level`
    exitRequested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._level: events.AudioLevel | None = None

    def attach(self, bus: EventBus) -> None:
        """Suscribe el puente a los eventos que muestra la interfaz."""
        for event_type in UI_EVENTS:
            bus.subscribe(event_type, self.eventReceived.emit)
        bus.subscribe(events.AudioLevel, self._on_level)

    def _on_level(self, event: events.AudioLevel) -> None:
        with self._lock:
            already_pending = self._level is not None
            self._level = event
        if not already_pending:
            self.levelReady.emit()

    def take_level(self) -> events.AudioLevel | None:
        """El último nivel recibido, o None si ya se recogió."""
        with self._lock:
            level, self._level = self._level, None
        return level
