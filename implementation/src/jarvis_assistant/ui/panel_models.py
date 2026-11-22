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
from jarvis_assistant.core.action_api import MAIN_CONSOLE

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
    """Panel de una consola de comandos: el directorio de trabajo y, debajo, el último
    resultado (listado, árbol o salida de un binario). `clear` lo vacía.

    Solo atiende los eventos de su consola (`console`) y sus controles piden las acciones en
    ella: cada ventana de Comandos es independiente de las demás."""

    changed = Signal()

    MODULE = "comandos"

    def __init__(
        self,
        output_lines: int = DEFAULT_OUTPUT_LINES,
        parent: QObject | None = None,
        publish: Publish = lambda _event: None,
        console: str = MAIN_CONSOLE,
        home: str = "",
    ) -> None:
        """`home`: la carpeta personal, si ya se sabe (una consola abierta en plena sesión)."""
        super().__init__(parent)
        self._output_lines = output_lines
        self._publish = publish
        self.console = console
        self._path = ""
        self._home = home  # la carpeta en la que empieza la sesión
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
        if getattr(event, "console", self.console) != self.console:
            return  # de otra consola
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
        self._publish(events.ActionRequested(self.MODULE, action, params, self.console))

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
        self._publish(events.ActionRequested("apertura", "abrir_carpeta", console=self.console))

    @Slot()
    def duplicate(self) -> None:
        """Abre otra ventana de Comandos, independiente, en la carpeta de esta."""
        self._publish(events.ConsoleRequested(self.console))

    @Slot(result=str)
    def outputText(self) -> str:
        """La salida que se ve, en texto: para copiarla."""
        return "\n".join(line["text"] for line in self._lines)

    # --- Propiedades -------------------------------------------------------------------------

    @property
    def home_path(self) -> str:
        """La carpeta en la que empezó la sesión: la de «Carpeta personal»."""
        return self._home

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


class ConsolesModel(QObject):
    """Los paneles de las consolas de Comandos: el de la principal y uno por cada consola
    extra (`ConsoleOpened`). La ventana de una consola toma el suyo con `get`."""

    def __init__(
        self,
        output_lines: int = DEFAULT_OUTPUT_LINES,
        parent: QObject | None = None,
        publish: Publish = lambda _event: None,
    ) -> None:
        super().__init__(parent)
        self._output_lines = output_lines
        self._publish = publish
        self.main = CommandsModel(output_lines, self, publish)
        self._models: dict[str, CommandsModel] = {MAIN_CONSOLE: self.main}

    def apply(self, event: object) -> None:
        if isinstance(event, events.ConsoleOpened) and event.console not in self._models:
            self._models[event.console] = CommandsModel(
                self._output_lines, self, self._publish, event.console, self.main.home_path
            )
        elif isinstance(event, events.ConsoleClosed):
            self.remove(event.console)
            return
        elif isinstance(event, events.SessionOpened | events.SessionClosed):
            self._drop_extras()
        for model in list(self._models.values()):
            model.apply(event)

    def _drop_extras(self) -> None:
        for console in [key for key in self._models if key != MAIN_CONSOLE]:
            self.remove(console)

    def remove(self, console: str) -> None:
        """La ventana de la consola se ha cerrado: su panel desaparece."""
        if console == MAIN_CONSOLE:
            return
        model = self._models.pop(console, None)
        if model is not None:
            model.deleteLater()

    def __contains__(self, console: str) -> bool:
        return console in self._models

    @Slot(str, result=QObject)
    def get(self, console: str) -> QObject:
        """El panel de la consola; el de la principal si no la hay."""
        return self._models.get(console, self.main)


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


class CatalogModel(QObject):
    """Ventana Catálogo: aplicaciones, páginas y comandos de terminal, con su formulario para
    añadir y el botón de eliminar de cada fila (eliminar lo confirma el asistente).

    `problem` es el motivo por el que no se ha podido hacer lo último que se pidió desde la
    ventana; `added` avisa a QML de que se ha añadido lo que envió, para vaciar el formulario.
    """

    MODULE = "catalogo"

    changed = Signal()
    problemChanged = Signal()
    added = Signal()

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._items: list[dict[str, Any]] = []
        self._problem = ""
        self._submitting = False  # se ha enviado el formulario y falta la respuesta

    def apply(self, event: object) -> None:
        if isinstance(event, events.CatalogShown):
            self._items = [
                {"id": item.id, "kind": item.kind, "name": item.name, "target": item.target,
                 "aliases": ", ".join(item.aliases), "args": " ".join(item.args)}
                for item in event.items
            ]  # fmt: skip
            self.changed.emit()
            if self._submitting:
                self._submitting = False
                if not event.problem:
                    self.added.emit()
            self._set_problem(event.problem)
        elif isinstance(event, events.SessionClosed):
            self._submitting = False
            self._set_problem("")

    def _set_problem(self, problem: str) -> None:
        if problem != self._problem:
            self._problem = problem
            self.problemChanged.emit()

    @Slot(str, str, str, str, str)
    def add(self, kind: str, name: str, target: str, aliases: str, args: str) -> None:
        """Botón «Añadir» del formulario. Los alias y los argumentos, uno por línea o
        separados por comas."""
        self._submitting = True
        self._set_problem("")
        params = {"tipo": kind, "nombre": name, "destino": target, "alias": aliases}
        if args.strip():
            params["argumentos"] = args
        self._publish(events.ActionRequested(self.MODULE, "añadir", params))

    @Slot(str)
    def remove(self, item_id: str) -> None:
        """Botón «Eliminar» de una fila: el asistente pide confirmación."""
        self._set_problem("")
        self._publish(events.ActionRequested(self.MODULE, "eliminar", {"entrada": item_id}))

    @Slot()
    def load(self) -> None:
        self._publish(events.ActionRequested(self.MODULE, "ver"))

    @Slot()
    def dismissProblem(self) -> None:
        self._set_problem("")

    @Property("QVariantList", notify=changed)
    def items(self) -> list:
        return self._items

    @Property(str, notify=problemChanged)
    def problem(self) -> str:
        return self._problem


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


class RemindersModel(QObject):
    """Panel de recordatorios: la lista numerada (activos y vencidos), con el próximo aviso, la
    fecha límite y el notificado o leído destacado."""

    changed = Signal()

    MODULE = "recordatorio"

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._items: list[dict[str, Any]] = []

    def apply(self, event: object) -> None:
        if not isinstance(event, events.RemindersChanged):
            return
        self._items = [
            {"index": r.index, "id": r.id, "content": r.content,
             "overdue": r.status == "vencido",
             "next": "" if r.next_trigger is None else _local(r.next_trigger, "%d/%m %H:%M"),
             "deadline": "" if r.deadline is None else _local(r.deadline, "%d/%m %H:%M"),
             "highlighted": r.highlighted}
            for r in event.items
        ]  # fmt: skip
        self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        """Muestra los recordatorios."""
        self._publish(events.ActionRequested(self.MODULE, "mostrar"))

    @Property("QVariantList", notify=changed)
    def items(self) -> list:
        return self._items

    @Property(int, notify=changed)
    def overdueCount(self) -> int:
        return sum(item["overdue"] for item in self._items)


class ProtocolModel(QObject):
    """Panel de protocolo: el protocolo en curso o el último, con sus tareas y su progreso
    (tareas terminadas / total), que cambian en cuanto cambia el estado de cada una (RF-57,
    RNF-14); o bien el listado de los protocolos de la configuración (RF-99)."""

    changed = Signal()

    MODULE = "protocolos"

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._reset()

    def _reset(self) -> None:
        self._mode = ""  # "", "run" o "list"
        self._task_id: int | None = None
        self._name = ""
        self._running = False
        self._steps: list[dict[str, Any]] = []
        self._positions: dict[int, int] = {}  # id de subtarea → posición en `_steps`
        self._protocols: list[dict[str, Any]] = []

    def apply(self, event: object) -> None:
        if isinstance(event, events.ProtocolStarted):
            self._mode, self._task_id, self._name = "run", event.task_id, event.name
            self._running = True
            self._steps = [
                {"id": step_id, "module": "", "description": step, "status": "pendiente",
                 "detail": "", "time": ""}
                for step, step_id in zip(event.steps, event.step_ids, strict=True)
            ]  # fmt: skip
            self._positions = {step_id: index for index, step_id in enumerate(event.step_ids)}
        elif isinstance(event, events.TaskUpdated) and event.task_id in self._positions:
            index = self._positions[event.task_id]
            self._steps[index] = {
                **self._steps[index], "module": event.module, "description": event.description,
                "status": event.status, "detail": event.detail or "",
                "time": _local(event.at, "%H:%M"),
            }  # fmt: skip
            self._steps = list(self._steps)  # una lista nueva: QML ve el cambio
        elif isinstance(event, events.ProtocolFinished) and event.task_id == self._task_id:
            self._running = False
        elif isinstance(event, events.ProtocolsListed):
            self._mode = "list"
            self._protocols = [
                {"name": p.name, "aliases": ", ".join(p.aliases), "important": p.important,
                 "steps": len(p.steps), "summary": " · ".join(p.steps)}
                for p in event.protocols
            ]  # fmt: skip
        elif isinstance(event, events.SessionOpened):
            self._reset()
        else:
            return
        self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        """Muestra los protocolos disponibles."""
        self._publish(events.ActionRequested(self.MODULE, "listar"))

    @Slot(str)
    def run(self, name: str) -> None:
        """Ejecuta el protocolo `name`: lo mismo que escribir «protocolo {name}»."""
        self._publish(events.ActionRequested(self.MODULE, "ejecutar", {"protocolo": name}))

    @Slot()
    def showRun(self) -> None:
        """Vuelve del listado al protocolo en curso o al último."""
        if self._task_id is not None:
            self._mode = "run"
            self.changed.emit()

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property(str, notify=changed)
    def name(self) -> str:
        return self._name

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._running

    @Property(bool, notify=changed)
    def hasRun(self) -> bool:
        return self._task_id is not None

    @Property("QVariantList", notify=changed)
    def steps(self) -> list:
        return self._steps

    @Property(int, notify=changed)
    def doneCount(self) -> int:
        """Tareas terminadas, en `completado` o en `error`."""
        return sum(step["status"] != "pendiente" for step in self._steps)

    @Property(int, notify=changed)
    def errorCount(self) -> int:
        return sum(step["status"] == "error" for step in self._steps)

    @Property(float, notify=changed)
    def progress(self) -> float:
        return self.doneCount / len(self._steps) if self._steps else 0.0

    @Property("QVariantList", notify=changed)
    def protocols(self) -> list:
        return self._protocols


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


class AdminModel(QObject):
    """Ventanas del Acedor: Permisos (tabla perfil × módulo), Credenciales y Perfiles.

    Las contraseñas solo se guardan mientras dura la sesión del Acedor: al cerrarla se olvidan.
    Cada una se muestra en su ventana solo cuando el usuario lo pide (lo decide QML)."""

    permissionsChanged = Signal()
    credentialsChanged = Signal()
    profilesChanged = Signal()

    def __init__(
        self, parent: QObject | None = None, publish: Publish = lambda _event: None
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._modules: list[dict[str, str]] = []
        self._matrix: list[dict[str, Any]] = []
        self._credentials: list[dict[str, Any]] = []
        self._profiles: list[dict[str, str]] = []

    def apply(self, event: object) -> None:
        if isinstance(event, events.PermissionsShown):
            self._modules = [{"id": m.id, "name": m.name} for m in event.modules]
            self._matrix = [
                {"id": p.id, "name": p.name,
                 "allowed": [(p.id, m.id) not in event.restricted for m in event.modules]}
                for p in event.profiles
            ]  # fmt: skip
            self.permissionsChanged.emit()
        elif isinstance(event, events.CredentialsShown):
            self._credentials = [
                {"id": item.profile_id, "name": item.profile_name,
                 "password": item.password or "", "available": item.password is not None}
                for item in event.items
            ]  # fmt: skip
            self.credentialsChanged.emit()
        elif isinstance(event, events.ProfilesListed):
            self._profiles = [{"id": p.id, "name": p.name} for p in event.profiles]
            self.profilesChanged.emit()
        elif isinstance(event, events.SessionClosed):
            self._credentials = []
            self.credentialsChanged.emit()

    @Slot(str, str, bool)
    def setPermission(self, profile_id: str, module: str, allowed: bool) -> None:
        self._publish(events.PermissionChangeRequested(profile_id, module, allowed))

    @Slot()
    def showPermissions(self) -> None:
        self._publish(events.ActionRequested("permisos", "ver"))

    @Slot()
    def showCredentials(self) -> None:
        self._publish(events.ActionRequested("credenciales", "ver"))

    @Slot(str)
    def removeProfile(self, profile_id: str) -> None:
        self._publish(events.ProfileRemovalRequested(profile_id))

    @Property("QVariantList", notify=permissionsChanged)
    def modules(self) -> list:
        return self._modules

    @Property("QVariantList", notify=permissionsChanged)
    def matrix(self) -> list:
        return self._matrix

    @Property("QVariantList", notify=credentialsChanged)
    def credentials(self) -> list:
        return self._credentials

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self) -> list:
        return self._profiles
