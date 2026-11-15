"""Datos que llevan los eventos de contenido de los paneles (bus-eventos.md).

Son valores inmutables: cada evento de contenido lleva la lista completa de su panel.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Entry:
    """Elemento de un listado de directorio."""

    name: str
    is_dir: bool


@dataclass(frozen=True)
class TreeNode:
    """Entrada del árbol de directorios, en orden de dibujo. `depth`: nivel, desde 1."""

    name: str
    depth: int
    is_dir: bool


OpenedKind = Literal["aplicacion", "pagina", "carpeta"]


@dataclass(frozen=True)
class OpenedItem:
    """Elemento abierto por el asistente en la sesión."""

    id: int
    title: str
    kind: OpenedKind
    status: str  # estado de la apertura (RN-01)
    can_focus: bool


@dataclass(frozen=True)
class SearchResult:
    """Resultado numerado de una búsqueda. `index`: lo que el usuario escribe (RN-50)."""

    index: int
    name: str
    is_dir: bool
    folder: str
    path: str
