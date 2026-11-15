"""Directorio de trabajo compartido (RN-14).

Vive en memoria: empieza en la carpeta del usuario en cada sesión y solo lo cambia
`comandos.cd`. Los demás módulos y el enrutador lo leen para resolver rutas relativas (RN-42).
"""
from pathlib import Path

from jarvis_assistant.core.action_api import Phrase


class Workdir:
    def __init__(self, home: Path) -> None:
        self.home = Path(home)
        self.path = self.home

    def reset(self) -> None:
        """Vuelve a la carpeta del usuario: sesión nueva."""
        self.path = self.home

    def change(self, path: Path) -> None:
        self.path = Path(path)

    def resolve(self, path: Path) -> Path:
        """Una ruta relativa se resuelve respecto al directorio de trabajo (RN-42)."""
        path = Path(path)
        return path if path.is_absolute() else self.path / path


def folder_name(path: Path) -> str:
    """Nombre real de la carpeta, para decirlo; la raíz de una unidad se dice entera."""
    return path.name or str(path)


def invalid_folder(path: Path) -> Phrase | None:
    """Motivo por el que `path` no vale como carpeta (RN-41), o None si vale."""
    if not path.exists():
        return Phrase("ruta.no_existe", {"nombre": folder_name(path)})
    if not path.is_dir():
        return Phrase("ruta.no_es_carpeta", {"nombre": folder_name(path)})
    return None
