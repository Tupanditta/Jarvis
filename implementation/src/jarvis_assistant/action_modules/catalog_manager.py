"""Módulo Catálogo: añadir y eliminar aplicaciones, páginas web y comandos de terminal.

Las aplicaciones y las páginas son las de `catalog.toml`, las que se abren con «abre
{nombre}»; los comandos, los binarios permitidos de `commands.toml` (RN-45). Las aplicaciones
descubiertas en el menú Inicio no se ven ni se editan aquí.

Se añade desde su ventana, que envía el formulario completo («añade al catálogo» solo la
abre). Eliminar pide confirmación, tanto por voz como desde la ventana. Cada cambio se escribe
en su archivo y se aplica en la sesión en curso (`ctx.save_launchers`): lo añadido se puede
abrir o ejecutar enseguida.
"""
import logging
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace

from jarvis_assistant.config import AppEntry, Binary, Catalog, PageEntry
from jarvis_assistant.config.catalog import URL_SCHEMES
from jarvis_assistant.core.action_api import (
    ActionContext,
    ActionResult,
    ExpectedType,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import CatalogItem, CatalogKind
from jarvis_assistant.core.events import CatalogShown

logger = logging.getLogger(__name__)

PANEL = "catalogo"
ENTRIES = "catalogo.entradas"

APP: CatalogKind = "aplicacion"
PAGE: CatalogKind = "pagina"
COMMAND: CatalogKind = "comando"
KINDS: tuple[CatalogKind, ...] = (APP, PAGE, COMMAND)
_LABELS = {APP: "Aplicación", PAGE: "Página", COMMAND: "Comando"}

Entry = AppEntry | PageEntry | Binary


def _comparable(text: str) -> str:
    """Forma de comparar nombres: sin mayúsculas, sin tildes y sin espacios sobrantes."""
    plain = unicodedata.normalize("NFKD", " ".join(text.split()))
    return "".join(char for char in plain if not unicodedata.combining(char)).casefold()


def _lines(value: object) -> tuple[str, ...]:
    """Una entrada por línea o separada por comas, sin vacías. Admite texto o una lista."""
    if isinstance(value, str):
        raw = value.splitlines()
    elif isinstance(value, Sequence):
        raw = [str(item) for item in value]
    else:
        raw = []
    parts = [part.strip() for line in raw for part in line.split(",")]
    return tuple(part for part in parts if part)


def _target(entry: Entry) -> str:
    if isinstance(entry, AppEntry):
        return entry.path
    if isinstance(entry, PageEntry):
        return entry.url
    return entry.executable


def _item(kind: CatalogKind, entry: Entry) -> CatalogItem:
    return CatalogItem(
        f"{kind}:{entry.name}", kind, entry.name, _target(entry), entry.aliases,
        entry.args if isinstance(entry, AppEntry) else (),
    )  # fmt: skip


class CatalogManager:
    name = "catalogo"
    title = "Catálogo"

    def __init__(self) -> None:
        self._catalog = Catalog()
        self._binaries: tuple[Binary, ...] = ()

    def intents(self) -> Sequence[IntentSpec]:
        changes = frozenset({ENTRIES})
        return (
            IntentSpec(
                "ver",
                ("muestra el catálogo", "ver el catálogo", "ver catálogo",
                 "enseña el catálogo"),
                (), "Ver las aplicaciones, páginas y comandos del catálogo",
                "Muestra el catálogo", PANEL, in_protocols=False, record=False,
            ),
            IntentSpec(
                "añadir",
                ("añade al catálogo", "añadir al catálogo", "nueva entrada del catálogo"),
                (), "Añadir una aplicación, una página o un comando (en su ventana)",
                "Añade al catálogo", PANEL, in_protocols=False, writes=changes,
            ),
            IntentSpec(
                "eliminar",
                ("elimina {entrada} del catálogo", "quita {entrada} del catálogo",
                 "borra {entrada} del catálogo"),
                (Slot("entrada", SlotType.CATALOG, catalog=ENTRIES),),
                "Eliminar una aplicación, una página o un comando del catálogo",
                "Quita GitHub del catálogo", PANEL, in_protocols=False, writes=changes,
            ),
        )  # fmt: skip

    def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]:
        return {
            ENTRIES: (
                lambda: [s for e in self._catalog.apps for s in (e.name, *e.aliases)],
                lambda: [s for e in self._catalog.pages for s in (e.name, *e.aliases)],
                lambda: [s for e in self._binaries for s in (e.name, *e.aliases)],
            )
        }

    # --- Ciclo de la sesión ------------------------------------------------------------------

    async def on_session_opened(self, ctx: ActionContext) -> None:
        self._refresh(ctx)
        self._publish(ctx)

    # --- Acciones ----------------------------------------------------------------------------

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        self._refresh(ctx)
        match action:
            case "ver":
                self._publish(ctx)
                return ActionResult("completado", Phrase("catalogo.mostrado"))
            case "añadir":
                return await self._add(params, ctx)
            case "eliminar":
                return await self._remove(params, ctx)
        raise ValueError(f"Acción desconocida: {action}")

    async def _add(self, params: Mapping[str, object], ctx: ActionContext) -> ActionResult:
        kind = str(params.get("tipo") or "")
        if kind not in KINDS:  # por voz: los datos se escriben en la ventana
            self._publish(ctx)
            return ActionResult("completado", Phrase("catalogo.usar_ventana"))
        name = " ".join(str(params.get("nombre") or "").split())
        target = str(params.get("destino") or "").strip()
        aliases = _lines(params.get("alias"))
        entry: Entry
        if kind == APP:
            entry = AppEntry(name, target, aliases, _lines(params.get("argumentos")))
        elif kind == PAGE:
            entry = PageEntry(name, target, aliases)
        else:
            entry = Binary(name, target, aliases)
        problem = self._problem(kind, entry)
        if problem:
            self._publish(ctx, problem)
            return ActionResult("error", Phrase("catalogo.no_valido"), detail=problem)
        if isinstance(entry, AppEntry):
            catalog = replace(self._catalog, apps=(*self._catalog.apps, entry))
            problem = await self._save(ctx, catalog=catalog)
        elif isinstance(entry, PageEntry):
            catalog = replace(self._catalog, pages=(*self._catalog.pages, entry))
            problem = await self._save(ctx, catalog=catalog)
        else:
            problem = await self._save(ctx, binaries=(*self._binaries, entry))
        if problem:
            return ActionResult("error", Phrase("catalogo.no_guardado"), detail=problem)
        logger.info("Añadido al catálogo: %s %s", kind, name)
        return ActionResult(
            "completado", Phrase("catalogo.anadido", {"nombre": name}),
            description=f"{_LABELS[kind]} {name} añadida al catálogo"
            if kind != COMMAND else f"Comando {name} añadido al catálogo",
        )  # fmt: skip

    async def _remove(self, params: Mapping[str, object], ctx: ActionContext) -> ActionResult:
        found = self._find(params.get("entrada"))
        if found is None:
            self._publish(ctx, "Esa entrada ya no está en el catálogo.")
            return ActionResult("error", Phrase("catalogo.no_encontrado"))
        kind, entry = found
        answer = await ctx.ask(
            Phrase("catalogo.confirmar", {"nombre": entry.name}), ExpectedType.BOOLEAN,
            subject={"entrada": entry.name},
        )  # fmt: skip
        if answer.cancelled or answer.value is not True:
            return ActionResult.cancelled(Phrase("general.operacion_cancelada"))
        if kind == COMMAND:
            binaries = tuple(b for b in self._binaries if b is not entry)
            problem = await self._save(ctx, binaries=binaries)
        else:
            catalog = replace(
                self._catalog,
                apps=tuple(a for a in self._catalog.apps if a is not entry),
                pages=tuple(p for p in self._catalog.pages if p is not entry),
            )
            problem = await self._save(ctx, catalog=catalog)
        if problem:
            return ActionResult("error", Phrase("catalogo.no_guardado"), detail=problem)
        logger.info("Eliminado del catálogo: %s %s", kind, entry.name)
        return ActionResult(
            "completado", Phrase("catalogo.eliminado", {"nombre": entry.name}),
            description=f"{entry.name} eliminado del catálogo",
        )  # fmt: skip

    # --- Interno -----------------------------------------------------------------------------

    def _refresh(self, ctx: ActionContext) -> None:
        self._catalog = ctx.config.catalog
        self._binaries = tuple(ctx.config.binaries)

    async def _save(
        self,
        ctx: ActionContext,
        *,
        catalog: Catalog | None = None,
        binaries: tuple[Binary, ...] | None = None,
    ) -> str:
        """Escribe y aplica el cambio; la ventana recibe la lista nueva o el motivo."""
        problem = await ctx.save_launchers(catalog=catalog, binaries=binaries)
        if problem:
            problem = f"No se ha podido guardar: {problem}"
        else:
            if catalog is not None:
                self._catalog = catalog
            if binaries is not None:
                self._binaries = binaries
        self._publish(ctx, problem)
        return problem

    def _entries(self) -> list[tuple[CatalogKind, Entry]]:
        return [
            *((APP, entry) for entry in self._catalog.apps),
            *((PAGE, entry) for entry in self._catalog.pages),
            *((COMMAND, entry) for entry in self._binaries),
        ]

    def _find(self, wanted: object) -> tuple[CatalogKind, Entry] | None:
        """Por id («{tipo}:{nombre}», desde la ventana) o por uno de sus nombres (por voz).
        Con el mismo nombre en varios tipos, gana la aplicación, luego la página."""
        text = str(wanted or "").strip()
        kind, _, name = text.partition(":")
        if kind in KINDS:
            return next(
                ((k, e) for k, e in self._entries() if k == kind and e.name == name), None
            )
        key = _comparable(text)
        return next(
            ((k, e) for k, e in self._entries()
             if key in (_comparable(s) for s in (e.name, *e.aliases))),
            None,
        )  # fmt: skip

    def _problem(self, kind: str, entry: Entry) -> str:
        """Por qué no se puede añadir; vacío si se puede."""
        if not entry.name:
            return "Escriba un nombre."
        if isinstance(entry, AppEntry) and not entry.path:
            return "Escriba la ruta del programa o su nombre en el PATH."
        if isinstance(entry, PageEntry) and not entry.url.startswith(URL_SCHEMES):
            return "La dirección debe empezar por http:// o https://."
        if isinstance(entry, Binary) and not entry.executable:
            return "Escriba el ejecutable: su nombre en el PATH o su ruta."
        # Las aplicaciones y las páginas comparten nombres («abre {nombre}»); los comandos
        # tienen los suyos.
        others = [
            other for other_kind, other in self._entries()
            if (other_kind == COMMAND) == (kind == COMMAND)
        ]  # fmt: skip
        taken = {_comparable(s) for other in others for s in (other.name, *other.aliases)}
        what = "otro comando" if kind == COMMAND else "otra aplicación o página"
        for spoken in (entry.name, *entry.aliases):
            if _comparable(spoken) in taken:
                return f"«{spoken}» ya es el nombre de {what}."
        return ""

    def _publish(self, ctx: ActionContext, problem: str = "") -> None:
        items = tuple(_item(kind, entry) for kind, entry in self._entries())
        ctx.publish(CatalogShown(items, problem))
