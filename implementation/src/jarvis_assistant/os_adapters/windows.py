"""Adaptador de Windows (plataforma.md).

Todo lo que depende del sistema operativo: carpetas, lanzamiento, ventanas externas y propias,
búsqueda indexada e instancia única. Las APIs de Windows se llaman con `ctypes`
(arquitectura.md, sección 9). No contiene reglas de negocio ni requiere privilegios de
administrador.
"""
import asyncio
import ctypes
import logging
import os
import shutil
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from jarvis_assistant.os_adapters.base import (
    AppTarget,
    DiscoveredApp,
    EdgeNotFound,
    LaunchHandle,
    SearchKind,
    SearchOutcome,
    WindowRef,
)

logger = logging.getLogger(__name__)

APP_FOLDER = "Jarvis"
MUTEX_NAME = "Local\\JarvisAssistant"

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
SW_RESTORE = 9
FLASHW_ALL = 0x0003
FLASHW_TIMERNOFG = 0x000C
CREATE_NEW_CONSOLE = 0x00000010
CREATE_NO_WINDOW = 0x08000000

FRONT_SECONDS = 1.0  # tiempo que la pantalla queda marcada como superior al pasar al frente
WINDOW_POLL_SECONDS = 0.25
SEARCH_TIMEOUT_SECONDS = 5.0

# Carpetas conocidas (`KNOWNFOLDERID`): respetan la redirección a OneDrive.
KNOWN_FOLDERS = {
    "escritorio": ("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}", "Desktop"),
    "documentos": ("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}", "Documents"),
    "descargas": ("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads"),
    "imagenes": ("{33E28130-4E1E-4676-835A-98395C3BC3BB}", "Pictures"),
    "musica": ("{4BD8D571-6D19-48D3-BE97-422220080E43}", "Music"),
    "videos": ("{18989B1D-99B5-455B-841C-AB7C74E4DDFC}", "Videos"),
}

_EDGE_REGISTRY_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
_EDGE_RELATIVE = Path("Microsoft") / "Edge" / "Application" / "msedge.exe"
_SHORTCUTS = (".lnk", ".url")


class _Guid(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.c_ulong),
        ("data2", ctypes.c_ushort),
        ("data3", ctypes.c_ushort),
        ("data4", ctypes.c_ubyte * 8),
    ]


class _FlashInfo(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint),
        ("hwnd", ctypes.c_void_p),
        ("flags", ctypes.c_uint),
        ("count", ctypes.c_uint),
        ("timeout", ctypes.c_uint),
    ]


def _default_user32() -> Any:
    if sys.platform != "win32":
        return None
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetWindowPos.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_uint,
    ]  # fmt: skip
    user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long
    for name in ("IsWindow", "IsWindowVisible", "IsIconic", "SetForegroundWindow"):
        getattr(user32, name).argtypes = [ctypes.c_void_p]
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    user32.FlashWindowEx.argtypes = [ctypes.POINTER(_FlashInfo)]
    return user32


def _timer(seconds: float, callback: Callable[[], None]) -> None:
    timer = threading.Timer(seconds, callback)
    timer.daemon = True
    timer.start()


def _known_folder(folder_id: str) -> Path | None:
    """Ruta real de una carpeta conocida (`SHGetKnownFolderPath`), o None si no se obtiene."""
    if sys.platform != "win32":
        return None
    try:
        raw = uuid.UUID(folder_id).bytes_le
        guid = _Guid.from_buffer_copy(raw)
        found = ctypes.c_wchar_p()
        shell32 = ctypes.WinDLL("shell32")
        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_Guid), ctypes.c_ulong, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]  # fmt: skip
        if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(found)) != 0:
            return None
        path = Path(found.value) if found.value else None
        ctypes.WinDLL("ole32").CoTaskMemFree(ctypes.cast(found, ctypes.c_void_p))
        return path
    except (OSError, ValueError, AttributeError):
        logger.debug("No se ha podido resolver la carpeta conocida %s", folder_id, exc_info=True)
        return None


def _edge_from_registry() -> Path | None:
    """Ruta de `msedge.exe` según el registro (`App Paths`)."""
    if sys.platform != "win32":
        return None
    import winreg

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, _EDGE_REGISTRY_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, "")
        except OSError:
            continue
        if value:
            return Path(value)
    return None


def _run_search(command: Sequence[str]) -> subprocess.CompletedProcess:
    flags = CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.run(  # sin intérprete de órdenes
        list(command), capture_output=True, timeout=SEARCH_TIMEOUT_SECONDS, creationflags=flags
    )


def _decode(output: bytes) -> str:
    for encoding in ("utf-8", "oem", "mbcs"):
        try:
            return output.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return output.decode("utf-8", errors="replace")


_DEFAULT: Any = object()


class WindowsAdapter:
    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
        *,
        user32: Any = _DEFAULT,
        call_later: Callable[[float, Callable[[], None]], None] = _timer,
        popen: Callable[..., Any] = subprocess.Popen,
        startfile: Callable[[str], None] | None = None,
        which: Callable[[str], str | None] = shutil.which,
        known_folder: Callable[[str], Path | None] = _known_folder,
        edge_registry: Callable[[], Path | None] = _edge_from_registry,
        run_search: Callable[[Sequence[str]], Any] = _run_search,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ):
        self._environ = os.environ if environ is None else environ
        self._home = home or Path.home()
        self._user32 = _default_user32() if user32 is _DEFAULT else user32
        self._call_later = call_later
        self._popen = popen
        self._startfile = startfile or getattr(os, "startfile", None)
        self._which = which
        self._known_folder = known_folder
        self._edge_registry = edge_registry
        self._run_search = run_search
        self._sleep = sleep
        self._instance: Any = None

    # --- Carpetas ----------------------------------------------------------------------------

    def data_dir(self) -> Path:
        return self._local() / APP_FOLDER / "data"

    def config_dir(self) -> Path:
        roaming = self._environ.get("APPDATA")
        base = Path(roaming) if roaming else self._home / "AppData" / "Roaming"
        return base / APP_FOLDER / "config"

    def log_dir(self) -> Path:
        return self._local() / APP_FOLDER / "logs"

    def _local(self) -> Path:
        local = self._environ.get("LOCALAPPDATA")
        return Path(local) if local else self._home / "AppData" / "Local"

    def default_places(self) -> Mapping[str, Path]:
        """Escritorio, Documentos, Descargas, Imágenes, Música y Vídeos reales del sistema."""
        places = {}
        for name, (folder_id, fallback) in KNOWN_FOLDERS.items():
            places[name] = self._known_folder(folder_id) or self._home / fallback
        return places

    # --- Lanzamiento -------------------------------------------------------------------------

    async def launch_app(self, target: AppTarget) -> LaunchHandle:
        """`Popen` para ejecutables; `os.startfile` para accesos directos. No espera."""
        known = self._snapshot()
        if target.path.lower().endswith(_SHORTCUTS):
            self._start(target.path)
            return LaunchHandle(None, target.name, known)
        process = self._popen([target.path, *target.args])
        return LaunchHandle(getattr(process, "pid", None), target.name, known)

    async def open_url_in_edge(self, url: str) -> LaunchHandle:
        edge = self.edge_path()
        if edge is None:
            raise EdgeNotFound(url)
        process = self._popen([str(edge), url])
        # Edge suele reutilizar su ventana: vale cualquiera, no solo una nueva.
        return LaunchHandle(getattr(process, "pid", None), "Edge")

    def edge_path(self) -> Path | None:
        """`msedge.exe`: el del registro o el de las rutas habituales."""
        candidates = [self._edge_registry()]
        for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            base = self._environ.get(variable)
            if base:
                candidates.append(Path(base) / _EDGE_RELATIVE)
        return next((path for path in candidates if path is not None and path.is_file()), None)

    async def open_folder(self, path: Path) -> LaunchHandle:
        known = self._snapshot()
        self._popen(["explorer.exe", str(path)])
        # El explorador delega en su proceso principal: la ventana se busca por el título.
        return LaunchHandle(None, Path(path).name or str(path), known)

    async def open_terminal(self, cwd: Path) -> LaunchHandle:
        """Ubuntu (WSL) situada en `cwd`, dentro de Windows Terminal si está.

        `wsl.exe --cd` traduce la ruta de Windows y entra en ella: el perfil de WSL de
        Windows Terminal arranca en `~` aunque se le pase `-d`. Sin WSL, Windows Terminal
        en `cwd`; sin ninguno de los dos, `cmd.exe` en una consola nueva.
        """
        known = self._snapshot()
        terminal = self._which("wt.exe")
        wsl = self._which("wsl.exe")
        if wsl is not None:
            shell = [wsl, "--cd", str(cwd)]
            if terminal is not None:
                process = self._popen([terminal, "-d", str(cwd), *shell])
            else:
                process = self._popen(shell, cwd=str(cwd), creationflags=CREATE_NEW_CONSOLE)
        elif terminal is not None:
            process = self._popen([terminal, "-d", str(cwd)])
        else:
            process = self._popen(["cmd.exe"], cwd=str(cwd), creationflags=CREATE_NEW_CONSOLE)
        return LaunchHandle(getattr(process, "pid", None), "", known)

    async def open_with_default(self, path: Path) -> None:
        self._start(str(path))

    def _start(self, path: str) -> None:
        if self._startfile is None:
            raise OSError("os.startfile no está disponible en este sistema")
        self._startfile(path)

    def discover_apps(self) -> Sequence[DiscoveredApp]:
        """Accesos directos de las dos carpetas del menú Inicio, por su nombre."""
        found: dict[str, DiscoveredApp] = {}
        for folder in self._start_menu_folders():
            try:
                shortcuts = sorted(folder.rglob("*.lnk"))
            except OSError:
                continue
            for shortcut in shortcuts:
                app = DiscoveredApp(shortcut.stem, str(shortcut))
                found.setdefault(app.name.casefold(), app)
        return sorted(found.values(), key=lambda app: app.name.casefold())

    def _start_menu_folders(self) -> list[Path]:
        relative = Path("Microsoft") / "Windows" / "Start Menu" / "Programs"
        roaming = self._environ.get("APPDATA")
        folders = [(Path(roaming) if roaming else self._home / "AppData" / "Roaming") / relative]
        shared = self._environ.get("PROGRAMDATA")
        if shared:
            folders.append(Path(shared) / relative)
        return folders

    # --- Ventanas externas -------------------------------------------------------------------

    def _windows(self) -> list[tuple[int, int, str]]:
        """Ventanas de primer nivel visibles y con título: (identificador, proceso, título)."""
        user32 = self._user32
        if user32 is None:
            return []
        found: list[tuple[int, int, str]] = []

        def visit(hwnd: int, _param: int) -> bool:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buffer, length + 1)
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    found.append((int(hwnd), int(pid.value), buffer.value))
            return True

        callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(visit)
        user32.EnumWindows(callback, 0)
        return found

    def _snapshot(self) -> frozenset[int]:
        return frozenset(hwnd for hwnd, _pid, _title in self._windows())

    async def wait_for_window(self, handle: LaunchHandle, timeout: float = 10) -> WindowRef | None:
        """Sondea cada 250 ms una ventana nueva: la del proceso lanzado y, si no, la primera
        cuyo título contenga el nombre."""
        hint = handle.title_hint.casefold()
        elapsed = 0.0
        while True:
            fresh = [w for w in self._windows() if w[0] not in handle.known_windows]
            for hwnd, pid, title in fresh:
                if handle.pid is not None and pid == handle.pid:
                    return WindowRef(hwnd, title)
            for hwnd, _pid, title in fresh:
                if hint and hint in title.casefold():
                    return WindowRef(hwnd, title)
            if elapsed >= timeout:
                return None
            await self._sleep(WINDOW_POLL_SECONDS)
            elapsed += WINDOW_POLL_SECONDS

    def window_exists(self, ref: WindowRef) -> bool:
        return self._user32 is not None and bool(self._user32.IsWindow(ref.native_id))

    def focus_window(self, ref: WindowRef) -> bool:
        """Trae la ventana al frente. Si Windows no lo permite, parpadea en la barra de tareas
        y devuelve False."""
        user32 = self._user32
        if user32 is None or not user32.IsWindow(ref.native_id):
            return False
        if user32.IsIconic(ref.native_id):
            user32.ShowWindow(ref.native_id, SW_RESTORE)
        if user32.SetForegroundWindow(ref.native_id):
            return True
        info = _FlashInfo(
            ctypes.sizeof(_FlashInfo), ref.native_id, FLASHW_ALL | FLASHW_TIMERNOFG, 0, 0
        )
        user32.FlashWindowEx(ctypes.byref(info))
        return False

    @property
    def can_focus_windows(self) -> bool:
        return True

    # --- Ventanas propias --------------------------------------------------------------------

    def bring_own_window_to_front(self, native_id: int) -> None:
        """Marca la ventana como superior y, pasado 1 s, le quita la marca: queda delante
        aunque Windows no conceda el foco. El foco lo pide Qt, sin forzarlo."""
        user32 = self._user32
        if user32 is None:
            return
        flags = SWP_NOMOVE | SWP_NOSIZE
        user32.SetWindowPos(native_id, HWND_TOPMOST, 0, 0, 0, 0, flags | SWP_SHOWWINDOW)

        def release() -> None:
            user32.SetWindowPos(native_id, HWND_NOTOPMOST, 0, 0, 0, 0, flags | SWP_NOACTIVATE)

        self._call_later(FRONT_SECONDS, release)

    def make_non_activating(self, native_id: int, enabled: bool = True) -> None:
        """Estilo `WS_EX_NOACTIVATE`: la ventana no se activa al mostrarse ni con un clic.
        `enabled=False` lo quita, para que la caja de texto del HUD reciba el teclado."""
        user32 = self._user32
        if user32 is None:
            return
        style = user32.GetWindowLongW(native_id, GWL_EXSTYLE)
        style = style | WS_EX_NOACTIVATE if enabled else style & ~WS_EX_NOACTIVATE
        user32.SetWindowLongW(native_id, GWL_EXSTYLE, style)

    # --- Búsqueda ----------------------------------------------------------------------------

    def search_tool(self) -> str | None:
        """`es.exe` de *Everything*: en el `PATH` o en su carpeta de instalación."""
        found = self._which("es.exe")
        if found is not None:
            return found
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            base = self._environ.get(variable)
            if base and (Path(base) / "Everything" / "es.exe").is_file():
                return str(Path(base) / "Everything" / "es.exe")
        return None

    async def indexed_search(
        self, query: str, kind: SearchKind, limit: int
    ) -> SearchOutcome | None:
        """Busca por nombre con *Everything*. None si no está instalado o no responde."""
        tool = self.search_tool()
        if tool is None:
            return None
        command = [tool, "-n", str(limit)]
        if kind is SearchKind.FILE:
            command.append("/a-d")
        elif kind is SearchKind.FOLDER:
            command.append("/ad")
        command.append(query)
        try:
            done = await asyncio.to_thread(self._run_search, command)
        except (OSError, subprocess.SubprocessError):
            logger.warning("La búsqueda indexada no responde", exc_info=True)
            return None
        if done.returncode != 0:  # p. ej. Everything no está en marcha
            logger.warning("es.exe ha terminado con el código %s", done.returncode)
            return None
        paths = tuple(Path(line) for line in _decode(done.stdout).splitlines() if line.strip())
        return SearchOutcome(paths, len(paths))

    # --- Proceso -----------------------------------------------------------------------------

    def acquire_single_instance(self) -> bool:
        """True si este proceso es la única instancia. El mutex se conserva hasta salir."""
        from jarvis_assistant.process.single_instance import acquire_single_instance

        if self._instance is None:
            self._instance = acquire_single_instance(MUTEX_NAME)
        return self._instance is not None
