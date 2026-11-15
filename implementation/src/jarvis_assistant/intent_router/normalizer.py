"""Normalización del texto transcrito y de los patrones (enrutador-intenciones.md, sección 2)."""
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

# Signos que se conservan dentro de una palabra: nombres de archivo y rutas.
_INNER_SIGNS = "./\\:_-"


def normalize(text: str, aliases: Mapping[str, str] | None = None) -> str:
    """Minúsculas, sin tildes ni signos, espacios colapsados y alias aplicados."""
    words = _words(text)
    if aliases:
        words = _apply_aliases(words, aliases)
    return " ".join(words)


@dataclass(frozen=True)
class Tokens:
    """Texto normalizado, palabra a palabra, con el trozo del texto original de cada una.

    `sources[i]` es el intervalo (primero, último) de palabras de `originals` del que sale
    `words[i]`: así una entidad de texto libre conserva lo que el usuario escribió.
    """

    words: tuple[str, ...]
    sources: tuple[tuple[int, int], ...]
    originals: tuple[str, ...]

    def original(self, start: int, end: int) -> str:
        """Texto original de las palabras normalizadas `start` a `end` (sin incluir)."""
        if start >= end:
            return ""
        first, last = self.sources[start][0], self.sources[end - 1][1]
        return " ".join(self.originals[first : last + 1])


def tokenize(text: str, aliases: Mapping[str, str] | None = None) -> Tokens:
    """Como `normalize`, pero conserva de qué palabra original sale cada palabra."""
    originals = tuple(text.split())
    words: list[str] = []
    sources: list[tuple[int, int]] = []
    for index, original in enumerate(originals):
        for word in _words(original):
            words.append(word)
            sources.append((index, index))
    table = _alias_table(aliases) if aliases else {}
    if table:
        words, sources = _replace(words, sources, table)
    return Tokens(tuple(words), tuple(sources), originals)


def _words(text: str) -> list[str]:
    cleaned = "".join(
        char if char.isalnum() or char in _INNER_SIGNS else " "
        for char in _strip_accents(text.lower())
    )
    stripped = (word.strip(_INNER_SIGNS) for word in cleaned.split())
    return [word for word in stripped if word]


def _strip_accents(text: str) -> str:
    """Quita tildes y diéresis; la `ñ` se conserva."""
    result = []
    for char in text:
        if char == "ñ":
            result.append(char)
            continue
        decomposed = unicodedata.normalize("NFD", char)
        result.append("".join(c for c in decomposed if not unicodedata.combining(c)))
    return "".join(result)


def _alias_table(aliases: Mapping[str, str]) -> dict[tuple[str, ...], list[str]]:
    table = {tuple(_words(heard)): meant.lower().split() for heard, meant in aliases.items()}
    table.pop((), None)
    return table


def _apply_aliases(words: list[str], aliases: Mapping[str, str]) -> list[str]:
    """Sustituye palabras o secuencias de palabras; a igualdad de posición gana la más larga."""
    table = _alias_table(aliases)
    if not table:
        return words
    return _replace(words, [(0, 0)] * len(words), table)[0]


def _replace(
    words: list[str], sources: list[tuple[int, int]], table: dict[tuple[str, ...], list[str]]
) -> tuple[list[str], list[tuple[int, int]]]:
    longest = max(len(key) for key in table)
    result: list[str] = []
    origins: list[tuple[int, int]] = []
    index = 0
    while index < len(words):
        for size in range(min(longest, len(words) - index), 0, -1):
            replacement = table.get(tuple(words[index : index + size]))
            if replacement is not None:
                span = (sources[index][0], sources[index + size - 1][1])
                result.extend(replacement)
                origins.extend([span] * len(replacement))
                index += size
                break
        else:
            result.append(words[index])
            origins.append(sources[index])
            index += 1
    return result, origins
