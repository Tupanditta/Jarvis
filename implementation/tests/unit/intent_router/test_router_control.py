"""Frase de activación, frases de control y cierre en reposo (catalogo-intenciones.md)."""
import pytest

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.state_machine import (
    Answer,
    AssistantState,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    IntentMatched,
    NoMatch,
    WakeWord,
)
from jarvis_assistant.intent_router.router import HIDE_SCREEN, SHOW_SCREEN, IntentRouter

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


@pytest.mark.parametrize("text", ["gracias jarvis", "cancelar", "olvidalo", "", "   ", "¿?"])
def test_en_reposo_las_frases_sin_sentido_en_reposo_se_descartan(router, text):
    assert router.route(text, S.IDLE) is None


@pytest.mark.parametrize(
    "text", ["abre el navegador", "qué tiempo hace hoy", "buenas noches", "buenas noches a todos"]
)
def test_en_reposo_un_texto_no_reconocido_despierta(router, text):
    assert router.route(text, S.IDLE) == NoMatch(text)


def test_en_reposo_el_umbral_de_cierre_es_mas_exigente_que_en_escucha():
    router = IntentRouter(RouterSettings(control_threshold=80, idle_closing_threshold=99))
    text = "buenas noches yarvis"
    assert router.route(text, S.LISTENING_COMMAND) == Control(ControlKind.CERRAR)
    assert router.route(text, S.IDLE) == NoMatch(text)


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


# --- Intenciones del núcleo: mostrar y ocultar la pantalla (T-2.7) -------------------------------


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("muestra la pantalla", SHOW_SCREEN),
        ("Muestra la pantalla.", SHOW_SCREEN),
        ("pantalla completa", SHOW_SCREEN),
        ("oculta la pantalla", HIDE_SCREEN),
        ("minimiza la pantalla", HIDE_SCREEN),
        ("ocutla la pantalla", HIDE_SCREEN),
    ],
)
def test_mostrar_y_ocultar_la_pantalla_en_escucha(router, text, intent):
    assert router.route(text, S.LISTENING_COMMAND) == IntentMatched(intent)


@pytest.mark.parametrize(
    ("text", "intent"), [("muestra la pantalla", SHOW_SCREEN), ("oculta la pantalla", HIDE_SCREEN)]
)
def test_en_reposo_mostrar_y_ocultar_la_pantalla_se_reconocen(router, text, intent):
    assert router.route(text, S.IDLE) == IntentMatched(intent)


def test_en_dormido_mostrar_la_pantalla_se_descarta(router):
    assert router.route("muestra la pantalla", S.DORMIDO) is None


def test_mostrar_la_pantalla_no_es_una_respuesta_de_dialogo(router):
    text = "muestra la pantalla"
    assert router.route(text, S.AWAITING_CONFIRMATION) == Answer(valid=False)
