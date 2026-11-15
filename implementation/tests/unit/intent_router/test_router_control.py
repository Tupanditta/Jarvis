"""Frase de activación, frases de control y cierre en reposo (catalogo-intenciones.md)."""
import pytest

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.state_machine import (
    AssistantState,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    NoMatch,
    WakeWord,
)
from jarvis_assistant.intent_router.router import IntentRouter

S = AssistantState
ATTENDING = (S.LISTENING_COMMAND, S.AWAITING_CONFIRMATION, S.AWAITING_PARAMETER)

NEGATIVE_CONTROLS = [
    "muchas gracias jarvis por todo",
    "buenas noches",
    "qué tiempo hace hoy",
    "abre",
    "jarvis abre el navegador",
]

WAKE_TEXTS = [
    "hey jarvis", "Hey Jarvis", "Hey, Jarvis.", "hey jarbis", "ey jarvis", "jarvis", "Jarvis",
]  # fmt: skip


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


@pytest.mark.parametrize("text", WAKE_TEXTS)
@pytest.mark.parametrize("state", [S.DORMIDO, S.IDLE, *ATTENDING])
def test_la_frase_de_activacion_se_reconoce_en_todos_los_estados(router, state, text):
    assert router.route(text, state) == WakeWord()


@pytest.mark.parametrize(
    "text", [*NEGATIVE_CONTROLS, "gracias jarvis", "buenas noches jarvis", "cancelar", "hola", ""]
)
def test_en_dormido_solo_vale_la_frase_de_activacion(router, text):
    assert router.route(text, S.DORMIDO) is None


def test_el_umbral_de_activacion_es_configurable():
    strict = IntentRouter(RouterSettings(wake_threshold=100))
    assert strict.route("hey jarbis", S.DORMIDO) is None
    assert strict.route("hey jarbis", S.LISTENING_COMMAND) == NoMatch("hey jarbis")
    assert strict.route("hey jarvis", S.DORMIDO) == WakeWord()


def test_en_escucha_una_frase_de_control_no_se_confunde_con_la_activacion():
    loose = IntentRouter(RouterSettings(wake_threshold=50, control_threshold=80))
    assert loose.route("gracias jarvis", S.LISTENING_COMMAND) == Control(ControlKind.REPOSO)


def test_los_alias_se_aplican_antes_de_comparar():
    router = IntentRouter(RouterSettings(), aliases={"yarbis": "jarvis"})
    assert router.route("gracias yarbis", S.LISTENING_COMMAND) == Control(ControlKind.REPOSO)


def test_misma_entrada_misma_salida_en_mil_repeticiones(router):
    results = {router.route("grasias jarvis", S.LISTENING_COMMAND) for _ in range(1000)}
    assert results == {Control(ControlKind.REPOSO)}
