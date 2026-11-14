"""Despacho del texto transcrito según el estado (enrutador-intenciones.md, sección 1).

Código puro: no ejecuta acciones, no habla y no publica eventos. De momento reconoce las
frases de control y el cierre en reposo; el registro de módulos, los patrones y las
respuestas de diálogo llegan con las órdenes y con el diálogo.
"""
from collections.abc import Mapping

from rapidfuzz import fuzz

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.state_machine import (
    AssistantState,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    Input,
    NoMatch,
)
from jarvis_assistant.intent_router.normalizer import normalize

CLOSING_PHRASE = "buenas noches jarvis"

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


class IntentRouter:
    def __init__(self, settings: RouterSettings, aliases: Mapping[str, str] | None = None) -> None:
        self._settings = settings
        self._aliases = dict(aliases or {})

    def route(self, text: str, state: AssistantState, dialogue: object = None) -> Input | None:
        """Entrada para la FSM, o None si el texto se descarta sin efecto."""
        normalized = normalize(text, self._aliases)
        if state in _ATTENDING:
            return self._control(normalized) or NoMatch(text)
        if state is AssistantState.IDLE:
            score = fuzz.ratio(normalized, CLOSING_PHRASE)
            if score >= self._settings.idle_closing_threshold:
                return ClosingPhraseInIdle()
        return None

    def _control(self, normalized: str) -> Control | None:
        """La frase de control más parecida a la frase completa, si alcanza el umbral."""
        if not normalized:
            return None
        score, kind = max(
            ((fuzz.ratio(normalized, phrase), kind) for phrase, kind in CONTROL_PHRASES),
            key=lambda scored: scored[0],
        )
        return Control(kind) if score >= self._settings.control_threshold else None
