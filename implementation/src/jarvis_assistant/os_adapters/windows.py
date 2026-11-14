"""Adaptador de Windows (plataforma.md).

De momento solo resuelve las carpetas del usuario, que es lo que necesita el arranque; el
resto de `PlatformAdapter` llega con los módulos de acción que lo usan.
"""
import os
from collections.abc import Mapping
from pathlib import Path

APP_FOLDER = "Jarvis"


class WindowsAdapter:
    def __init__(self, environ: Mapping[str, str] | None = None, home: Path | None = None):
        self._environ = os.environ if environ is None else environ
        self._home = home or Path.home()

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
