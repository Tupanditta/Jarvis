"""Apartado Aplicaciones: añadir, editar y eliminar a mano aplicaciones y páginas web.

Solo las entradas de `catalog.toml`; las aplicaciones descubiertas en el menú Inicio no se
ven ni se editan aquí. Al añadir se elige primero si es una aplicación o una página.
"""
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from jarvis_assistant.config import AppEntry, Config, PageEntry
from jarvis_assistant.config.catalog import URL_SCHEMES, dump_catalog
from jarvis_assistant.configurator.sections.base import Section, comparable, split_lines

APP = "app"
PAGE = "page"

Entry = AppEntry | PageEntry


def _kind(entry: Entry) -> str:
    return APP if isinstance(entry, AppEntry) else PAGE


def _target(entry: Entry) -> str:
    return entry.path if isinstance(entry, AppEntry) else entry.url


class CatalogSection(Section):
    itemsChanged = Signal()

    files = ("catalog.toml",)

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[Entry] = []

    # --- Section -----------------------------------------------------------------------------

    def load(self, config: Config) -> None:
        self._entries = [*config.catalog.apps, *config.catalog.pages]
        self.itemsChanged.emit()

    def validate(self) -> list[str]:
        problems = []
        for row, entry in enumerate(self._entries):
            problem = self._problem(row, entry)
            if problem:
                problems.append(f"{entry.name or 'Una entrada'}: {problem}")
        return problems

    def dump(self, documents: Mapping[str, Any]) -> None:
        apps = [entry for entry in self._entries if isinstance(entry, AppEntry)]
        pages = [entry for entry in self._entries if isinstance(entry, PageEntry)]
        dump_catalog(documents["catalog.toml"], apps, pages)

    # --- Para QML ----------------------------------------------------------------------------

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list[dict[str, Any]]:
        return [self._row(entry) for entry in self._entries]

    @Slot(int, result="QVariantMap")
    def entry(self, row: int) -> dict[str, Any]:
        """La entrada para el formulario; vacía si la fila no existe."""
        if not 0 <= row < len(self._entries):
            return {}
        return self._row(self._entries[row])

    @Slot(int, str, str, str, str, str, result=str)
    def submit(self, row: int, kind: str, name: str, target: str, args: str, aliases: str) -> str:
        """Guarda el formulario en el borrador: sustituye la fila o, con `row` < 0, añade una
        entrada. Devuelve el motivo por el que no vale, o vacío si se ha guardado."""
        name = " ".join(name.split())
        target = target.strip()
        entry: Entry
        if kind == APP:
            entry = AppEntry(name, target, split_lines(aliases), split_lines(args))
        else:
            entry = PageEntry(name, target, split_lines(aliases))
        problem = self._problem(row, entry)
        if problem:
            return problem
        if 0 <= row < len(self._entries):
            if self._entries[row] == entry:
                return ""
            self._entries[row] = entry
        else:
            self._entries.append(entry)
        self.itemsChanged.emit()
        self.touch()
        return ""

    @Slot(str, str, result=str)
    def warning(self, kind: str, target: str) -> str:
        """Aviso que no impide guardar: una ruta que no existe puede ser un nombre del PATH."""
        target = target.strip()
        if kind != APP or not target:
            return ""
        path = Path(target).expanduser()
        if ("/" in target or "\\" in target) and not path.exists():
            return "La ruta no existe en este equipo. Se guardará igualmente."
        return ""

    @Slot(int)
    def remove(self, row: int) -> None:
        if 0 <= row < len(self._entries):
            del self._entries[row]
            self.itemsChanged.emit()
            self.touch()

    # --- Interno -----------------------------------------------------------------------------

    def _row(self, entry: Entry) -> dict[str, Any]:
        return {
            "kind": _kind(entry),
            "name": entry.name,
            "target": _target(entry),
            "args": "\n".join(entry.args) if isinstance(entry, AppEntry) else "",
            "aliases": "\n".join(entry.aliases),
        }

    def _problem(self, row: int, entry: Entry) -> str:
        if not entry.name:
            return "Escriba un nombre."
        if isinstance(entry, AppEntry) and not entry.path:
            return "Escriba la ruta del programa o su nombre en el PATH."
        if isinstance(entry, PageEntry) and not entry.url.startswith(URL_SCHEMES):
            return "La dirección debe empezar por http:// o https://."
        taken = {
            comparable(spoken)
            for index, other in enumerate(self._entries) if index != row
            for spoken in (other.name, *other.aliases)
        }  # fmt: skip
        for spoken in (entry.name, *entry.aliases):
            if comparable(spoken) in taken:
                return f"«{spoken}» ya es el nombre de otra aplicación o página."
        return ""
