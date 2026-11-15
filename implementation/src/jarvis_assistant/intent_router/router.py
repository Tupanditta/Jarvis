"""Despacho del texto escrito según el estado (enrutador-intenciones.md, sección 1).

Código puro: no ejecuta acciones, no habla y no publica eventos. De momento reconoce la frase
de activación, las frases de control y el cierre en reposo; el registro de módulos, los
patrones y las respuestas de diálogo llegan con las órdenes y con el diálogo.
"""
from collections.abc import Iterable, Mapping

from rapidfuzz import fuzz

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.state_machine import (
    AssistantState,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    Input,
    NoMatch,
    WakeWord,
)
from jarvis_assistant.intent_router.normalizer import normalize

CLOSING_PHRASE = "buenas noches jarvis"

# Frases de activación ya normalizadas.
WAKE_PHRASES: tuple[str, ...] = ("hey jarvis", "jarvis")

# Frases de control ya normalizadas (catalogo-intenciones.md, sección 1).
CONTROL_PHRASES: tuple[tuple[str, ControlKind], ...] = (
    ("gracias jarvis", ControlKind.REPOSO),
    (CLOSING_PHRASE, ControlKind.CERRAR),
    ("cancelar", ControlKind.CANCELAR),
    ("cancela", ControlKind.CANCELAR),
    ("olvidalo", ControlKind.CANCELAR),
    ("dejalo", ControlKind.CANCELAR),
)

_ATTENDING = (
    AssistantState.LISTENING_COMMAND,
    AssistantState.AWAITING_CONFIRMATION,
    AssistantState.AWAITING_PARAMETER,
)


def _best(normalized: str, phrases: Iterable[str]) -> float:
    return max(fuzz.ratio(normalized, phrase) for phrase in phrases)


class IntentRouter:
    def __init__(self, settings: RouterSettings, aliases: Mapping[str, str] | None = None) -> None:
        self._settings = settings
        self._aliases = dict(aliases or {})

    def route(self, text: str, state: AssistantState, dialogue: object = None) -> Input | None:
        """Entrada para la FSM, o None si el texto se descarta sin efecto."""
        normalized = normalize(text, self._aliases)
        if state in _ATTENDING:
            return self._attending(normalized) or NoMatch(text)
        if self._is_wake(normalized):
            return WakeWord()
        if state is AssistantState.IDLE:
            score = fuzz.ratio(normalized, CLOSING_PHRASE)
            if score >= self._settings.idle_closing_threshold:
                return ClosingPhraseInIdle()
        return None

    def _is_wake(self, normalized: str) -> bool:
        return bool(normalized) and _best(normalized, WAKE_PHRASES) >= self._settings.wake_threshold

    def _attending(self, normalized: str) -> Input | None:
        """La frase de control o de activación más parecida a la frase completa, si alcanza
        su umbral. A igual parecido gana la frase de control."""
        if not normalized:
            return None
        score, kind = max(
            ((fuzz.ratio(normalized, phrase), kind) for phrase, kind in CONTROL_PHRASES),
            key=lambda scored: scored[0],
        )
        is_control = score >= self._settings.control_threshold
        wake = _best(normalized, WAKE_PHRASES)
        if wake >= self._settings.wake_threshold and not (is_control and score >= wake):
            return WakeWord()
        return Control(kind) if is_control else None
