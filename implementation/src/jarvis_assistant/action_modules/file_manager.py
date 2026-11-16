"""Módulos Búsqueda (busqueda.md) y Creación (creacion-archivos.md) de archivos y carpetas.

Con herramienta indexada (*Everything*) busca en todo el disco. Sin ella, la búsqueda se
limita a la carpeta del usuario y a los lugares con nombre: nunca se recorre el disco
completo (RES-31). La búsqueda no modifica ni borra nada.

La creación nunca sobrescribe, mueve ni borra nada que ya exista (RN-18): la colisión se
comprueba con `exists()` y la creación misma falla si el destino aparece entretanto.
"""
import asyncio
import logging
import os
import stat
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath

from jarvis_assistant.config import StructureDef
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    WORKDIR,
    ActionContext,
    ActionResult,
    ExpectedType,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import SearchResult
from jarvis_assistant.core.workdir import folder_name, invalid_folder
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
        first = {
            "consulta": query,
            "nombre": shown[0].path.name,
            "carpeta": folder_name(shown[0].path.parent),
        }
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


# --- Creación --------------------------------------------------------------------------------

STRUCTURES = "estructuras"
_LEVEL_SEPARATOR = "barra"


@dataclass(frozen=True)
class _Kind:
    """Lo que se crea: su acción y cómo se nombra en la respuesta."""

    action: str
    spoken: str  # «He creado {tipo} {nombre}…»


_FILE = _Kind("crear_archivo", "el archivo")
_FOLDER = _Kind("crear_carpeta", "la carpeta")
_TREE = _Kind("crear_arbol", "las carpetas")
_STRUCTURE = _Kind("crear_estructura", "la estructura")


class FileCreation:
    """Crear un archivo, una carpeta, un árbol o una estructura (RF-29 a RF-31, RF-97). Si el
    destino ya existe, pregunta otro nombre (RN-19)."""

    name = "creacion"
    title = "Creación"

    def __init__(self) -> None:
        self._structures: tuple[StructureDef, ...] = ()

    def intents(self) -> Sequence[IntentSpec]:
        place = Slot("ruta", SlotType.DIR_PATH, optional=True)
        name = Slot("nombre", SlotType.NEW_NAME)
        # Sin ruta, la ubicación es el directorio de trabajo (RN-54).
        here = frozenset({WORKDIR})
        return (
            IntentSpec(
                "crear_archivo", ("crea el archivo {nombre}", "crea un archivo llamado {nombre}",
                                  "crea el archivo {nombre} en {ruta}",
                                  "crea un archivo llamado {nombre} en {ruta}"),
                (name, place), "Crear un archivo vacío",
                "Crea el archivo notas punto txt en documentos", reads=here,
            ),
            IntentSpec(
                "crear_carpeta", ("crea la carpeta {nombre}", "crea una carpeta llamada {nombre}",
                                  "crea la carpeta {nombre} en {ruta}",
                                  "crea una carpeta llamada {nombre} en {ruta}"),
                (name, place), "Crear una carpeta", "Crea la carpeta apuntes", reads=here,
            ),
            IntentSpec(
                "crear_arbol", ("crea las carpetas {arbol}", "crea las carpetas {arbol} en {ruta}",
                                "crea el árbol {arbol}"),
                (Slot("arbol", SlotType.NEW_PATH), place), "Crear carpetas anidadas",
                "Crea las carpetas backend barra src barra modelos", reads=here,
            ),
            IntentSpec(
                "crear_estructura", ("crea la estructura {estructura} llamada {nombre}",
                                     "crea la estructura {estructura} llamada {nombre} en {ruta}"),
                (Slot("estructura", SlotType.CATALOG, STRUCTURES), name, place),
                "Crear una estructura de carpetas",
                "Crea la estructura proyecto python llamada analizador", reads=here,
            ),
        )  # fmt: skip

    def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]:
        return {STRUCTURES: (lambda: [structure.name for structure in self._structures],)}

    async def on_session_opened(self, ctx: ActionContext) -> None:
        self._structures = ctx.config.structures  # la configuración vigente (RF-96)

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        self._structures = ctx.config.structures
        place = params.get("ruta")
        location = Path(place) if isinstance(place, str | Path) else ctx.workdir.path
        if not location.is_absolute():
            location = ctx.workdir.path / location  # RN-42
        match action:
            case "crear_archivo":
                return await self._create(_FILE, PurePath(str(params["nombre"])), location, ctx)
            case "crear_carpeta":
                levels = _levels(str(params["nombre"]))
                kind = _TREE if len(levels.parts) > 1 else _FOLDER  # «a barra b» es un árbol
                return await self._create(kind, levels, location, ctx)
            case "crear_arbol":
                return await self._create(_TREE, PurePath(str(params["arbol"])), location, ctx)
            case "crear_estructura":
                wanted = str(params["estructura"])
                structure = next((item for item in self._structures if item.name == wanted), None)
                if structure is None:
                    return ActionResult(
                        "error", Phrase("entidad.no_encontrado", {"nombre": wanted})
                    )
                return await self._create(
                    _STRUCTURE, PurePath(str(params["nombre"])), location, ctx, structure
                )
        raise ValueError(f"Acción desconocida: {action}")

    async def _create(
        self,
        kind: _Kind,
        relative: PurePath,
        location: Path,
        ctx: ActionContext,
        structure: StructureDef | None = None,
    ) -> ActionResult:
        """Comprueba la colisión y crea. Con colisión pregunta otro nombre, que sustituye a la
        carpeta más profunda (árbol) o a la raíz (estructura); tras `max_collisions`
        colisiones seguidas, cancela."""
        description = f"crear {relative.as_posix()}"
        problem = invalid_folder(location)  # RN-41
        if problem is not None:
            return ActionResult("error", problem, description)
        limit = ctx.config.settings.dialogue.max_collisions
        collisions = 0
        while True:
            target = location / relative
            description = f"crear {relative.as_posix()}"
            if not target.exists():  # nunca con expresiones regulares (RES-30)
                try:
                    _make(kind, target, structure)
                except FileExistsError:
                    pass  # ha aparecido entretanto: es una colisión más
                except OSError:
                    logger.exception("No se ha podido crear %s", target)
                    return ActionResult(
                        "error", Phrase("creacion.fallo", {"nombre": relative.as_posix()}),
                        description,
                    )  # fmt: skip
                else:
                    logger.info("Creado %s", target)
                    return ActionResult(
                        "completado",
                        Phrase("creacion.creado", {
                            "tipo": kind.spoken, "nombre": relative.as_posix(),
                            "carpeta": folder_name(location),
                        }),
                        description,
                    )  # fmt: skip
            collisions += 1
            if collisions >= limit:
                return ActionResult.cancelled(Phrase("general.operacion_cancelada"), description)
            answer = await ctx.ask(
                Phrase("creacion.colision", {"nombre": relative.name}),
                ExpectedType.NEW_FILENAME,
                metadata={"destino": target, "ubicacion": location},
                subject={"nombre": relative.name, "carpeta": folder_name(target.parent)},
            )
            if answer.cancelled:
                return ActionResult.cancelled(description=description)  # ya se ha dicho
            relative = relative.with_name(str(answer.value))


def _levels(name: str) -> PurePath:
    """El nombre de `crear_carpeta` con «barra» se trata como un árbol."""
    levels: list[list[str]] = [[]]
    for word in name.split(" "):
        if normalize(word) == _LEVEL_SEPARATOR:
            levels.append([])
        else:
            levels[-1].append(word)
    parts = [" ".join(level).strip() for level in levels]
    if len(parts) > 1 and all(parts):
        return PurePath(*parts)
    return PurePath(name)


def _make(kind: _Kind, target: Path, structure: StructureDef | None) -> None:
    """Crea `target`; falla con `FileExistsError` si ya existe, sin tocarlo."""
    if kind is _FILE:
        with open(target, "x"):  # «x»: nunca abre un archivo que ya exista
            pass
    elif kind is _TREE:
        target.mkdir(parents=True, exist_ok=False)  # las intermedias existentes se reutilizan
    else:
        target.mkdir(exist_ok=False)
        for folder in structure.folders if structure is not None else ():
            sub = PurePath(folder)
            if sub.is_absolute() or ".." in sub.parts:
                logger.warning("Subcarpeta fuera de la estructura ignorada: %s", folder)
                continue
            # La raíz es nueva: dentro no existe nada que se pueda modificar.
            (target / sub).mkdir(parents=True, exist_ok=True)
