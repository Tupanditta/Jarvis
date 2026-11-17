"""Identificadores estables de perfiles y plantillas.

El usuario ve y cambia el nombre; el id no cambia al renombrar, así las referencias entre
archivos (el perfil apunta a su plantilla) siguen valiendo.
"""
import re
import unicodedata
from collections.abc import Collection

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def is_valid_id(value: str) -> bool:
    return bool(ID_PATTERN.match(value))


def make_id(name: str, taken: Collection[str]) -> str:
    """Id nuevo a partir de un nombre: minúsculas, sin tildes, guiones en lugar de espacios,
    y un número al final si ya existe."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or "elemento"
    candidate, number = base, 2
    while candidate in taken:
        candidate = f"{base}-{number}"
        number += 1
    return candidate
