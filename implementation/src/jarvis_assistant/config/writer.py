"""Escritura de los archivos de configuración.

Solo la usa la ventana de configuración, y solo al pulsar Guardar: el asistente nunca escribe
la configuración (RES-36). Con `tomlkit` se conservan los comentarios, el orden y el formato
de lo que no cambia.
"""
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument
from tomlkit.exceptions import TOMLKitError

from jarvis_assistant.config.loader import DEFAULTS_DIR


class WriteError(Exception):
    """No se ha podido escribir un archivo. `file`: su nombre."""

    def __init__(self, file: str, reason: str) -> None:
        super().__init__(f"{file}: {reason}")
        self.file = file
        self.reason = reason


def read_document(config_dir: Path, name: str) -> TOMLDocument:
    """El documento editable de `name`. Si falta, el predeterminado del paquete (con sus
    comentarios); si tampoco hay, uno vacío. Lanza `WriteError` si no se puede leer."""
    for path in (config_dir / name, DEFAULTS_DIR / name):
        try:
            return tomlkit.parse(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (OSError, UnicodeDecodeError, TOMLKitError) as error:
            raise WriteError(name, str(error)) from error
    return tomlkit.document()


def write_documents(config_dir: Path, documents: Mapping[str, TOMLDocument]) -> None:
    """Escribe cada documento en su archivo de `config_dir`.

    Cada archivo se escribe en un temporal de la misma carpeta y luego sustituye al original:
    nunca queda un archivo a medias. Si falla uno, lanza `WriteError` con su nombre; los ya
    sustituidos quedan bien formados.
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    for name, document in documents.items():
        target = config_dir / name
        try:
            descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=config_dir)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
                    file.write(tomlkit.dumps(document))
                os.replace(temporary, target)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise
        except OSError as error:
            raise WriteError(name, str(error)) from error
