"""Compilación y coincidencia de patrones (enrutador-intenciones.md, sección 3).

Un patrón es una frase con texto fijo y huecos: `"crea el archivo {nombre} en {ruta}"`. Solo
el texto fijo cuenta para la puntuación; el contenido de los huecos no influye (RNF-15).
"""
from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz

from jarvis_assistant.intent_router.normalizer import normalize

EXACT_MAX_CHARS = 3  # un segmento así de corto («cd», «ls», «en») exige coincidencia exacta


class PatternError(ValueError):
    """El patrón no cumple las reglas de escritura."""


@dataclass(frozen=True)
class Pattern:
    source: str
    # Alterna texto fijo (tupla de palabras) y huecos (su nombre). Empieza por texto fijo.
    parts: tuple[tuple[str, ...] | str, ...]

    @property
    def holes(self) -> tuple[str, ...]:
        return tuple(part for part in self.parts if isinstance(part, str))

    @property
    def fixed_words(self) -> int:
        return sum(len(part) for part in self.parts if not isinstance(part, str))

    @property
    def key(self) -> str:
        """Forma normalizada: dos patrones con la misma clave son el mismo patrón."""
        return " ".join("{}" if isinstance(part, str) else " ".join(part) for part in self.parts)


@dataclass(frozen=True)
class Match:
    score: float  # la menor similitud de los segmentos fijos
    spans: dict[str, tuple[int, int]]  # hueco → palabras [inicio, fin) del texto


def compile_pattern(source: str) -> Pattern:
    parts: list[tuple[str, ...] | str] = []
    fixed: list[str] = []

    def flush() -> None:
        if fixed:
            words = tuple(normalize(" ".join(fixed)).split())
            if not words:
                raise PatternError(f"Texto fijo vacío en el patrón «{source}»")
            parts.append(words)
            fixed.clear()

    for token in source.split():
        if token.startswith("{") and token.endswith("}"):
            flush()
            name = token[1:-1]
            if not name.isidentifier():
                raise PatternError(f"Hueco no válido en el patrón «{source}»: {token}")
            if not parts:
                raise PatternError(f"El patrón «{source}» debe empezar por texto fijo")
            if isinstance(parts[-1], str):
                raise PatternError(f"El patrón «{source}» tiene dos huecos contiguos")
            if name in parts:
                raise PatternError(f"El patrón «{source}» repite el hueco {name}")
            parts.append(name)
        elif "{" in token or "}" in token:
            raise PatternError(f"Hueco mal escrito en el patrón «{source}»: {token}")
        else:
            fixed.append(token)
    flush()
    if not parts:
        raise PatternError("Patrón vacío")
    return Pattern(source, tuple(parts))


def similarity(segment: Sequence[str], window: Sequence[str]) -> float:
    wanted, found = " ".join(segment), " ".join(window)
    if len(wanted) <= EXACT_MAX_CHARS:
        return 100.0 if wanted == found else 0.0
    return fuzz.ratio(wanted, found)


def match(pattern: Pattern, words: Sequence[str], threshold: float) -> Match | None:
    """Coincidencia de `words` con el patrón, o None si no alcanza el umbral."""
    parts = pattern.parts
    first = parts[0]
    assert not isinstance(first, str)
    if len(parts) == 1:
        score = similarity(first, words)
        return Match(score, {}) if score >= threshold else None

    head = len(first)
    if len(words) < head:
        return None
    scores = [similarity(first, words[:head])]
    if scores[0] < threshold:
        return None

    end = len(words)
    index = len(parts) - 1
    last = parts[index]
    if not isinstance(last, str):  # el patrón termina en texto fijo: debe cerrar la frase
        start = end - len(last)
        if start <= head:
            return None
        score = similarity(last, words[start:end])
        if score < threshold:
            return None
        scores.append(score)
        end = start
        index -= 1

    spans: dict[str, tuple[int, int]] = {}
    while True:  # de derecha a izquierda: gana la última aparición de cada separador
        hole = parts[index]
        assert isinstance(hole, str)
        if index == 1:
            if end <= head:
                return None
            spans[hole] = (head, end)
            break
        separator = parts[index - 1]
        assert not isinstance(separator, str)
        size = len(separator)
        # Lo que queda a la izquierda necesita sitio: una palabra por hueco y su texto fijo.
        lowest = head + sum(1 if isinstance(p, str) else len(p) for p in parts[1 : index - 1])
        found = None
        for position in range(end - size - 1, lowest - 1, -1):
            score = similarity(separator, words[position : position + size])
            if score >= threshold:
                found = (position, score)
                break
        if found is None:
            return None
        position, score = found
        spans[hole] = (position + size, end)
        scores.append(score)
        end = position
        index -= 2
    return Match(min(scores), spans)
