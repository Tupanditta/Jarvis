"""Modelos de vista de los paneles de los módulos (hud.md, sección 3).

Uno por panel, registrados como propiedades de contexto de QML. Como los de `view_models.py`,
reconstruyen su estado solo con los eventos que reciben: cada evento de contenido lleva la
lista completa de su panel. No contienen reglas de negocio.

Los controles de cada ventana piden acciones a su módulo con `ActionRequested`: la acción
entra en la cola de órdenes como si se hubiera escrito, y su resultado vuelve como evento.
"""
from collections.abc import Callable
from datetime import datetime
from pathlib import Path, PurePath
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from jarvis_assistant.core import events

Publish = Callable[[events.Event], None]

DEFAULT_OUTPUT_LINES = 200


def _local(moment: datetime, fmt: str) -> str:
    return moment.astimezone().strftime(fmt)


def _crumbs(path: str) -> list[dict[str, str]]:
    """Las carpetas que llevan hasta `path`, de la raíz a ella, con la ruta de cada una."""
    if not path:
        return []
    pure = PurePath(path)
    chain = [*reversed(pure.parents), pure]
    return [{"name": part.name or part.anchor.rstrip("\\/"), "path": str(part)} for part in chain]


class CommandsModel(QObject):
    """Panel de comandos: el directorio de trabajo y, debajo, el último resultado (listado,
    árbol o salida de un binario). `clear` lo vacía."""

    changed = Signal()

    MODULE = "comandos"

    def __init__(
        self,
        output_lines: int = DEFAULT_OUTPUT_LINES,
        parent: QObject | None = None,
        publish: Publish = lambda _event: None,
    ) -> None:
        super().__init__(parent)
        self._output_lines = output_lines
        self._publish = publish
        self._path = ""
        self._home = ""  # la carpeta en la que empieza la sesión
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
            self._home = self._home or event.path  # el primero de la sesión
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
            self._path = self._home = ""
            self._reset()
        else:
            return
        self.changed.emit()

    # --- Acciones de la ventana --------------------------------------------------------------

    def _request(self, action: str, **params: object) -> None:
        self._publish(events.ActionRequested(self.MODULE, action, params))

    @Slot(str)
    def goTo(self, path: str) -> None:
        """Cambia a la carpeta `path` y la lista."""
        if path:
            self._request("cd", ruta=Path(path))
            self._request("ls")

    @Slot(str)
    def enter(self, name: str) -> None:
        """Entra en la carpeta `name` del directorio de trabajo."""
        if self._path and name:
            self.goTo(str(Path(self._path) / name))

    @Slot()
    def up(self) -> None:
        if self._path:
            self.goTo(str(Path(self._path).parent))

    @Slot()
    def home(self) -> None:
        self.goTo(self._home)

    @Slot()
    def refresh(self) -> None:
        self._request("ls")

    @Slot()
    def tree(self) -> None:
        self._request("arbol")

    @Slot()
    def clear(self) -> None:
        self._request("clear")

    @Slot()
    def terminal(self) -> None:
        self._request("abrir_consola")

    @Slot()
    def reveal(self) -> None:
        """Abre el directorio de trabajo en el gestor de archivos."""
        self._publish(events.ActionRequested("apertura", "abrir_carpeta"))

    @Slot(result=str)
    def outputText(self) -> str:
        """La salida que se ve, en texto: para copiarla."""
        return "\n".join(line["text"] for line in self._lines)

    # --- Propiedades -------------------------------------------------------------------------

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property("QVariantList", notify=changed)
    def crumbs(self) -> list:
        return _crumbs(self._path)

    @Property(bool, notify=changed)
    def canGoUp(self) -> bool:
        return bool(self._path) and Path(self._path).parent != Path(self._path)

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
        self._targets: list[dict[str, Any]] = []
        self._focus_supported = True

    def apply(self, event: object) -> None:
        if isinstance(event, events.OpenedItemsChanged):
            self._focus_supported = event.can_focus_windows
            self._items = [
                {"id": item.id, "title": item.title, "kind": item.kind, "status": item.status,
                 "canFocus": item.can_focus}
                for item in reversed(event.items)  # el más reciente arriba
            ]  # fmt: skip
        elif isinstance(event, events.LaunchTargetsChanged):
            self._targets = [{"name": t.name, "kind": t.kind} for t in event.targets]
        elif isinstance(event, events.SessionOpened):
            self._items = []
        else:
            return
        self.changed.emit()

    @Slot(str)
    def launch(self, name: str) -> None:
        """Abre una aplicación o una página del catálogo por su nombre."""
        if name:
            self._publish(events.ActionRequested("apertura", "abrir", {"objetivo": name}))

    @Property("QVariantList", notify=changed)
    def targets(self) -> list:
        """Aplicaciones y páginas del catálogo: el acceso rápido de la ventana."""
        return self._targets

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

    MODULE = "busqueda"
    KINDS = ("ambos", "archivos", "carpetas")

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._search: events.SearchResultsReady | None = None

    def apply(self, event: object) -> None:
        if isinstance(event, events.SearchResultsReady):
            self._search = event
        elif isinstance(event, events.SessionOpened):
            self._search = None
        else:
            return
        self.changed.emit()

    @Slot(str, str)
    def run(self, query: str, kind: str) -> None:
        """Busca `query`. `kind`: 'ambos', 'archivos' o 'carpetas'."""
        if query.strip():
            self._publish(
                events.ActionRequested(
                    self.MODULE, "buscar",
                    {"consulta": query.strip(), "tipo": kind if kind in self.KINDS else "ambos"},
                )
            )  # fmt: skip

    @Slot(int)
    def open(self, index: int) -> None:
        """Abre el resultado número `index`."""
        self._publish(events.ActionRequested(self.MODULE, "abrir_resultado", {"n": index}))

    @Slot(int)
    def reveal(self, index: int) -> None:
        """Abre la carpeta que contiene el resultado número `index`."""
        self._publish(events.ActionRequested(self.MODULE, "abrir_ubicacion", {"n": index}))

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return self._search is not None

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._search.query if self._search else ""

    @Property(str, notify=changed)
    def kind(self) -> str:
        return self._search.kind if self._search else "ambos"

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
            {"index": r.index, "name": r.name, "isDir": r.is_dir, "folder": r.folder,
             "path": r.path}
            for r in self._search.results
        ]


class HistoryModel(QObject):
    """Panel de historial: la tabla de sesiones o las actividades de una sesión."""

    changed = Signal()

    MODULE = "historial"

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
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

    @Slot()
    def refresh(self) -> None:
        """Muestra las sesiones recientes."""
        self._publish(events.ActionRequested(self.MODULE, "mostrar"))

    @Slot(int)
    def open(self, session_id: int) -> None:
        """Muestra las actividades de la sesión `session_id`."""
        self._publish(events.ActionRequested(self.MODULE, "actividades", {"id": session_id}))

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property("QVariantList", notify=changed)
    def sessions(self) -> list:
        return self._sessions

    @Property(int, notify=changed)
    def errorCount(self) -> int:
        """Actividades en `error` de la sesión que se muestra."""
        return sum(activity["status"] == "error" for activity in self._activities)

    @Property(str, notify=changed)
    def sessionTitle(self) -> str:
        return self._title

    @Property("QVariantList", notify=changed)
    def activities(self) -> list:
        return self._activities


class HelpModel(QObject):
    """Panel de ayuda: las órdenes disponibles, agrupadas por módulo, con un ejemplo."""

    changed = Signal()

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
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

    @Slot()
    def load(self) -> None:
        """Pide las órdenes disponibles: las muestra la intención «ayuda» del núcleo."""
        self._publish(events.ActionRequested("nucleo", "ayuda"))

    @Property("QVariantList", notify=changed)
    def rows(self) -> list:
        return self._rows
