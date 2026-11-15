"""Módulo Comandos: directorio de trabajo, listado, árbol y binarios externos (comandos.md).

`cd`, `ls`, `clear` y el árbol son nativos: nunca se ejecutan como subprocesos. Los binarios
salen de la lista permitida (RN-45) y se lanzan sin intérprete de órdenes.
"""
import asyncio
import logging
import os
import shutil
from collections import deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    WORKDIR,
    ActionContext,
    ActionResult,
    CommandLine,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import Entry, TreeNode
from jarvis_assistant.core.workdir import folder_name, invalid_folder
from jarvis_assistant.speaker.phrases import count

logger = logging.getLogger(__name__)

PANEL = "comandos"
MAX_LISTED = 500
TREE_MAX_DEPTH = 3
TREE_MAX_ENTRIES = 200
OUTPUT_BATCH_SECONDS = 0.2

Launcher = Callable[[str, Sequence[str], Path], Awaitable[Any]]


async def launch_process(executable: str, args: Sequence[str], cwd: Path) -> Any:
    """Lanza el binario sin intérprete de órdenes. `FileNotFoundError` si no existe."""
    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(executable)
    return await asyncio.create_subprocess_exec(
        resolved, *args, cwd=str(cwd),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )  # fmt: skip


def kill_process_tree(pid: int) -> None:
    """Termina el proceso y todos sus descendientes."""
    import psutil

    try:
        root = psutil.Process(pid)
    except psutil.Error:
        return
    for process in [*root.children(recursive=True), root]:
        try:
            process.kill()
        except psutil.Error:
            continue


@dataclass
class _TreeDir:
    path: Path
    depth: int
    children: list["_TreeItem"] = field(default_factory=list)


@dataclass
class _TreeItem:
    name: str
    depth: int
    is_dir: bool
    inner: _TreeDir | None = None


@dataclass(frozen=True)
class Tree:
    nodes: tuple[TreeNode, ...]
    dirs: int
    files: int
    truncated: bool


def _sorted_entries(path: Path) -> list[tuple[str, bool]]:
    """Entradas de `path`: carpetas primero, orden alfabético sin distinguir mayúsculas.
    No sigue enlaces simbólicos. Una carpeta ilegible se ve vacía."""
    found: list[tuple[str, bool]] = []
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                except OSError:
                    is_dir = False
                found.append((entry.name, is_dir))
    except OSError:
        return []
    return sorted(found, key=lambda item: (not item[1], item[0].casefold(), item[0]))


def build_tree(
    root: Path, max_depth: int = TREE_MAX_DEPTH, max_entries: int = TREE_MAX_ENTRIES
) -> Tree:
    """Mapeo de entorno (RN-40): recorrido en anchura hasta `max_depth` niveles y
    `max_entries` entradas. La raíz no cuenta como nivel ni como entrada."""
    top = _TreeDir(root, 0)
    queue: deque[_TreeDir] = deque([top])
    total = dirs = files = 0
    truncated = False
    while queue and not truncated:
        current = queue.popleft()
        for name, is_dir in _sorted_entries(current.path):
            if total >= max_entries:
                truncated = True
                break
            item = _TreeItem(name, current.depth + 1, is_dir)
            current.children.append(item)
            total += 1
            if is_dir:
                dirs += 1
                if item.depth < max_depth:
                    item.inner = _TreeDir(current.path / name, item.depth)
                    queue.append(item.inner)
            else:
                files += 1
    nodes: list[TreeNode] = []

    def draw(directory: _TreeDir) -> None:
        for item in directory.children:
            nodes.append(TreeNode(item.name, item.depth, item.is_dir))
            if item.inner is not None:
                draw(item.inner)

    draw(top)
    return Tree(tuple(nodes), dirs, files, truncated)


class CommandRunner:
    name = "comandos"
    title = "Comandos"

    def __init__(
        self,
        launcher: Launcher = launch_process,
        kill_tree: Callable[[int], None] = kill_process_tree,
    ) -> None:
        self._launch = launcher
        self._kill_tree = kill_tree
        self._running = False  # hay un binario lanzado con una orden

    def intents(self) -> Sequence[IntentSpec]:
        path = Slot("ruta", SlotType.DIR_PATH)
        here = frozenset({WORKDIR})  # la acción usa el directorio de trabajo
        return (
            IntentSpec(
                # «ve {ruta}» atiende «ve atrás», «ve arriba» y «ve aquí».
                "cd", ("ve a {ruta}", "ve {ruta}", "entra en {ruta}",
                       "cambia a la carpeta {ruta}", "cd {ruta}"),
                (path,), "Cambiar de carpeta", "Ve a proyectos barra jarvis", PANEL,
                writes=here,
            ),
            IntentSpec(
                "ls", ("lista", "lista el directorio", "qué hay aquí", "ls"), (),
                "Listar la carpeta actual", "Qué hay aquí", PANEL, reads=here,
            ),
            IntentSpec(
                "pwd", ("dónde estoy", "directorio actual", "en qué carpeta estoy"), (),
                "Decir la carpeta actual", "Dónde estoy", PANEL, reads=here,
            ),
            IntentSpec(
                "arbol", ("árbol", "muestra el árbol", "árbol de {ruta}",
                          "muestra el árbol de {ruta}", "mapa de {ruta}"),
                (Slot("ruta", SlotType.DIR_PATH, optional=True),),
                "Mostrar el árbol de una carpeta", "Árbol de documentos", PANEL, reads=here,
            ),
            IntentSpec(
                "clear", ("limpia", "limpia la consola", "clear"), (),
                "Limpiar el panel de comandos", "Limpia la consola", PANEL,
            ),
            IntentSpec(
                "ejecutar", ("ejecuta {comando}", "lanza el comando {comando}",
                             "corre {comando}"),
                (Slot("comando", SlotType.COMMAND_LINE),),
                "Ejecutar un programa permitido", "Ejecuta git status", PANEL, reads=here,
            ),
            IntentSpec(
                "abrir_consola", ("abre una consola", "abre la consola", "abre una terminal",
                                  "abre la terminal"),
                (), "Abrir la terminal del sistema", "Abre una terminal", reads=here,
            ),
        )  # fmt: skip

    async def on_session_opened(self, ctx: ActionContext) -> None:
        self._running = False
        ctx.publish(events.CommandPanelCleared())
        ctx.publish(events.WorkdirChanged(str(ctx.workdir.path)))

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        match action:
            case "cd":
                return self._cd(params["ruta"], ctx)  # type: ignore[arg-type]
            case "ls":
                return self._ls(ctx)
            case "pwd":
                return self._pwd(ctx)
            case "arbol":
                return await self._tree(params.get("ruta"), ctx)  # type: ignore[arg-type]
            case "clear":
                ctx.publish(events.CommandPanelCleared())
                return ActionResult("completado")
            case "ejecutar":
                return await self._run(params["comando"], ctx)  # type: ignore[arg-type]
            case "abrir_consola":
                return await self._open_terminal(ctx)
        raise ValueError(f"Acción desconocida: {action}")

    # --- Directorio de trabajo ---------------------------------------------------------------

    def _cd(self, target: Path, ctx: ActionContext) -> ActionResult:
        path = ctx.workdir.resolve(target)
        invalid = invalid_folder(path)
        if invalid is not None:
            return ActionResult("error", invalid)
        ctx.workdir.change(path)
        ctx.publish(events.WorkdirChanged(str(path)))
        return ActionResult(
            "completado", Phrase("comandos.cd", {"carpeta": folder_name(path)}),
            description=f"cd {path}",
        )  # fmt: skip

    def _ls(self, ctx: ActionContext) -> ActionResult:
        path = ctx.workdir.path
        invalid = invalid_folder(path)
        if invalid is not None:
            return ActionResult("error", invalid)
        entries = _sorted_entries(path)
        dirs = sum(is_dir for _, is_dir in entries)
        ctx.publish(
            events.DirectoryListed(
                str(path),
                tuple(Entry(name, is_dir) for name, is_dir in entries[:MAX_LISTED]),
                len(entries),
            )
        )
        return ActionResult(
            "completado",
            Phrase("comandos.ls", {
                "carpetas": count(dirs, "carpeta", "carpetas"),
                "archivos": count(len(entries) - dirs, "archivo", "archivos"),
            }),
            description=f"ls {path}",
        )  # fmt: skip

    def _pwd(self, ctx: ActionContext) -> ActionResult:
        path = str(ctx.workdir.path)
        ctx.publish(events.WorkdirChanged(path))
        return ActionResult("completado", Phrase("comandos.pwd", {"ruta": path}))

    async def _tree(self, target: Path | None, ctx: ActionContext) -> ActionResult:
        root = ctx.workdir.path if target is None else ctx.workdir.resolve(target)
        invalid = invalid_folder(root)
        if invalid is not None:
            return ActionResult("error", invalid)
        tree = await asyncio.to_thread(build_tree, root)
        ctx.publish(
            events.DirectoryTreeBuilt(str(root), tree.nodes, tree.dirs, tree.files, tree.truncated)
        )
        phrase = "comandos.arbol_recortado" if tree.truncated else "comandos.arbol"
        return ActionResult(
            "completado",
            Phrase(phrase, {
                "carpetas": count(tree.dirs, "carpeta", "carpetas"),
                "archivos": count(tree.files, "archivo", "archivos"),
            }),
            description=f"árbol de {root}",
        )  # fmt: skip

    # --- Binarios externos -------------------------------------------------------------------

    async def _run(self, command: CommandLine, ctx: ActionContext) -> ActionResult:
        inline = ctx.origin == "protocolo"  # en un protocolo, el binario se espera en línea
        if not inline and self._running:
            return ActionResult("error", Phrase("comandos.ocupado"))
        try:
            process = await self._launch(command.executable, command.args, ctx.workdir.path)
        except FileNotFoundError:
            return ActionResult(
                "error", Phrase("comandos.no_encontrado", {"nombre": command.name}),
                description=command.text,
            )  # fmt: skip
        except OSError:
            logger.exception("No se ha podido lanzar %s", command.text)
            return ActionResult(
                "error", Phrase("comandos.fallo", {"comando": command.text}),
                description=command.text,
            )  # fmt: skip
        if inline:
            return await self._supervise(process, command, ctx)
        self._running = True
        ctx.background(self._supervise(process, command, ctx, release=True))
        return ActionResult(
            "completado", Phrase("comandos.ejecutando", {"comando": command.text}),
            description=command.text, background=True,
        )  # fmt: skip

    async def _supervise(
        self, process: Any, command: CommandLine, ctx: ActionContext, *, release: bool = False
    ) -> ActionResult:
        """Sigue al proceso hasta que termina, publicando su salida por lotes."""
        limit = command.timeout_seconds or ctx.config.settings.commands.default_timeout_seconds
        pending: dict[str, list[str]] = {"out": [], "err": []}
        timed_out = False

        def flush() -> None:
            for stream, lines in pending.items():
                if lines:
                    ctx.publish(
                        events.CommandOutputAppended(
                            ctx.task_id or 0, command.text, tuple(lines), stream  # type: ignore[arg-type]
                        )
                    )
                    lines.clear()

        async def read(reader: Any, stream: str) -> None:
            if reader is None:
                return
            while line := await reader.readline():
                pending[stream].append(line.decode("utf-8", errors="replace").rstrip("\r\n"))

        async def batch() -> None:
            while True:
                await ctx.clock.sleep(OUTPUT_BATCH_SECONDS)
                flush()

        def expire() -> None:
            nonlocal timed_out
            timed_out = True
            self._kill_tree(process.pid)

        ctx.publish(events.CommandOutputAppended(ctx.task_id or 0, command.text, (), "out"))
        timer = ctx.clock.call_later(limit, expire)
        batcher = asyncio.ensure_future(batch())
        try:
            await asyncio.gather(read(process.stdout, "out"), read(process.stderr, "err"))
            code = await process.wait()
        except asyncio.CancelledError:
            self._kill_tree(process.pid)  # «cancelar» o cierre de sesión (RN-46, RN-52)
            raise
        finally:
            timer.cancel()
            batcher.cancel()
            flush()
            if release:
                self._running = False
        if timed_out:
            return ActionResult("error", Phrase("comandos.tiempo"), description=command.text)
        phrase = "comandos.ok" if code == 0 else "comandos.fallo"
        return ActionResult(
            "completado" if code == 0 else "error",
            Phrase(phrase, {"comando": command.text}),
            description=command.text,
        )

    async def _open_terminal(self, ctx: ActionContext) -> ActionResult:
        try:
            await ctx.platform.open_terminal(ctx.workdir.path)
        except OSError:
            logger.exception("No se ha podido abrir la terminal")
            return ActionResult("error", Phrase("general.error"))
        return ActionResult("completado", Phrase("comandos.consola"))
