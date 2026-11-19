"""Directorio de trabajo (RN-14) y consolas de Comandos.

Vive en memoria: empieza en la carpeta del usuario en cada sesión y solo lo cambia
`comandos.cd`. Los demás módulos y el enrutador lo leen para resolver rutas relativas (RN-42).

Cada ventana de Comandos es una consola con su propio directorio de trabajo: la principal
(`MAIN_CONSOLE`) y las que abren los protocolos o el botón de la ventana. Una orden sin
consola usa la activa, la ventana de Comandos que está delante; las tareas de un protocolo, la
suya. `Consoles` se comporta como el `Workdir` de la consola activa, así el enrutador resuelve
las rutas de una orden en la consola que la recibirá.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from jarvis_assistant.core.action_api import MAIN_CONSOLE, Phrase


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


class Consoles:
    """Las consolas de la sesión, cada una con su directorio de trabajo. La principal siempre
    existe; las extra viven hasta que se cierra su ventana o la sesión."""

    def __init__(self, main: Workdir) -> None:
        self._main = main
        self._extra: dict[str, Workdir] = {}
        self._titles: dict[str, str] = {}
        self._active = MAIN_CONSOLE
        self._override: str | None = None
        self._count = 1  # la principal; las del botón se numeran a partir de 2

    @property
    def main(self) -> Workdir:
        return self._main

    @property
    def active(self) -> str:
        return self._active

    def get(self, console: str | None) -> Workdir:
        """El directorio de la consola; una que ya no existe usa el de la principal."""
        if console is None:
            return self.get(self._active)
        return self._extra.get(console, self._main)

    def exists(self, console: str) -> bool:
        return console == MAIN_CONSOLE or console in self._extra

    def title(self, console: str) -> str:
        return self._titles.get(console, "Comandos")

    def focus(self, console: str) -> None:
        """`console` pasa a ser la activa; si ya no existe, la principal."""
        self._active = console if self.exists(console) else MAIN_CONSOLE

    def open_for(self, key: str, title: str, start: Path | None = None) -> tuple[str, bool]:
        """La consola de `key` (un protocolo), creada si no existe. Empieza, también si ya
        existía, en `start` o, sin ella, en la carpeta del usuario. Devuelve su nombre y si
        es nueva."""
        console = f"{MAIN_CONSOLE}:{key}"
        created = console not in self._extra
        if created:
            self._extra[console] = Workdir(self._main.home)
        self._titles[console] = title
        workdir = self._extra[console]
        workdir.reset()
        if start is not None:
            workdir.change(start)
        return console, created

    def open_copy(self, source: str | None) -> str:
        """Consola nueva en la carpeta de `source`: el botón de la ventana."""
        self._count += 1
        console = f"{MAIN_CONSOLE}:{self._count}"
        workdir = Workdir(self._main.home)
        workdir.change(self.get(source).path)
        self._extra[console] = workdir
        self._titles[console] = f"Comandos {self._count}"
        return console

    def close(self, console: str) -> bool:
        """Retira una consola extra. False si no lo es o ya no existe."""
        if self._extra.pop(console, None) is None:
            return False
        self._titles.pop(console, None)
        if self._active == console:
            self._active = MAIN_CONSOLE
        return True

    def reset(self) -> None:
        """Sesión nueva: solo la principal, en la carpeta del usuario."""
        self._extra.clear()
        self._titles.clear()
        self._active = MAIN_CONSOLE
        self._count = 1
        self._main.reset()

    @contextmanager
    def using(self, console: str) -> Iterator[None]:
        """Mientras dura, `path` y `home` son los de `console`: para resolver las rutas de una
        tarea de protocolo en su consola. Sin esperas dentro: no lo ve ninguna otra orden."""
        previous, self._override = self._override, console
        try:
            yield
        finally:
            self._override = previous

    # Lo que el enrutador usa de un `Workdir`.

    @property
    def path(self) -> Path:
        return self.get(self._override).path

    @property
    def home(self) -> Path:
        return self._main.home


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
