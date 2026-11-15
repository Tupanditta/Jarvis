"""Búsqueda difusa de un nombre en una lista conocida (enrutador-intenciones.md, sección 4)."""
from collections.abc import Sequence

from rapidfuzz import fuzz

from jarvis_assistant.intent_router.normalizer import normalize

_ARTICLES = ("el", "la", "los", "las", "un", "una")


def _core(text: str) -> str:
    """Texto normalizado sin su artículo inicial: «el editor» y «editor» son lo mismo.

    Sin esto, `WRatio` da por parecidos dos nombres que solo comparten el artículo («el
    resultado» y «el editor»).
    """
    words = normalize(text).split()
    if len(words) > 1 and words[0] in _ARTICLES:
        words = words[1:]
    return " ".join(words)


def best_match(query: str, names: Sequence[str], threshold: float) -> str | None:
    """El elemento de `names` más parecido a `query`, si alcanza el umbral.

    Compara nombres normalizados con `fuzz.WRatio`. A igualdad, gana el primero en orden
    alfabético: el resultado no depende del orden de la lista.
    """
    wanted = _core(query)
    if not wanted:
        return None
    best: tuple[float, str, str] | None = None
    for name in names:
        candidate = _core(name)
        if not candidate:
            continue
        score = fuzz.WRatio(wanted, candidate)
        if score < threshold:
            continue
        key = (-score, candidate, name)
        if best is None or key < best:
            best = key
    return None if best is None else best[2]
