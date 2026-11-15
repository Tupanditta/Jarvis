"""Modelos de vista de los paneles de los módulos (hud.md, sección 3).

Uno por panel, registrados como propiedades de contexto de QML. Como los de `view_models.py`,
reconstruyen su estado solo con los eventos que reciben: cada evento de contenido lleva la
lista completa de su panel. No contienen reglas de negocio.
"""
from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from jarvis_assistant.core import events

Publish = Callable[[events.Event], None]

DEFAULT_OUTPUT_LINES = 200


def _local(moment: datetime, fmt: str) -> str:
    return moment.astimezone().strftime(fmt)


class CommandsModel(QObject):
    """Panel de comandos: el directorio de trabajo y, debajo, el último resultado (listado,
    árbol o salida de un binario). `clear` lo vacía."""

    changed = Signal()

    def __init__(self, output_lines: int = DEFAULT_OUTPUT_LINES, parent: QObject | None = None):
        super().__init__(parent)
        self._output_lines = output_lines
        self._path = ""
        self._reset()

    def _reset(self) -> None:
        self._mode = ""  # "", "listing", "tree" u "output"
        self._entries: list[dict[str, Any]] = []
        self._hidden = 0
        self._nodes: list[dict[str, Any]] = []
        self._truncated = False
        self._task_id: int | None = None
        self._command = ""
        self._status = "pendiente"
        self._lines: list[dict[str, Any]] = []

    def apply(self, event: object) -> None:
        if isinstance(event, events.WorkdirChanged):
            self._path = event.path
        elif isinstance(event, events.DirectoryListed):
            self._reset()
            self._mode, self._path = "listing", event.path
            self._entries = [{"name": e.name, "isDir": e.is_dir} for e in event.entries]
            self._hidden = max(0, event.total - len(event.entries))
        elif isinstance(event, events.DirectoryTreeBuilt):
            self._reset()
            self._mode, self._truncated = "tree", event.truncated
            self._nodes = [
                {"name": n.name, "depth": n.depth, "isDir": n.is_dir} for n in event.nodes
            ]
        elif isinstance(event, events.CommandOutputAppended):
            if self._mode != "output" or event.task_id != self._task_id:
                self._reset()
                self._mode, self._task_id, self._command = "output", event.task_id, event.command
            self._lines += [{"text": line, "error": event.stream == "err"} for line in event.lines]
            del self._lines[: -self._output_lines]  # solo las últimas líneas
        elif isinstance(event, events.TaskUpdated):
            if self._mode != "output" or event.task_id != self._task_id:
                return
            self._status = event.status
        elif isinstance(event, events.CommandPanelCleared):
            self._reset()
        elif isinstance(event, events.SessionOpened):
            self._path = ""
            self._reset()
        else:
            return
        self.changed.emit()

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property("QVariantList", notify=changed)
    def entries(self) -> list:
        return self._entries

    @Property(int, notify=changed)
    def hiddenEntries(self) -> int:
        """Entradas del directorio que no caben en el listado."""
        return self._hidden

    @Property("QVariantList", notify=changed)
    def nodes(self) -> list:
        return self._nodes

    @Property(bool, notify=changed)
    def truncated(self) -> bool:
        return self._truncated

    @Property(str, notify=changed)
    def command(self) -> str:
        return self._command

    @Property(str, notify=changed)
    def commandStatus(self) -> str:
        return self._status

    @Property("QVariantList", notify=changed)
    def lines(self) -> list:
        return self._lines


class OpenedModel(QObject):
    """Panel de aperturas: una tarjeta por elemento abierto, con «traer al frente»."""

    changed = Signal()

    def __init__(self, publish: Publish = lambda _event: None, parent: QObject | None = None):
        super().__init__(parent)
        self._publish = publish
        self._items: list[dict[str, Any]] = []
        self._focus_supported = True

    def apply(self, event: object) -> None:
        if isinstance(event, events.OpenedItemsChanged):
            self._focus_supported = event.can_focus_windows
            self._items = [
                {"id": item.id, "title": item.title, "kind": item.kind, "status": item.status,
                 "canFocus": item.can_focus}
                for item in reversed(event.items)  # el más reciente arriba
            ]  # fmt: skip
        elif isinstance(event, events.SessionOpened):
            self._items = []
        else:
            return
        self.changed.emit()

    @Slot(int)
    def focus(self, item_id: int) -> None:
        """Botón «traer al frente» de una tarjeta."""
        self._publish(events.FocusItemRequested(item_id))

    @Property("QVariantList", notify=changed)
    def items(self) -> list:
        return self._items

    @Property(bool, notify=changed)
    def focusSupported(self) -> bool:
        return self._focus_supported


class SearchModel(QObject):
    """Panel de búsqueda: resultados numerados; el número es lo que el usuario escribe."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._search: events.SearchResultsReady | None = None

    def apply(self, event: object) -> None:
        if isinstance(event, events.SearchResultsReady):
            self._search = event
        elif isinstance(event, events.SessionOpened):
            self._search = None
        else:
            return
        self.changed.emit()

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return self._search is not None

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._search.query if self._search else ""

    @Property(int, notify=changed)
    def total(self) -> int:
        return self._search.total if self._search else 0

    @Property(bool, notify=changed)
    def limited(self) -> bool:
        return bool(self._search and self._search.limited)

    @Property("QVariantList", notify=changed)
    def results(self) -> list:
        if self._search is None:
            return []
        return [
            {"index": r.index, "name": r.name, "isDir": r.is_dir, "folder": r.folder}
            for r in self._search.results
        ]


class HistoryModel(QObject):
    """Panel de historial: la tabla de sesiones o las actividades de una sesión."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mode = ""  # "", "sessions" o "activities"
        self._sessions: list[dict[str, Any]] = []
        self._title = ""
        self._activities: list[dict[str, Any]] = []

    def apply(self, event: object) -> None:
        if isinstance(event, events.HistoryShown):
            self._mode = "sessions"
            self._sessions = [
                {"id": s.id, "name": s.name, "date": _local(s.opened_at, "%d/%m/%Y %H:%M"),
                 "important": s.is_important, "current": s.id == event.current_id}
                for s in event.sessions
            ]  # fmt: skip
        elif isinstance(event, events.SessionActivitiesShown):
            self._mode = "activities"
            self._title = f"{event.session.id} · {event.session.name}"
            self._activities = [
                {"module": a.module, "description": a.description, "status": a.status,
                 "time": _local(a.executed_at, "%H:%M")}
                for a in reversed(event.activities)  # la más reciente arriba
            ]  # fmt: skip
        elif isinstance(event, events.SessionOpened):
            self._mode, self._sessions, self._activities, self._title = "", [], [], ""
        else:
            return
        self.changed.emit()

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property("QVariantList", notify=changed)
    def sessions(self) -> list:
        return self._sessions

    @Property(str, notify=changed)
    def sessionTitle(self) -> str:
        return self._title

    @Property("QVariantList", notify=changed)
    def activities(self) -> list:
        return self._activities


class HelpModel(QObject):
    """Panel de ayuda: las órdenes disponibles, agrupadas por módulo, con un ejemplo."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []

    def apply(self, event: object) -> None:
        if not isinstance(event, events.HelpShown):
            return
        # Lista plana: una fila de cabecera por grupo y una por orden.
        self._rows = []
        for group in event.groups:
            self._rows.append({"header": True, "title": group.title, "example": ""})
            self._rows += [
                {"header": False, "title": entry.description, "example": entry.example}
                for entry in group.entries
            ]
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def rows(self) -> list:
        return self._rows
