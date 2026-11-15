"""Módulo Apertura: aplicaciones, páginas del catálogo y carpetas (apertura-apps.md).

El asistente no trae nada al frente por su cuenta ni recupera el foco tras abrir (RES-32):
solo lo hace cuando el usuario lo pide, con una orden o con el botón de la tarjeta.
"""
import asyncio
import itertools
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from jarvis_assistant.config import AppEntry, Catalog, PageEntry
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    ActionContext,
    ActionResult,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import OpenedItem, OpenedKind
from jarvis_assistant.core.workdir import folder_name, invalid_folder
from jarvis_assistant.os_adapters.base import AppTarget, DiscoveredApp, EdgeNotFound, WindowRef

logger = logging.getLogger(__name__)

PANEL = "aperturas"
MAX_ITEMS = 12
WINDOW_TIMEOUT_SECONDS = 10.0
EDGE_TITLE = "Edge"

TARGETS = "apertura.objetivos"
OPENED = "apertura.abiertos"


@dataclass
class _Opened:
    item: OpenedItem
    window: WindowRef | None = None


class AppLauncher:
    name = "apertura"
    title = "Aperturas"

    def __init__(self) -> None:
        self._catalog = Catalog()
        self._discovered: tuple[DiscoveredApp, ...] = ()
        self._items: list[_Opened] = []
        self._ids = itertools.count(1)
        self._lookups: set[asyncio.Task] = set()
        self._discovery: asyncio.Task | None = None

    def intents(self) -> Sequence[IntentSpec]:
        return (
            IntentSpec(
                "abrir", ("abre {objetivo}", "abrir {objetivo}", "lanza {objetivo}",
                          "inicia {objetivo}"),
                (Slot("objetivo", SlotType.CATALOG, catalog=TARGETS),),
                "Abrir una aplicación o una página", "Abre GitHub", PANEL,
            ),
            IntentSpec(
                "abrir_carpeta", ("abre la carpeta {ruta}", "muestra la carpeta {ruta}",
                                  "abre esta carpeta", "abre la carpeta actual"),
                (Slot("ruta", SlotType.DIR_PATH, optional=True),),
                "Abrir una carpeta en el gestor de archivos", "Abre la carpeta descargas", PANEL,
            ),
            IntentSpec(
                "traer_al_frente", ("trae al frente {objetivo}", "pon delante {objetivo}",
                                    "vuelve a {objetivo}"),
                (Slot("objetivo", SlotType.CATALOG, catalog=OPENED),),
                "Traer al frente algo abierto por el asistente", "Trae al frente GitHub", PANEL,
            ),
        )  # fmt: skip

    def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]:
        # Orden de RN-49: aplicaciones del catálogo, páginas y aplicaciones descubiertas.
        return {
            TARGETS: (
                lambda: _spellings(self._catalog.apps),
                lambda: _spellings(self._catalog.pages),
                lambda: [app.name for app in self._discovered_apps()],
            ),
            OPENED: (lambda: [opened.item.title for opened in self._items],),
        }

    def user_actions(self) -> Mapping[type, Callable[[Any], tuple[str, Mapping[str, object]]]]:
        return {
            events.FocusItemRequested: lambda event: ("traer_al_frente", {"id": event.item_id})
        }

    # --- Ciclo de la sesión ------------------------------------------------------------------

    async def on_session_opened(self, ctx: ActionContext) -> None:
        self._catalog = ctx.config.catalog
        self._items.clear()
        self._publish(ctx)
        if self._catalog.discover_installed_apps:
            self._discovery = asyncio.ensure_future(self.discover(ctx.platform))

    async def on_session_closed(self, ctx: ActionContext) -> None:
        """La lista se vacía; las aplicaciones abiertas no se cierran."""
        for task in (*self._lookups, self._discovery):
            if task is not None:
                task.cancel()
        self._lookups.clear()
        self._items.clear()
        self._publish(ctx)

    async def discover(self, platform: Any) -> None:
        """Descubre las aplicaciones instaladas, en un hilo: puede tardar."""
        try:
            self._discovered = tuple(await asyncio.to_thread(platform.discover_apps))
        except Exception:
            logger.exception("No se han podido descubrir las aplicaciones instaladas")

    def _discovered_apps(self) -> tuple[DiscoveredApp, ...]:
        return self._discovered if self._catalog.discover_installed_apps else ()

    # --- Acciones ----------------------------------------------------------------------------

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        self._catalog = ctx.config.catalog
        match action:
            case "abrir":
                return await self._open(str(params["objetivo"]), ctx)
            case "abrir_carpeta":
                return await self._open_folder(params.get("ruta"), ctx)  # type: ignore[arg-type]
            case "traer_al_frente":
                return self._focus(params, ctx)
        raise ValueError(f"Acción desconocida: {action}")

    async def _open(self, wanted: str, ctx: ActionContext) -> ActionResult:
        target = self._find(wanted)
        if target is None:
            return ActionResult("error", Phrase("entidad.no_encontrado", {"nombre": wanted}))
        name = target.name
        kind: OpenedKind = "pagina" if isinstance(target, PageEntry) else "aplicacion"
        try:
            if isinstance(target, PageEntry):
                handle = await ctx.platform.open_url_in_edge(target.url)
                handle = replace(handle, title_hint=EDGE_TITLE)  # la ventana es la de Edge
            else:
                args = target.args if isinstance(target, AppEntry) else ()
                handle = await ctx.platform.launch_app(AppTarget(name, target.path, tuple(args)))
        except EdgeNotFound:
            self._add(name, kind, "error", ctx)
            return ActionResult("error", Phrase("apertura.sin_edge"), description=f"abrir {name}")
        except Exception:
            logger.exception("No se ha podido abrir %s", name)
            self._add(name, kind, "error", ctx)
            return ActionResult(
                "error", Phrase("apertura.fallo", {"nombre": name}), description=f"abrir {name}"
            )
        self._locate(self._add(name, kind, "completado", ctx), handle, ctx)
        return ActionResult(
            "completado", Phrase("apertura.abriendo", {"nombre": name}),
            description=f"abrir {name}",
        )  # fmt: skip

    async def _open_folder(self, target: Path | None, ctx: ActionContext) -> ActionResult:
        path = ctx.workdir.path if target is None else ctx.workdir.resolve(target)
        invalid = invalid_folder(path)
        if invalid is not None:
            return ActionResult("error", invalid)
        name = folder_name(path)
        try:
            handle = await ctx.platform.open_folder(path)
        except Exception:
            logger.exception("No se ha podido abrir el gestor de archivos en %s", path)
            return ActionResult(
                "error", Phrase("ruta.gestor_fallo"), description=f"abrir carpeta {name}"
            )
        self._locate(self._add(name, "carpeta", "completado", ctx), handle, ctx)
        return ActionResult(
            "completado", Phrase("apertura.abriendo", {"nombre": name}),
            description=f"abrir carpeta {name}",
        )  # fmt: skip

    def _focus(self, params: Mapping[str, object], ctx: ActionContext) -> ActionResult:
        if not ctx.platform.can_focus_windows:
            return ActionResult("error", Phrase("general.no_disponible"))
        opened = self._opened(params)
        if opened is None:
            return ActionResult("error", Phrase("apertura.ventana_cerrada"))
        description = f"traer al frente {opened.item.title}"
        if opened.window is None or not ctx.platform.window_exists(opened.window):
            opened.item = replace(opened.item, can_focus=False)
            self._publish(ctx)
            return ActionResult(
                "error", Phrase("apertura.ventana_cerrada"), description=description
            )
        ctx.platform.focus_window(opened.window)
        return ActionResult("completado", description=description)

    # --- Elementos abiertos ------------------------------------------------------------------

    def _find(self, wanted: str) -> AppEntry | PageEntry | DiscoveredApp | None:
        key = wanted.casefold()
        for entry in (*self._catalog.apps, *self._catalog.pages):
            if key in (spelling.casefold() for spelling in (entry.name, *entry.aliases)):
                return entry
        return next((app for app in self._discovered_apps() if app.name.casefold() == key), None)

    def _opened(self, params: Mapping[str, object]) -> _Opened | None:
        if "id" in params:
            return next((o for o in self._items if o.item.id == params["id"]), None)
        title = str(params.get("objetivo", "")).casefold()
        # Con el mismo nombre abierto varias veces, vale el más reciente.
        return next((o for o in reversed(self._items) if o.item.title.casefold() == title), None)

    def _add(self, title: str, kind: OpenedKind, status: str, ctx: ActionContext) -> _Opened:
        opened = _Opened(OpenedItem(next(self._ids), title, kind, status, can_focus=False))
        self._items.append(opened)
        del self._items[:-MAX_ITEMS]  # se descarta el más antiguo
        self._publish(ctx)
        return opened

    def _locate(self, opened: _Opened, handle: Any, ctx: ActionContext) -> None:
        """Busca en segundo plano la ventana de lo lanzado; si aparece, activa su botón."""

        async def locate() -> None:
            window = await ctx.platform.wait_for_window(handle, WINDOW_TIMEOUT_SECONDS)
            if window is not None and opened in self._items:
                opened.window = window
                opened.item = replace(opened.item, can_focus=True)
                self._publish(ctx)

        task = asyncio.ensure_future(locate())
        self._lookups.add(task)
        task.add_done_callback(self._lookup_done)

    def _lookup_done(self, task: asyncio.Task) -> None:
        self._lookups.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("Error al localizar una ventana", exc_info=task.exception())

    def _publish(self, ctx: ActionContext) -> None:
        ctx.publish(
            events.OpenedItemsChanged(
                tuple(opened.item for opened in self._items), ctx.platform.can_focus_windows
            )
        )


def _spellings(entries: Sequence[AppEntry | PageEntry]) -> list[str]:
    return [spelling for entry in entries for spelling in (entry.name, *entry.aliases)]
