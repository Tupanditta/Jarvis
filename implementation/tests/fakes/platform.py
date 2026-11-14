"""Doble de `PlatformAdapter`: registra las llamadas y simula ventanas y resultados."""
import itertools
from collections.abc import Mapping, Sequence
from pathlib import Path

from jarvis_assistant.os_adapters.base import (
    AppTarget,
    DiscoveredApp,
    EdgeNotFound,
    LaunchHandle,
    SearchKind,
    SearchOutcome,
    WindowRef,
)

_PLACES = ("escritorio", "documentos", "descargas", "imagenes", "musica", "videos")


class FakePlatform:
    """Plataforma simulada sobre una carpeta temporal.

    Atributos que la prueba puede cambiar: `window_appears`, `focus_succeeds`, `can_focus`,
    `edge_available`, `launch_error`, `search_outcome`, `discovered`.
    Lo ocurrido queda en `calls` (nombre y argumentos, en orden) y en `focused`.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.calls: list[tuple[str, tuple]] = []
        self.focused: list[WindowRef] = []
        self.window_appears = True
        self.focus_succeeds = True
        self.can_focus = True
        self.edge_available = True
        self.launch_error: Exception | None = None
        self.search_outcome: SearchOutcome | None = None
        self.discovered: list[DiscoveredApp] = []
        self._windows: dict[int, WindowRef] = {}
        self._ids = itertools.count(1)
        self._instance_taken = False

    # Carpetas
    def data_dir(self) -> Path:
        return self.root / "local" / "Jarvis" / "data"

    def config_dir(self) -> Path:
        return self.root / "roaming" / "Jarvis" / "config"

    def log_dir(self) -> Path:
        return self.root / "local" / "Jarvis" / "logs"

    def default_places(self) -> Mapping[str, Path]:
        places = {name: self.root / "home" / name for name in _PLACES}
        for path in places.values():
            path.mkdir(parents=True, exist_ok=True)
        return places

    # Lanzamiento
    async def launch_app(self, target: AppTarget) -> LaunchHandle:
        return self._launch("launch_app", target, title=target.name)

    async def open_url_in_edge(self, url: str) -> LaunchHandle:
        self.calls.append(("open_url_in_edge", (url,)))
        if not self.edge_available:
            raise EdgeNotFound(url)
        return self._handle(title=url)

    async def open_folder(self, path: Path) -> LaunchHandle:
        return self._launch("open_folder", path, title=Path(path).name)

    async def open_terminal(self, cwd: Path) -> LaunchHandle:
        return self._launch("open_terminal", cwd, title="Terminal")

    async def open_with_default(self, path: Path) -> None:
        self.calls.append(("open_with_default", (path,)))
        if self.launch_error is not None:
            raise self.launch_error

    def discover_apps(self) -> Sequence[DiscoveredApp]:
        self.calls.append(("discover_apps", ()))
        return list(self.discovered)

    # Ventanas externas
    async def wait_for_window(self, handle: LaunchHandle, timeout: float = 10) -> WindowRef | None:
        self.calls.append(("wait_for_window", (handle, timeout)))
        if not self.window_appears:
            return None
        ref = WindowRef(native_id=next(self._ids), title=handle.title_hint)
        self._windows[ref.native_id] = ref
        return ref

    def window_exists(self, ref: WindowRef) -> bool:
        return ref.native_id in self._windows

    def focus_window(self, ref: WindowRef) -> bool:
        self.calls.append(("focus_window", (ref,)))
        if not self.focus_succeeds or not self.window_exists(ref):
            return False
        self.focused.append(ref)
        return True

    @property
    def can_focus_windows(self) -> bool:
        return self.can_focus

    # Ventanas propias
    def bring_own_window_to_front(self, native_id: int) -> None:
        self.calls.append(("bring_own_window_to_front", (native_id,)))

    def make_non_activating(self, native_id: int) -> None:
        self.calls.append(("make_non_activating", (native_id,)))

    # Búsqueda
    async def indexed_search(
        self, query: str, kind: SearchKind, limit: int
    ) -> SearchOutcome | None:
        self.calls.append(("indexed_search", (query, kind, limit)))
        return self.search_outcome

    # Proceso
    def acquire_single_instance(self) -> bool:
        if self._instance_taken:
            return False
        self._instance_taken = True
        return True

    # Ayudas de las pruebas
    def close_window(self, ref: WindowRef) -> None:
        """Simula que el usuario cierra la ventana."""
        self._windows.pop(ref.native_id, None)

    def _launch(self, name: str, argument: object, *, title: str) -> LaunchHandle:
        self.calls.append((name, (argument,)))
        if self.launch_error is not None:
            raise self.launch_error
        return self._handle(title)

    def _handle(self, title: str) -> LaunchHandle:
        return LaunchHandle(pid=1000 + next(self._ids), title_hint=title)
