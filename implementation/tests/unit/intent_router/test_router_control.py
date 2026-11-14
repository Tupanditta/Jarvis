"""Frases de control y cierre en reposo (catalogo-intenciones.md, secciones 1 y 6)."""
import pytest

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.state_machine import (
    AssistantState,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    NoMatch,
)
from jarvis_assistant.intent_router.router import IntentRouter

S = AssistantState
ATTENDING = (S.LISTENING_COMMAND, S.AWAITING_CONFIRMATION, S.AWAITING_PARAMETER)

NEGATIVE_CONTROLS = [
    "muchas gracias jarvis por todo",
    "jarvis",
    "buenas noches",
    "qué tiempo hace hoy",
    "hey jarvis",
    "abre",
]


@pytest.fixture
def router():
    return IntentRouter(RouterSettings())


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("gracias jarvis", ControlKind.REPOSO),
        ("Gracias, Jarvis.", ControlKind.REPOSO),
        ("grasias jarvis", ControlKind.REPOSO),
        ("buenas noches jarvis", ControlKind.CERRAR),
        ("Buenas noches, Jarvis.", ControlKind.CERRAR),
        ("cancelar", ControlKind.CANCELAR),
        ("Cancela.", ControlKind.CANCELAR),
        ("Olvídalo", ControlKind.CANCELAR),
        ("déjalo", ControlKind.CANCELAR),
    ],
)
@pytest.mark.parametrize("state", ATTENDING)
def test_frases_de_control_en_escucha_y_en_espera(router, state, text, kind):
    assert router.route(text, state) == Control(kind)


@pytest.mark.parametrize("text", NEGATIVE_CONTROLS)
def test_controles_negativos_en_escucha_no_son_frases_de_control(router, text):
    assert router.route(text, S.LISTENING_COMMAND) == NoMatch(text)


@pytest.mark.parametrize("text", ["", "   ", "¿?"])
def test_texto_vacio_no_coincide(router, text):
    assert router.route(text, S.LISTENING_COMMAND) == NoMatch(text)


@pytest.mark.parametrize("text", ["buenas noches jarvis", "Buenas noches, Jarvis."])
def test_en_reposo_solo_vale_la_frase_de_cierre(router, text):
    assert router.route(text, S.IDLE) == ClosingPhraseInIdle()


@pytest.mark.parametrize(
    "text", [*NEGATIVE_CONTROLS, "gracias jarvis", "cancelar", "buenas noches a todos", ""]
)
def test_en_reposo_cualquier_otra_frase_se_descarta(router, text):
    assert router.route(text, S.IDLE) is None


def test_en_reposo_el_umbral_es_mas_exigente_que_en_escucha():
    router = IntentRouter(RouterSettings(control_threshold=80, idle_closing_threshold=99))
    text = "buenas noches yarvis"
    assert router.route(text, S.LISTENING_COMMAND) == Control(ControlKind.CERRAR)
    assert router.route(text, S.IDLE) is None


def test_en_dormido_no_se_enruta_nada(router):
    assert router.route("buenas noches jarvis", S.DORMIDO) is None


def test_los_alias_se_aplican_antes_de_comparar():
    router = IntentRouter(RouterSettings(), aliases={"yarbis": "jarvis"})
    assert router.route("gracias yarbis", S.LISTENING_COMMAND) == Control(ControlKind.REPOSO)


def test_misma_entrada_misma_salida_en_mil_repeticiones(router):
    results = {router.route("grasias jarvis", S.LISTENING_COMMAND) for _ in range(1000)}
    assert results == {Control(ControlKind.REPOSO)}
