"""Lo común a todos los apartados de la ventana de configuración."""
import unicodedata
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Property, QObject, Signal

from jarvis_assistant.config import Config


def comparable(text: str) -> str:
    """Forma de comparar nombres: sin mayúsculas, sin tildes y sin espacios sobrantes."""
    plain = unicodedata.normalize("NFKD", " ".join(text.split()))
    return "".join(char for char in plain if not unicodedata.combining(char)).casefold()


def split_lines(text: str) -> tuple[str, ...]:
    """Una entrada por línea (o separada por comas), sin vacías."""
    parts = [part.strip() for line in text.splitlines() for part in line.split(",")]
    return tuple(part for part in parts if part)


class Section(QObject):
    """Un apartado: carga su parte de la configuración, la edita en memoria, la valida y la
    vuelca en los documentos TOML al guardar.

    Las subclases definen `files` (los archivos que escribe), `load`, `validate` y `dump`, y
    llaman a `touch` en cada cambio. `locked` impide editar un apartado cuyo archivo tenía
    errores al abrir la ventana: guardar sobre él borraría lo que el asistente no pudo leer.
    """

    dirtyChanged = Signal()
    lockedChanged = Signal()

    files: tuple[str, ...] = ()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dirty = False
        self._locked = ""

    # --- Para las subclases ------------------------------------------------------------------

    def load(self, config: Config) -> None:
        """Toma su parte de `config`. Al terminar, el apartado no tiene cambios."""
        raise NotImplementedError

    def validate(self) -> list[str]:
        """Problemas que impiden guardar, en frases para el usuario. Vacía si todo es válido."""
        return []

    def dump(self, documents: Mapping[str, Any]) -> None:
        """Escribe su parte en los documentos `tomlkit` de `files`."""
        raise NotImplementedError

    def touch(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit()

    # --- Para la ventana ---------------------------------------------------------------------

    def reset(self, config: Config, locked: str = "") -> None:
        """Vuelve a cargar desde `config`, sin cambios pendientes."""
        self.load(config)
        if self._dirty:
            self._dirty = False
            self.dirtyChanged.emit()
        if locked != self._locked:
            self._locked = locked
            self.lockedChanged.emit()

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._dirty

    @Property(str, notify=lockedChanged)
    def locked(self) -> str:
        """Motivo por el que no se puede editar; vacío si se puede."""
        return self._locked
