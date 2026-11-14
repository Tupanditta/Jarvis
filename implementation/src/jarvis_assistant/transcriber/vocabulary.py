"""Indicación inicial de vocabulario del transcriptor (transcriptor.md, AD-17).

Funciones puras: los mismos términos de entrada dan siempre el mismo texto.
"""
from collections.abc import Iterable, Sequence
from pathlib import Path

FIXED_TERMS = ("Jarvis", "Gracias Jarvis", "Buenas noches Jarvis")


def workdir_entries(workdir: Path, limit: int) -> list[str]:
    """Nombres del directorio de trabajo: carpetas primero, orden alfabético, sin ocultos."""
    try:
        entries = [entry for entry in workdir.iterdir() if not entry.name.startswith(".")]
    except OSError:
        return []
    entries.sort(key=lambda entry: (not entry.is_dir(), entry.name.casefold()))
    return [entry.name for entry in entries[:limit]]


def build_terms(
    *,
    dialogue: Iterable[str] = (),
    workdir: Iterable[str] = (),
    protocols: Iterable[str] = (),
    places: Iterable[str] = (),
    catalog: Iterable[str] = (),
    binaries: Iterable[str] = (),
    discovered: Iterable[str] = (),
) -> tuple[str, ...]:
    """Términos en orden de prioridad, sin repetidos ni vacíos."""
    seen: set[str] = set()
    terms: list[str] = []
    groups = (FIXED_TERMS, dialogue, workdir, protocols, places, catalog, binaries, discovered)
    for group in groups:
        for term in group:
            cleaned = " ".join(term.split())
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                terms.append(cleaned)
    return tuple(terms)


def render_prompt(terms: Sequence[str], max_chars: int) -> str:
    """Une los términos con comas; si no caben, se pierden los últimos (menor prioridad)."""
    prompt = ""
    for term in terms:
        candidate = f"{prompt}, {term}" if prompt else term
        if len(candidate) > max_chars:
            break
        prompt = candidate
    return prompt
