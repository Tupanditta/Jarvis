"""Escritura de los archivos de configuración.

La usa la ventana de configuración, al pulsar Guardar. El asistente solo escribe lo que le
pide el usuario de forma explícita: el Acedor al eliminar un perfil (`remove_profile`) y el
módulo Catálogo al añadir o eliminar una entrada (`save_launchers`). Con `tomlkit` se
conservan los comentarios, el orden y el formato de lo que no cambia.
"""
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument
from tomlkit.exceptions import TOMLKitError

from jarvis_assistant.config.catalog import Catalog, dump_catalog
from jarvis_assistant.config.commands import Binary, dump_binaries
from jarvis_assistant.config.loader import DEFAULTS_DIR, check, load
from jarvis_assistant.config.profiles import dump_profiles


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


def remove_profile(config_dir: Path, profile_id: str) -> None:
    """Quita un perfil de `profiles.toml`, conservando los comentarios. Lo usa el Acedor."""
    config, _errors = load(config_dir)
    remaining = [profile for profile in config.profiles if profile.id != profile_id]
    if len(remaining) == len(config.profiles):
        return
    document = read_document(config_dir, "profiles.toml")
    dump_profiles(document, remaining)
    write_documents(config_dir, {"profiles.toml": document})


def save_launchers(
    config_dir: Path,
    catalog: Catalog | None = None,
    binaries: Sequence[Binary] | None = None,
) -> None:
    """Escribe las aplicaciones y páginas de `catalog` en `catalog.toml` y los `binaries` en
    `commands.toml`; lo que es None no se toca. Lo usa el módulo Catálogo.

    Lanza `WriteError` si el archivo tenía errores al leerlo (guardar sobre él borraría lo que
    el asistente no ha podido leer) o si el resultado no es válido."""
    dumps: dict[str, Callable[[TOMLDocument], None]] = {}
    if catalog is not None:
        dumps["catalog.toml"] = lambda document: dump_catalog(
            document, catalog.apps, catalog.pages
        )
    if binaries is not None:
        dumps["commands.toml"] = lambda document: dump_binaries(document, binaries)
    if not dumps:
        return
    _config, errors = load(config_dir)
    for error in errors:
        if error.file in dumps and not error.warning:
            raise WriteError(error.file, f"tiene un error; corríjalo a mano: {error.reason}")
    documents = {}
    for name, dump in dumps.items():
        document = read_document(config_dir, name)
        dump(document)
        for error in check(name, document.unwrap()):
            if not error.warning:
                raise WriteError(name, f"{error.key}: {error.reason}")
        documents[name] = document
    write_documents(config_dir, documents)
