"""Validación de las respuestas a un diálogo según el tipo esperado (maquina-estados.md,
«Contexto de diálogo»; catalogo-intenciones.md, sección 4).

Las respuestas de sí o no se comparan como frase completa, igual que las frases de control:
«sí, claro que no» no es ni lo uno ni lo otro.
"""
from rapidfuzz import fuzz

from jarvis_assistant.core.action_api import ExpectedType
from jarvis_assistant.core.state_machine import Answer
from jarvis_assistant.intent_router.slots import names

# Ya normalizadas: sin tildes.
AFFIRMATIONS = ("si", "vale", "de acuerdo", "confirmo", "adelante", "correcto", "hazlo")
NEGATIONS = ("no", "negativo", "mejor no", "no lo hagas")

_SHORT = 3  # una frase de 3 caracteres o menos exige coincidencia exacta
_TEXT_EDGES = " .,;:!?¿¡\"'«»"

INVALID = Answer(valid=False)


def validate(text: str, normalized: str, expected: ExpectedType, threshold: float) -> Answer:
    """`Answer(value)` si el texto es una respuesta admitida para `expected`; si no,
    `Answer(valid=False)`."""
    if not normalized:
        return INVALID
    match expected:
        case ExpectedType.BOOLEAN:
            return _boolean(normalized, threshold)
        case ExpectedType.NEW_FILENAME:
            try:
                return Answer(names.build(text.strip(_TEXT_EDGES)))
            except names.InvalidNameError:
                return INVALID
    # DATETIME y REMINDER_ACTION llegan con Recordatorios.
    return INVALID


def _boolean(normalized: str, threshold: float) -> Answer:
    best: tuple[float, bool] | None = None
    for phrases, value in ((AFFIRMATIONS, True), (NEGATIONS, False)):
        for phrase in phrases:
            score = _similarity(normalized, phrase)
            if score >= threshold and (best is None or score > best[0]):
                best = (score, value)
    return INVALID if best is None else Answer(best[1])


def _similarity(normalized: str, phrase: str) -> float:
    if len(phrase) <= _SHORT or len(normalized) <= _SHORT:
        return 100.0 if normalized == phrase else 0.0
    return fuzz.ratio(normalized, phrase)
