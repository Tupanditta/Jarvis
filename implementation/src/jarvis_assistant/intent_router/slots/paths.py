"""Resolución de rutas escritas (enrutador-intenciones.md, sección 6).

Orden: palabras especiales, ruta literal y niveles separados por «barra». Cada nivel se busca
entre las subcarpetas reales, por similitud, de modo que el resultado es siempre una carpeta
que existe; si no, el error distingue «no existe» de «no es una carpeta» (RN-41).
"""
import os
from collections.abc import Mapping
from pathlib import Path

from rapidfuzz import fuzz

from jarvis_assistant.intent_router.normalizer import normalize

PLACE_THRESHOLD = 85
LEVEL_SEPARATOR = "barra"

_HERE = ("aqui", "esta carpeta")
_PARENT = ("atras", "arriba", "carpeta anterior")
_HOME = ("inicio", "carpeta personal")
_LITERAL_SIGNS = ("/", "\\", ":")

_LETTERS = {
    "a": "a", "be": "b", "ce": "c", "de": "d", "e": "e", "efe": "f", "ge": "g", "hache": "h",
    "i": "i", "jota": "j", "ka": "k", "ele": "l", "eme": "m", "ene": "n", "o": "o", "pe": "p",
    "cu": "q", "erre": "r", "ese": "s", "te": "t", "u": "u", "uve": "v", "equis": "x",
    "zeta": "z",
}  # fmt: skip


class PathError(Exception):
    """La ruta escrita no lleva a una carpeta. `kind`: `no_existe` o `no_es_carpeta`."""

    def __init__(self, kind: str, name: str) -> None:
        super().__init__(f"{kind}: {name}")
        self.kind = kind
        self.name = name


def resolve(
    spoken: str,
    workdir: Path,
    places: Mapping[str, Path],
    *,
    home: Path,
    threshold: float = 80,
) -> Path:
    """La carpeta a la que se refiere `spoken`, el texto original de la entidad."""
    normalized = normalize(spoken)
    if normalized in _HERE:
        return workdir
    if normalized in _PARENT:
        return workdir.parent
    if normalized in _HOME:
        return home
    if any(sign in spoken for sign in _LITERAL_SIGNS):
        return _literal(spoken.strip(), workdir)

    levels = [" ".join(level) for level in _split(normalized.split())]
    if not levels or not all(levels):
        raise PathError("no_existe", spoken.strip())
    current = _first_level(levels[0], workdir, places, threshold)
    for level in levels[1:]:
        current = _child(current, level, threshold)
    return current


def _literal(text: str, workdir: Path) -> Path:
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = workdir / path
    if not path.exists():
        raise PathError("no_existe", text)
    if not path.is_dir():
        raise PathError("no_es_carpeta", path.name or text)
    return path


def _split(words: list[str]) -> list[list[str]]:
    levels: list[list[str]] = [[]]
    for word in words:
        if word == LEVEL_SEPARATOR:
            levels.append([])
        else:
            levels[-1].append(word)
    return levels


def _first_level(name: str, workdir: Path, places: Mapping[str, Path], threshold: float) -> Path:
    place = _place(name, places)
    if place is not None:
        if not place.exists():
            raise PathError("no_existe", name)
        if not place.is_dir():
            raise PathError("no_es_carpeta", name)
        return place
    drive = _drive(name)
    if drive is not None:
        if not drive.is_dir():
            raise PathError("no_existe", name)
        return drive
    return _child(workdir, name, threshold)


def _place(name: str, places: Mapping[str, Path]) -> Path | None:
    best: tuple[float, str] | None = None
    for place in places:
        score = fuzz.ratio(name, normalize(place))
        if score >= PLACE_THRESHOLD and (best is None or (-score, place) < (-best[0], best[1])):
            best = (score, place)
    return None if best is None else Path(places[best[1]])


def _drive(name: str) -> Path | None:
    words = name.split()
    if len(words) == 2 and words[0] in ("disco", "unidad") and words[1] in _LETTERS:
        return Path(f"{_LETTERS[words[1]].upper()}:\\")
    return None


def _child(parent: Path, name: str, threshold: float) -> Path:
    """La subcarpeta de `parent` que mejor coincide con `name`."""
    folders: list[str] = []
    files: list[str] = []
    try:
        with os.scandir(parent) as entries:
            for entry in entries:
                try:
                    (folders if entry.is_dir() else files).append(entry.name)
                except OSError:
                    continue
    except OSError:
        raise PathError("no_existe", name) from None
    found = _closest(name, folders, threshold)
    if found is not None:
        return parent / found
    as_file = _closest(name, files, threshold)
    if as_file is not None:
        raise PathError("no_es_carpeta", as_file)
    raise PathError("no_existe", name)


def _closest(name: str, candidates: list[str], threshold: float) -> str | None:
    best: tuple[float, str, str] | None = None
    for candidate in candidates:
        normalized = normalize(candidate)
        score = 101.0 if normalized == name else fuzz.WRatio(name, normalized)
        if score < threshold:
            continue
        key = (-score, normalized, candidate)
        if best is None or key < best:
            best = key
    return None if best is None else best[2]
