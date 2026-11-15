"""Números escritos: cifras, letras de 0 a 999 y ordinales del 1 al 10.

Trabaja sobre texto normalizado (minúsculas, sin tildes). Sin expresiones regulares (RES-25).
"""

_UNITS = {
    "cero": 0, "uno": 1, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintiun": 21,
    "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}  # fmt: skip

_TENS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
    "ochenta": 80, "noventa": 90,
}  # fmt: skip

_HUNDREDS = {
    "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300, "cuatrocientos": 400,
    "quinientos": 500, "seiscientos": 600, "setecientos": 700, "ochocientos": 800,
    "novecientos": 900,
}  # fmt: skip
_HUNDREDS.update({word[:-2] + "as": value for word, value in list(_HUNDREDS.items())[2:]})

_ORDINALS = {
    "primero": 1, "primer": 1, "primera": 1, "segundo": 2, "segunda": 2, "tercero": 3,
    "tercer": 3, "tercera": 3, "cuarto": 4, "cuarta": 4, "quinto": 5, "quinta": 5,
    "sexto": 6, "sexta": 6, "septimo": 7, "septima": 7, "octavo": 8, "octava": 8,
    "noveno": 9, "novena": 9, "decimo": 10, "decima": 10,
}  # fmt: skip

_LEADING = ("el", "la", "numero")  # «la segunda», «el número tres»

MAX_VALUE = 999


def parse(text: str) -> int | None:
    """El número que dice `text`, o None si no es un número."""
    words = text.split()
    while words and words[0] in _LEADING:
        words = words[1:]
    if not words:
        return None
    if len(words) == 1:
        word = words[0]
        if word.isascii() and word.isdigit():
            return int(word)
        if word in _ORDINALS:
            return _ORDINALS[word]
    return _cardinal(words)


def _cardinal(words: list[str]) -> int | None:
    total = 0
    rest = list(words)
    if rest[0] in _HUNDREDS:
        word = rest.pop(0)
        if word == "cien" and rest:
            return None  # «cien tres» no existe: es «ciento tres»
        total = _HUNDREDS[word]
        if not rest:
            return total
    below = _below_hundred(rest)
    return None if below is None else total + below


def _below_hundred(words: list[str]) -> int | None:
    if len(words) == 1:
        word = words[0]
        if word in _UNITS:
            return _UNITS[word]
        return _TENS.get(word)
    if len(words) == 3 and words[0] in _TENS and words[1] == "y":
        unit = _UNITS.get(words[2])
        if unit is not None and 1 <= unit <= 9:
            return _TENS[words[0]] + unit
    return None
