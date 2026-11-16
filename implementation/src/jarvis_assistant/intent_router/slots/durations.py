"""Duraciones escritas (enrutador-intenciones.md, sección 4).

`{número} {unidad}` con unidad segundos, minutos, horas o días; «media hora», «un cuarto de
hora», «una hora y media» y sumas como «dos horas y diez minutos». Trabaja sobre palabras
normalizadas (minúsculas, sin tildes). Sin expresiones regulares (RES-25).
"""
from collections.abc import Sequence
from datetime import timedelta

from jarvis_assistant.intent_router.slots import numbers

_UNITS = {
    "segundo": 1, "segundos": 1,
    "minuto": 60, "minutos": 60,
    "hora": 3600, "horas": 3600,
    "dia": 86400, "dias": 86400,
}  # fmt: skip

_FIXED: dict[tuple[str, ...], int] = {
    ("media", "hora"): 1800,
    ("un", "cuarto", "de", "hora"): 900,
    ("cuarto", "de", "hora"): 900,
}


def parse(text: str) -> timedelta | None:
    """La duración que dice `text` (normalizado), o None si no es una duración."""
    return parse_words(text.split())


def parse_words(words: Sequence[str]) -> timedelta | None:
    """Como `parse`, sobre las palabras ya separadas. Solo duraciones mayores que cero."""
    seconds = _seconds(tuple(words))
    return None if not seconds else timedelta(seconds=seconds)


def _seconds(words: tuple[str, ...]) -> int | None:
    if not words:
        return None
    if words in _FIXED:
        return _FIXED[words]
    simple = _simple(words)
    if simple is not None:
        return simple
    # «una hora y media»: la mitad de la unidad anterior.
    if len(words) >= 4 and words[-2:] == ("y", "media"):
        unit = _UNITS.get(words[-3])
        base = _simple(words[:-2])
        if unit is not None and base is not None and unit > 1:
            return base + unit // 2
    # «dos horas y diez minutos»: dos duraciones unidas por «y».
    for index, word in enumerate(words):
        if word != "y" or index == 0:
            continue
        left, right = _seconds(words[:index]), _seconds(words[index + 1 :])
        if left and right:
            return left + right
    return None


def _simple(words: tuple[str, ...]) -> int | None:
    """`{número} {unidad}`."""
    if len(words) < 2 or words[-1] not in _UNITS:
        return None
    amount = numbers.parse(" ".join(words[:-1]))
    if amount is None:
        return None
    return amount * _UNITS[words[-1]]
