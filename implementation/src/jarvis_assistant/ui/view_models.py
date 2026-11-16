"""Modelos de vista expuestos a QML (hud.md, sección 5).

Viven en el hilo de la interfaz. Reconstruyen su estado solo con los eventos que reciben y
publican las acciones del usuario; no interpretan el texto ni contienen reglas de negocio.
"""
import logging
import time
from collections.abc import Callable
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

from jarvis_assistant.config import UiSettings
from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity

logger = logging.getLogger(__name__)

ACTIVITY_LABELS = {
    Activity.DORMIDO: "Dormido",
    Activity.REPOSO: "En reposo",
    Activity.ESCUCHANDO: "Escuchando",
    Activity.PROCESANDO: "Procesando",
    Activity.HABLANDO: "Hablando",
    Activity.ESPERANDO: "Esperando",
}

PLACEHOLDER_ASLEEP = "Escriba el código de activación para iniciar la sesión"
PLACEHOLDER_RESTING = "En reposo. Escriba una orden"
PLACEHOLDER_ATTENDING = "Escriba una orden"
_PLACEHOLDERS = {"DORMIDO": PLACEHOLDER_ASLEEP, "IDLE": PLACEHOLDER_RESTING}

TYPING_INTERVAL_SECONDS = 1.0

Publish = Callable[[events.Event], None]
_Index = QModelIndex | QPersistentModelIndex


class AssistantModel(QObject):
    """Estado, actividad, sesión, nivel de la voz, subtítulos y panel activo."""

    stateChanged = Signal()
    sessionChanged = Signal()
    levelChanged = Signal()
    speakingChanged = Signal()
    subtitlesChanged = Signal()
    activePanelChanged = Signal()
    suggested = Signal(str)  # texto propuesto para la caja de órdenes

    def __init__(
        self,
        publish: Publish = lambda _event: None,
        monotonic: Callable[[], float] = time.monotonic,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._monotonic = monotonic
        self._last_typing: float | None = None
        self._state = "DORMIDO"
        self._activity = Activity.DORMIDO
        self._session_open = False
        self._session_name = ""
        self._session_important = False
        self._level = 0.0
        self._speaking = False
        self._interruptible = False
        self._command_text = ""
        self._command_recognized = True
        self._response_text = ""
        self._subtitle_serial = 0
        self._active_panel = ""

    # --- Eventos del núcleo ------------------------------------------------------------------

    def apply(self, event: object) -> None:
        if isinstance(event, events.AssistantActivityChanged):
            self._state, self._activity = event.state, event.activity
            self.stateChanged.emit()
        elif isinstance(event, events.SessionOpened):
            self._session_open, self._session_name = True, event.name
            self._session_important = False
            self._set_active_panel("")
            self.sessionChanged.emit()
        elif isinstance(event, events.SessionChanged):
            self._session_open, self._session_name = True, event.name
            self._session_important = event.is_important
            self.sessionChanged.emit()
        elif isinstance(event, events.SessionClosed):
            self._session_open, self._session_name = False, ""
            self._session_important = False
            self.sessionChanged.emit()
        elif isinstance(event, events.CommandReceived):
            self._command_text, self._command_recognized = event.text, event.recognized
            self._response_text = ""  # la respuesta anterior era de otra orden
            self._touch_subtitles()
        elif isinstance(event, events.SpeechStarted):
            self._speaking, self._interruptible = True, event.interruptible
            self.speakingChanged.emit()
            if event.interruptible:
                self._response_text = event.text
            else:
                # Frase del ciclo de vida (activación, reposo, cierre): no es conversación y
                # no se muestra; los subtítulos de la orden anterior se retiran.
                self._command_text, self._command_recognized = "", True
                self._response_text = ""
            self._touch_subtitles()
        elif isinstance(event, events.SpeechFinished):
            self._speaking = False
            self.speakingChanged.emit()
            self._set_level(0.0)
        elif isinstance(event, events.AudioLevel):
            self._set_level(event.level if event.source == "assistant" else 0.0)
        elif isinstance(event, events.PanelActivated):
            self._set_active_panel(event.panel)

    def _touch_subtitles(self) -> None:
        self._subtitle_serial += 1
        self.subtitlesChanged.emit()

    def _set_level(self, level: float) -> None:
        if level != self._level:
            self._level = level
            self.levelChanged.emit()

    def _set_active_panel(self, panel: str) -> None:
        if panel != self._active_panel:
            self._active_panel = panel
            self.activePanelChanged.emit()

    # --- Acciones del usuario ----------------------------------------------------------------

    @Slot(str)
    def submit(self, text: str) -> None:
        """Enter en la caja de texto: publica el texto tal cual; un envío vacío no hace nada."""
        self._last_typing = None
        if text.strip():
            # Para medir la latencia hasta la respuesta (RNF-03). Sin el texto (RES-48).
            logger.debug("Texto enviado: %.3f", self._monotonic())
            self._publish(events.TextSubmitted(text))

    @Slot()
    def typing(self) -> None:
        """El usuario teclea: `UserTyping` como mucho una vez por segundo."""
        now = self._monotonic()
        if self._last_typing is None or now - self._last_typing >= TYPING_INTERVAL_SECONDS:
            self._last_typing = now
            self._publish(events.UserTyping())

    @Slot()
    def windowPressed(self) -> None:
        """Pulsación en una ventana flotante: en reposo despierta al asistente."""
        self._publish(events.WindowPressed())

    @Slot()
    def silence(self) -> None:
        """Botón de silencio."""
        self._publish(events.SilenceRequested())

    @Slot(str)
    def suggest(self, text: str) -> None:
        """Una ventana propone una orden: la caja de texto la muestra, sin enviarla."""
        self.suggested.emit(text)

    # --- Propiedades -------------------------------------------------------------------------

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=stateChanged)
    def activity(self) -> str:
        return self._activity.value

    @Property(str, notify=stateChanged)
    def stateText(self) -> str:
        return ACTIVITY_LABELS[self._activity]

    @Property(str, notify=stateChanged)
    def placeholder(self) -> str:
        return _PLACEHOLDERS.get(self._state, PLACEHOLDER_ATTENDING)

    @Property(bool, notify=sessionChanged)
    def sessionOpen(self) -> bool:
        return self._session_open

    @Property(str, notify=sessionChanged)
    def sessionName(self) -> str:
        return self._session_name

    @Property(bool, notify=sessionChanged)
    def sessionImportant(self) -> bool:
        return self._session_important

    @Property(float, notify=levelChanged)
    def level(self) -> float:
        return self._level

    @Property(bool, notify=speakingChanged)
    def speaking(self) -> bool:
        return self._speaking

    @Property(bool, notify=speakingChanged)
    def canSilence(self) -> bool:
        return self._speaking and self._interruptible

    @Property(str, notify=subtitlesChanged)
    def commandText(self) -> str:
        return self._command_text

    @Property(bool, notify=subtitlesChanged)
    def commandRecognized(self) -> bool:
        return self._command_recognized

    @Property(str, notify=subtitlesChanged)
    def responseText(self) -> str:
        return self._response_text

    @Property(int, notify=subtitlesChanged)
    def subtitleSerial(self) -> int:
        return self._subtitle_serial

    @Property(str, notify=activePanelChanged)
    def activePanel(self) -> str:
        return self._active_panel


class TaskListModel(QAbstractListModel):
    """Tareas de la sesión, la más reciente arriba; las de un protocolo, bajo la suya."""

    countChanged = Signal()
    queueChanged = Signal()

    ROLES = ("taskId", "parentId", "module", "description", "status", "detail", "time", "child")
    _FIRST_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tasks: list[events.TaskUpdated] = []
        self._queue: list[str] = []  # órdenes que esperan su turno

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self._FIRST_ROLE + i: QByteArray(name.encode()) for i, name in enumerate(self.ROLES)
        }

    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._tasks)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._tasks):
            return None
        task = self._tasks[index.row()]
        name = self.ROLES[role - self._FIRST_ROLE] if role >= self._FIRST_ROLE else ""
        match name:
            case "taskId":
                return task.task_id
            case "parentId":
                return -1 if task.parent_id is None else task.parent_id
            case "time":
                return task.at.strftime("%H:%M")
            case "child":
                return task.parent_id is not None
            case "detail":
                return task.detail or ""
            case "module" | "description" | "status":
                return getattr(task, name)
        return None

    def apply(self, event: object) -> None:
        if isinstance(event, events.TaskUpdated):
            self._upsert(event)
        elif isinstance(event, events.OrderQueueChanged):
            self._set_queue(list(event.waiting))
        elif isinstance(event, events.SessionOpened):
            self.clear()
            self._set_queue([])

    def _set_queue(self, queue: list[str]) -> None:
        if queue != self._queue:
            self._queue = queue
            self.queueChanged.emit()

    def clear(self) -> None:
        if not self._tasks:
            return
        self.beginResetModel()
        self._tasks = []
        self.endResetModel()
        self.countChanged.emit()

    def _upsert(self, task: events.TaskUpdated) -> None:
        for row, current in enumerate(self._tasks):
            if current.task_id == task.task_id:
                self._tasks[row] = task
                index = self.index(row)
                self.dataChanged.emit(index, index)
                self.countChanged.emit()
                return
        row = self._insertion_row(task)
        self.beginInsertRows(QModelIndex(), row, row)
        self._tasks.insert(row, task)
        self.endInsertRows()
        self.countChanged.emit()

    def _insertion_row(self, task: events.TaskUpdated) -> int:
        if task.parent_id is None:
            return 0
        row = next(
            (i for i, t in enumerate(self._tasks) if t.task_id == task.parent_id), None
        )
        if row is None:
            return 0
        row += 1
        while row < len(self._tasks) and self._tasks[row].parent_id == task.parent_id:
            row += 1
        return row

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._tasks)

    @Property(int, notify=countChanged)
    def pendingCount(self) -> int:
        return sum(task.status == "pendiente" for task in self._tasks)

    @Property(int, notify=countChanged)
    def errorCount(self) -> int:
        return sum(task.status == "error" for task in self._tasks)

    @Property("QStringList", notify=queueChanged)
    def queue(self) -> list[str]:
        """Órdenes en la cola, en su orden: aún no han empezado."""
        return self._queue


class DialogueModel(QObject):
    """La pregunta en curso, si la hay."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dialogue: events.DialogueOpened | None = None
        self._serial = 0

    def apply(self, event: object) -> None:
        if isinstance(event, events.DialogueOpened):
            self._dialogue = event
            self._serial += 1
        elif isinstance(event, events.DialogueClosed | events.SessionClosed):
            if self._dialogue is None:
                return
            self._dialogue = None
        else:
            return
        self.changed.emit()

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return self._dialogue is not None

    @Property(str, notify=changed)
    def question(self) -> str:
        return self._dialogue.question if self._dialogue else ""

    @Property(str, notify=changed)
    def expectedType(self) -> str:
        return self._dialogue.expected_type if self._dialogue else ""

    @Property("QStringList", notify=changed)
    def hints(self) -> list[str]:
        return list(self._dialogue.hints) if self._dialogue else []

    @Property(str, notify=changed)
    def subject(self) -> str:
        """El elemento sobre el que se pregunta, en una línea."""
        if self._dialogue is None or not self._dialogue.subject:
            return ""
        return " · ".join(str(value) for value in self._dialogue.subject.values())

    @Property(float, notify=changed)
    def timeoutSeconds(self) -> float:
        return self._dialogue.timeout_seconds if self._dialogue else 0.0

    @Property(int, notify=changed)
    def serial(self) -> int:
        """Cambia con cada pregunta: reinicia la barra del tiempo de espera."""
        return self._serial


class HudModel(QObject):
    """HUD contraído o expandido (hud.md, sección 2).

    Se expande con cualquier evento de tarea, diálogo o panel y se contrae tras
    `collapse_seconds` sin eventos, siempre que no haya un diálogo abierto ni una tarea
    `pendiente`.
    """

    expandedChanged = Signal()

    CONTENT_EVENTS = (
        events.TaskUpdated,
        events.DialogueOpened,
        events.DialogueClosed,
        events.PanelActivated,
    )

    def __init__(
        self,
        collapse_seconds: float,
        is_busy: Callable[[], bool] = lambda: False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = False
        self._is_busy = is_busy
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(round(collapse_seconds * 1000))
        self._timer.timeout.connect(self._idle)

    def apply(self, event: object) -> None:
        if isinstance(event, self.CONTENT_EVENTS):
            self._set(True)
            self._timer.start()
        elif isinstance(event, events.SessionClosed):
            self.collapse()

    def _idle(self) -> None:
        if self._is_busy():
            self._timer.start()
        else:
            self._set(False)

    def _set(self, expanded: bool) -> None:
        if expanded != self._expanded:
            self._expanded = expanded
            self.expandedChanged.emit()

    @Slot()
    def collapse(self) -> None:
        self._timer.stop()
        self._set(False)

    @Slot()
    def toggle(self) -> None:
        """Botón de expandir o contraer."""
        if self._expanded:
            self.collapse()
        else:
            self._set(True)
            self._timer.start()

    @Property(bool, notify=expandedChanged)
    def expanded(self) -> bool:
        return self._expanded


class UiOptions(QObject):
    """Ajustes de `[ui]` y del modo de diagnóstico; no cambian durante la ejecución."""

    def __init__(
        self, settings: UiSettings, debug: bool = False, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._debug = debug

    @Property(str, constant=True)
    def quality(self) -> str:
        return self._settings.quality

    @Property(bool, constant=True)
    def reduceMotion(self) -> bool:
        return self._settings.reduce_motion

    @Property(str, constant=True)
    def hudCorner(self) -> str:
        return self._settings.hud_corner

    @Property(bool, constant=True)
    def debug(self) -> bool:
        return self._debug
