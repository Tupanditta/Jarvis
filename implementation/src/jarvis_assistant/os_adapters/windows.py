"""Adaptador de Windows (plataforma.md).

De momento resuelve las carpetas del usuario y las operaciones sobre las ventanas propias que
necesita la interfaz; el resto de `PlatformAdapter` llega con los módulos de acción que lo
usan. Las APIs de Windows se llaman con `ctypes` (arquitectura.md, sección 9).
"""
import ctypes
import logging
import os
import sys
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

APP_FOLDER = "Jarvis"

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000

FRONT_SECONDS = 1.0  # tiempo que la pantalla queda marcada como superior al pasar al frente


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
    return user32


def _timer(seconds: float, callback: Callable[[], None]) -> None:
    timer = threading.Timer(seconds, callback)
    timer.daemon = True
    timer.start()


_DEFAULT: Any = object()


class WindowsAdapter:
    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
        *,
        user32: Any = _DEFAULT,
        call_later: Callable[[float, Callable[[], None]], None] = _timer,
    ):
        self._environ = os.environ if environ is None else environ
        self._home = home or Path.home()
        self._user32 = _default_user32() if user32 is _DEFAULT else user32
        self._call_later = call_later

    # Carpetas

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

    # Ventanas propias

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
