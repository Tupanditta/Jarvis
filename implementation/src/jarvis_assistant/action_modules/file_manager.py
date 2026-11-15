"""Módulo Búsqueda de archivos y carpetas (busqueda.md). Creación llega con el diálogo.

Con herramienta indexada (*Everything*) busca en todo el disco. Sin ella, la búsqueda se
limita a la carpeta del usuario y a los lugares con nombre: nunca se recorre el disco
completo (RES-31). La búsqueda no modifica ni borra nada.
"""
import asyncio
import logging
import os
import stat
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    ActionContext,
    ActionResult,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import SearchResult
from jarvis_assistant.core.workdir import folder_name
from jarvis_assistant.intent_router.normalizer import normalize
from jarvis_assistant.os_adapters.base import SearchKind

logger = logging.getLogger(__name__)

PANEL = "busqueda"
SEARCH_LIMIT = 50
FALLBACK_MAX_DEPTH = 6
SKIPPED_FOLDERS = frozenset({"node_modules", ".git", ".venv", "__pycache__"})
_HIDDEN = stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM

_KINDS = {"archivos": SearchKind.FILE, "carpetas": SearchKind.FOLDER, "ambos": SearchKind.ANY}


@dataclass(frozen=True)
class Found:
    path: Path
    is_dir: bool


def _is_hidden(entry: os.DirEntry) -> bool:
    if entry.name.startswith("."):
        return True
    try:
        return bool(getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & _HIDDEN)
    except OSError:
        return True


def limited_search(
    roots: Sequence[Path],
    query: str,
    kind: SearchKind,
    *,
    limit: int = SEARCH_LIMIT,
    timeout: float = 5.0,
    monotonic: Callable[[], float],
    max_depth: int = FALLBACK_MAX_DEPTH,
) -> list[Found]:
    """Búsqueda sin índice: recorre `roots` hasta `max_depth` niveles, omitiendo carpetas
    ocultas, de sistema y de dependencias. Se corta a los `timeout` segundos o a los `limit`
    resultados. Coincide un nombre que, normalizado, contiene la consulta normalizada."""
    wanted = normalize(query)
    found: list[Found] = []
    if not wanted:
        return found
    deadline = monotonic() + timeout
    seen: set[str] = set()
    queue: deque[tuple[Path, int]] = deque((Path(root), 1) for root in roots)
    while queue:
        folder, depth = queue.popleft()
        key = os.path.normcase(os.path.abspath(folder))
        if key in seen:
            continue
        seen.add(key)
        if monotonic() > deadline:
            break
        try:
            with os.scandir(folder) as entries:
                listed = sorted(entries, key=lambda entry: entry.name.casefold())
        except OSError:
            continue
        for entry in listed:
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir and (entry.name in SKIPPED_FOLDERS or _is_hidden(entry)):
                continue
            wanted_kind = kind is SearchKind.ANY or is_dir == (kind is SearchKind.FOLDER)
            if wanted_kind and wanted in normalize(entry.name):
                found.append(Found(Path(entry.path), is_dir))
                if len(found) >= limit:
                    return found
            if is_dir and depth < max_depth:
                queue.append((Path(entry.path), depth + 1))
    return found


def rank(found: Sequence[Found], query: str) -> list[Found]:
    """Orden de presentación: nombre igual a la consulta; después, el que empieza por ella;
    después, el resto. A igualdad, la ruta más corta."""
    wanted = normalize(query)

    def key(item: Found) -> tuple[int, int, str]:
        name = normalize(item.path.name)
        stem = normalize(item.path.stem)
        if wanted in (name, stem):
            order = 0
        elif name.startswith(wanted):
            order = 1
        else:
            order = 2
        return (order, len(str(item.path)), str(item.path).casefold())

    return sorted(found, key=key)


class FileSearch:
    name = "busqueda"
    title = "Búsqueda"

    def __init__(self) -> None:
        self._results: list[Found] = []  # los que muestra el panel, en su orden (RN-50)
        self._install_hint_given = False

    def intents(self) -> Sequence[IntentSpec]:
        query = (Slot("consulta", SlotType.TEXT),)
        index = (Slot("n", SlotType.INTEGER),)
        return (
            IntentSpec(
                "buscar", ("busca {consulta}", "encuentra {consulta}"), query,
                "Buscar archivos y carpetas", "Busca presupuesto", PANEL,
                fixed={"tipo": "ambos"},
            ),
            IntentSpec(
                "buscar", ("busca el archivo {consulta}", "busca archivos {consulta}",
                           "encuentra el archivo {consulta}"),
                query, panel=PANEL, fixed={"tipo": "archivos"},
            ),
            IntentSpec(
                "buscar", ("busca la carpeta {consulta}", "busca carpetas {consulta}",
                           "encuentra la carpeta {consulta}"),
                query, panel=PANEL, fixed={"tipo": "carpetas"},
            ),
            IntentSpec(
                "abrir_resultado", ("abre el resultado {n}", "abre el resultado número {n}"),
                index, "Abrir un resultado de la búsqueda", "Abre el resultado dos", PANEL,
                in_protocols=False,
            ),
            IntentSpec(
                "abrir_ubicacion", ("abre la carpeta del resultado {n}",
                                    "dónde está el resultado {n}"),
                index, "Abrir la carpeta de un resultado", "Abre la carpeta del resultado dos",
                PANEL, in_protocols=False,
            ),
        )  # fmt: skip

    async def on_session_closed(self, ctx: ActionContext) -> None:
        self._results = []
        self._install_hint_given = False

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        match action:
            case "buscar":
                return await self._search(
                    str(params["consulta"]), str(params.get("tipo", "ambos")), ctx
                )
            case "abrir_resultado":
                return await self._open(int(params["n"]), ctx, location=False)  # type: ignore[call-overload]
            case "abrir_ubicacion":
                return await self._open(int(params["n"]), ctx, location=True)  # type: ignore[call-overload]
        raise ValueError(f"Acción desconocida: {action}")

    async def _search(self, query: str, kind_name: str, ctx: ActionContext) -> ActionResult:
        kind = _KINDS.get(kind_name, SearchKind.ANY)
        settings = ctx.config.settings.search
        outcome = await ctx.platform.indexed_search(query, kind, SEARCH_LIMIT)
        limited = outcome is None
        if outcome is None:
            roots = [ctx.workdir.home, *ctx.places.values()]
            found = await asyncio.to_thread(
                limited_search, roots, query, kind,
                timeout=settings.fallback_timeout_seconds, monotonic=ctx.clock.monotonic,
            )  # fmt: skip
            total = len(found)
        else:
            found = [Found(Path(path), Path(path).is_dir()) for path in outcome.paths]
            total = max(outcome.total, len(found))
        shown = rank(found, query)[: settings.max_results]
        self._results = shown
        ctx.publish(
            events.SearchResultsReady(
                query,
                kind_name,
                tuple(
                    SearchResult(
                        index, item.path.name, item.is_dir, str(item.path.parent), str(item.path)
                    )
                    for index, item in enumerate(shown, start=1)
                ),
                total,
                limited,
            )
        )
        speech = self._summary(query, shown, total)
        if limited:
            await ctx.say(speech)
            speech = Phrase("busqueda.limitada")
            if not self._install_hint_given:  # la primera vez en cada sesión
                self._install_hint_given = True
                await ctx.say(speech)
                speech = Phrase("busqueda.instalar")
        return ActionResult("completado", speech, description=f"buscar {query}")

    @staticmethod
    def _summary(query: str, shown: Sequence[Found], total: int) -> Phrase:
        if not shown:
            return Phrase("busqueda.ninguno", {"consulta": query})
        first = {"nombre": shown[0].path.name, "carpeta": folder_name(shown[0].path.parent)}
        if total == 1:
            return Phrase("busqueda.uno", first)
        return Phrase("busqueda.varios", {"n": total, **first})

    async def _open(self, n: int, ctx: ActionContext, *, location: bool) -> ActionResult:
        if not 1 <= n <= len(self._results):  # también sin búsqueda previa (RN-50)
            return ActionResult("error", Phrase("general.indice_invalido", {"n": n}))
        item = self._results[n - 1]
        target = item.path.parent if location else item.path
        name = folder_name(target)
        description = f"abrir {name}"
        if not target.exists():
            return ActionResult("error", Phrase("busqueda.no_existe"), description=description)
        try:
            if target.is_dir():
                await ctx.platform.open_folder(target)
            else:
                await ctx.platform.open_with_default(target)
        except Exception:
            logger.exception("No se ha podido abrir %s", target)
            return ActionResult(
                "error", Phrase("apertura.fallo", {"nombre": name}), description=description
            )
        return ActionResult(
            "completado", Phrase("apertura.abriendo", {"nombre": name}), description=description
        )
