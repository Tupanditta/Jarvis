"""Validación de las respuestas a un diálogo según el tipo esperado (maquina-estados.md,
«Contexto de diálogo»; catalogo-intenciones.md, sección 4).

Las respuestas de sí o no se comparan como frase completa, igual que las frases de control:
«sí, claro que no» no es ni lo uno ni lo otro.
"""
from datetime import UTC, datetime, tzinfo

from rapidfuzz import fuzz

from jarvis_assistant.core.action_api import ExpectedType, ReminderAction
from jarvis_assistant.core.state_machine import Answer
from jarvis_assistant.intent_router import patterns
from jarvis_assistant.intent_router.slots import datetimes, names

# Ya normalizadas: sin tildes.
AFFIRMATIONS = ("si", "vale", "de acuerdo", "confirmo", "adelante", "correcto", "hazlo")
NEGATIONS = ("no", "negativo", "mejor no", "no lo hagas")

# REMINDER_ACTION: lo que termina el diálogo de creación y las dos acciones con su fecha.
REMINDER_DONE = (*NEGATIONS, "nada mas", "listo", "ya esta", "nada")
REMINDER_PREFIXES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("otro", "aviso"), "aviso"),
    (("fecha", "limite"), "limite"),
)

_SHORT = 3  # una frase de 3 caracteres o menos exige coincidencia exacta
_TEXT_EDGES = " .,;:!?¿¡\"'«»"

INVALID = Answer(valid=False)


def validate(
    text: str,
    normalized: str,
    expected: ExpectedType,
    threshold: float,
    *,
    now: datetime | None = None,
    default_hour: int = 9,
    tz: tzinfo | None = None,
) -> Answer:
    """`Answer(value)` si el texto es una respuesta admitida para `expected`; si no,
    `Answer(valid=False)`. `now`, `default_hour` y `tz`: para las fechas."""
    if not normalized:
        return INVALID
    moment = now or datetime.now(UTC)
    match expected:
        case ExpectedType.BOOLEAN:
            return _boolean(normalized, threshold)
        case ExpectedType.NEW_FILENAME:
            try:
                return Answer(names.build(text.strip(_TEXT_EDGES)))
            except names.InvalidNameError:
                return INVALID
        case ExpectedType.DATETIME:
            found = datetimes.parse(normalized.split(), moment, default_hour, tz)
            return INVALID if found is None else Answer(found)
        case ExpectedType.REMINDER_ACTION:
            return _reminder_action(normalized, threshold, moment, default_hour, tz)
    return INVALID


def _boolean(normalized: str, threshold: float) -> Answer:
    best: tuple[float, bool] | None = None
    for phrases, value in ((AFFIRMATIONS, True), (NEGATIONS, False)):
        for phrase in phrases:
            score = _similarity(normalized, phrase)
            if score >= threshold and (best is None or score > best[0]):
                best = (score, value)
    return INVALID if best is None else Answer(best[1])


def _reminder_action(
    normalized: str, threshold: float, now: datetime, default_hour: int, tz: tzinfo | None
) -> Answer:
    """«otro aviso {fecha}», «fecha límite {fecha}» o una frase que termina («no», «listo»)."""
    if any(_similarity(normalized, phrase) >= threshold for phrase in REMINDER_DONE):
        return Answer(False)
    words = normalized.split()
    for prefix, kind in REMINDER_PREFIXES:
        if len(words) <= len(prefix):
            continue
        if patterns.similarity(prefix, words[: len(prefix)]) < threshold:
            continue
        found = datetimes.parse(words[len(prefix) :], now, default_hour, tz)
        if found is not None:
            return Answer(ReminderAction(kind, found))  # type: ignore[arg-type]
    return INVALID


def _similarity(normalized: str, phrase: str) -> float:
    if len(phrase) <= _SHORT or len(normalized) <= _SHORT:
        return 100.0 if normalized == phrase else 0.0
    return fuzz.ratio(normalized, phrase)
