"""Interfaz única de todo lo que depende del sistema operativo (RES-06).

`main.py` elige el adaptador según el sistema y lo inyecta. El adaptador solo ejecuta
operaciones y devuelve resultados: no contiene reglas de negocio.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


class EdgeNotFound(Exception):
    """Microsoft Edge no está instalado."""


class SearchKind(Enum):
    """Qué busca una búsqueda indexada."""

    FILE = "archivo"
    FOLDER = "carpeta"
    ANY = "cualquiera"


@dataclass(frozen=True)
class AppTarget:
    """Aplicación que se va a lanzar."""

    name: str
    path: str  # ejecutable, acceso directo o nombre en el PATH
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiscoveredApp:
    """Aplicación instalada encontrada por el adaptador."""

    name: str
    path: str


@dataclass(frozen=True)
class LaunchHandle:
    """Resultado de un lanzamiento; sirve para localizar después su ventana."""

    pid: int | None
    title_hint: str
    known_windows: frozenset[int] = frozenset()  # ventanas que ya existían antes de lanzar


@dataclass(frozen=True)
class WindowRef:
    """Ventana externa de primer nivel."""

    native_id: int
    title: str


@dataclass(frozen=True)
class SearchOutcome:
    """Resultado de una búsqueda indexada."""

    paths: tuple[Path, ...]
    total: int


@runtime_checkable
class PlatformAdapter(Protocol):
    """Operaciones dependientes del sistema operativo."""

    # Carpetas
    def data_dir(self) -> Path: ...
    def config_dir(self) -> Path: ...
    def log_dir(self) -> Path: ...
    def default_places(self) -> Mapping[str, Path]: ...

    # Lanzamiento
    async def launch_app(self, target: AppTarget) -> LaunchHandle: ...
    async def open_url_in_edge(self, url: str) -> LaunchHandle: ...  # lanza EdgeNotFound
    async def open_folder(self, path: Path) -> LaunchHandle: ...
    async def open_terminal(self, cwd: Path) -> LaunchHandle: ...
    async def open_with_default(self, path: Path) -> None: ...
    def discover_apps(self) -> Sequence[DiscoveredApp]: ...

    # Ventanas externas
    async def wait_for_window(
        self, handle: LaunchHandle, timeout: float = 10
    ) -> WindowRef | None: ...
    def window_exists(self, ref: WindowRef) -> bool: ...
    def focus_window(self, ref: WindowRef) -> bool: ...
    @property
    def can_focus_windows(self) -> bool: ...

    # Ventanas propias
    def bring_own_window_to_front(self, native_id: int) -> None: ...
    def make_non_activating(self, native_id: int, enabled: bool = True) -> None: ...

    # Búsqueda: None = herramienta indexada no disponible
    async def indexed_search(
        self, query: str, kind: SearchKind, limit: int
    ) -> SearchOutcome | None: ...

    # Proceso
    def acquire_single_instance(self) -> bool: ...
