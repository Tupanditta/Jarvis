"""Interfaz común de los módulos de acción (arquitectura.md, sección 5).

De momento solo contiene `Phrase`, que ya usa el sintetizador; el resto del contrato llega
con el primer módulo de acción.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Phrase:
    """Frase del catálogo `speaker/phrases.py` con sus parámetros."""

    id: str
    params: Mapping[str, object] = field(default_factory=dict)
