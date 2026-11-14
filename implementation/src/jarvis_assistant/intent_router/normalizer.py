"""Normalización del texto transcrito y de los patrones (enrutador-intenciones.md, sección 2)."""
import unicodedata
from collections.abc import Mapping

# Signos que se conservan dentro de una palabra: nombres de archivo y rutas.
_INNER_SIGNS = "./\\:_-"


def normalize(text: str, aliases: Mapping[str, str] | None = None) -> str:
    """Minúsculas, sin tildes ni signos, espacios colapsados y alias aplicados."""
    words = _words(text)
    if aliases:
        words = _apply_aliases(words, aliases)
    return " ".join(words)


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


def _apply_aliases(words: list[str], aliases: Mapping[str, str]) -> list[str]:
    """Sustituye palabras o secuencias de palabras; a igualdad de posición gana la más larga."""
    table = {tuple(_words(heard)): meant.lower().split() for heard, meant in aliases.items()}
    table.pop((), None)
    if not table:
        return words
    longest = max(len(key) for key in table)
    result: list[str] = []
    index = 0
    while index < len(words):
        for size in range(min(longest, len(words) - index), 0, -1):
            replacement = table.get(tuple(words[index : index + size]))
            if replacement is not None:
                result.extend(replacement)
                index += size
                break
        else:
            result.append(words[index])
            index += 1
    return result
