"""Nombres de archivo y carpeta nuevos (enrutador-intenciones.md, sección 7)."""
from pathlib import PurePath

from jarvis_assistant.intent_router.normalizer import normalize

_FORBIDDEN = set('<>:"/\\|?*')
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}
_LEVEL_SEPARATOR = "barra"


class InvalidNameError(ValueError):
    """El nombre está vacío, tiene caracteres no permitidos o está reservado."""


def build(spoken: str) -> str:
    """Nombre de archivo o carpeta a partir de lo escrito: «notas punto txt» → `notas.txt`."""
    parts: list[str] = []
    glue: str | None = None  # signo que une la palabra siguiente con la anterior
    words = spoken.split()
    index = 0
    while index < len(words):
        word = words[index]
        key = normalize(word)
        if key == "punto":
            glue = "."
        elif key == "guion":
            if index + 1 < len(words) and normalize(words[index + 1]) == "bajo":
                glue = "_"
                index += 1
            else:
                glue = "-"
        else:
            if glue is not None and parts:
                parts[-1] = f"{parts[-1]}{glue}{word}"
            elif glue is not None:
                parts.append(f"{glue}{word}")
            else:
                parts.append(word)
            glue = None
        index += 1
    if glue is not None and parts:
        parts[-1] += glue
    name = " ".join(parts)
    _validate(name)
    return name


def build_path(spoken: str) -> PurePath:
    """Ruta anidada nueva: los niveles se separan con «barra» o con `/`."""
    levels: list[list[str]] = [[]]
    for word in spoken.replace("/", f" {_LEVEL_SEPARATOR} ").split():
        if normalize(word) == _LEVEL_SEPARATOR:
            levels.append([])
        else:
            levels[-1].append(word)
    return PurePath(*(build(" ".join(level)) for level in levels))


def _validate(name: str) -> None:
    if not name or name in (".", ".."):
        raise InvalidNameError("nombre vacío")
    if any(char in _FORBIDDEN or ord(char) < 32 for char in name):
        raise InvalidNameError("caracteres no permitidos")
    if name.endswith((".", " ")):
        raise InvalidNameError("no puede terminar en punto ni en espacio")
    if name.split(".")[0].strip().lower() in _RESERVED:
        raise InvalidNameError("nombre reservado")
