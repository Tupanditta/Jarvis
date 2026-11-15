"""Despacho del texto escrito según el estado (enrutador-intenciones.md, sección 1).

Código puro: no ejecuta acciones, no habla y no publica eventos. De momento reconoce la frase
de activación, las frases de control, el cierre en reposo y las intenciones del núcleo para
mostrar y ocultar la pantalla. En reposo, cualquier otro texto se atiende como orden: la FSM
despierta en silencio. El registro de módulos, los patrones y las respuestas de diálogo llegan
con las órdenes y con el diálogo.
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
    IntentMatched,
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

SHOW_SCREEN = "nucleo.mostrar_pantalla"
HIDE_SCREEN = "nucleo.ocultar_pantalla"

# Intenciones del núcleo sin entidades (catalogo-intenciones.md, sección 2), ya normalizadas.
CORE_PHRASES: tuple[tuple[str, str], ...] = (
    ("muestra la pantalla", SHOW_SCREEN),
    ("pantalla completa", SHOW_SCREEN),
    ("oculta la pantalla", HIDE_SCREEN),
    ("minimiza la pantalla", HIDE_SCREEN),
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
            entry = self._attending(normalized)
            if entry is None and state is AssistantState.LISTENING_COMMAND:
                entry = self._core_intent(normalized)
            return entry or NoMatch(text)
        if self._is_wake(normalized):
            return WakeWord()
        if state is AssistantState.IDLE:
            return self._resting(text, normalized)
        return None

    def _resting(self, text: str, normalized: str) -> Input | None:
        """En reposo, cualquier texto despierta y se atiende como orden. El cierre exige su
        umbral de reposo; las frases de control sin sentido en reposo se descartan."""
        if fuzz.ratio(normalized, CLOSING_PHRASE) >= self._settings.idle_closing_threshold:
            return ClosingPhraseInIdle()
        if not normalized:
            return None
        control = self._attending(normalized)
        if isinstance(control, Control) and control.kind is not ControlKind.CERRAR:
            return None
        return self._core_intent(normalized) or NoMatch(text)

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

    def _core_intent(self, normalized: str) -> Input | None:
        if not normalized:
            return None
        score, intent = max(
            ((fuzz.ratio(normalized, phrase), intent) for phrase, intent in CORE_PHRASES),
            key=lambda scored: scored[0],
        )
        return IntentMatched(intent) if score >= self._settings.intent_threshold else None
