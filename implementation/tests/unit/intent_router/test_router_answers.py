"""Respuestas a un diálogo: validación por tipo en el enrutador (T-4.1; catalogo-intenciones.md,
sección 4)."""
from pathlib import Path

import pytest

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.action_api import ExpectedType, IntentSpec, Phrase, Slot, SlotType
from jarvis_assistant.core.state_machine import (
    Answer,
    AssistantState,
    Control,
    ControlKind,
    DialogueContext,
    WakeWord,
)
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router.router import IntentRouter

S = AssistantState


def dialogue(expected: ExpectedType) -> DialogueContext:
    return DialogueContext(Phrase("historial.confirmar_eliminar"), expected)


@pytest.fixture
def router():
    return IntentRouter(RouterSettings())


YES = ["sí", "Sí.", "si", "vale", "Vale", "de acuerdo", "confirmo", "adelante", "correcto",
       "hazlo", "Hazlo."]  # fmt: skip
NO = ["no", "No.", "negativo", "mejor no", "no lo hagas"]
NEITHER = ["quizá", "sí, claro que no", "abre GitHub", "muestra la pantalla", "sin", "o"]


@pytest.mark.parametrize("text", YES)
def test_una_afirmacion_es_verdadero(router, text):
    assert router.route(text, S.AWAITING_CONFIRMATION, dialogue(ExpectedType.BOOLEAN)) == (
        Answer(True)
    )


@pytest.mark.parametrize("text", NO)
def test_una_negacion_es_falso_no_una_cancelacion(router, text):
    assert router.route(text, S.AWAITING_CONFIRMATION, dialogue(ExpectedType.BOOLEAN)) == (
        Answer(False)
    )


@pytest.mark.parametrize("text", NEITHER)
def test_lo_que_no_es_si_ni_no_no_es_valido(router, text):
    assert router.route(text, S.AWAITING_CONFIRMATION, dialogue(ExpectedType.BOOLEAN)) == (
        Answer(valid=False)
    )


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("notas dos punto txt", "notas dos.txt"),
        ("informe", "informe"),
        ("mi guion bajo archivo punto md", "mi_archivo.md"),
        ("abre GitHub", "abre GitHub"),  # en espera nunca es una orden
    ],
)
def test_un_nombre_nuevo_se_construye(router, text, name):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.NEW_FILENAME))
    assert entry == Answer(name)


@pytest.mark.parametrize("text", ["con", "a:b", "punto"])
def test_un_nombre_no_valido_no_es_una_respuesta(router, text):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.NEW_FILENAME))
    assert entry == Answer(valid=False)


@pytest.mark.parametrize(
    ("text", "ids"),
    [
        ("1, 3, 5", (1, 3, 5)),
        ("1,3,5", (1, 3, 5)),
        ("5, 1, 3, 3", (1, 3, 5)),
        ("1-5", (1, 2, 3, 4, 5)),
        ("2 - 4", (2, 3, 4)),
        ("1-3, 7", (1, 2, 3, 7)),
        ("4", (4,)),
        ("1 3 5", (1, 3, 5)),
        ("las sesiones 1 y 3", (1, 3)),
        ("uno, tres y cinco", (1, 3, 5)),
        ("treinta y dos", (32,)),
        ("1, 3,", (1, 3)),
    ],
)
def test_ids_de_sesion_separados_por_comas_o_en_intervalo(router, text, ids):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.SESSION_IDS))
    assert entry == Answer(ids)


@pytest.mark.parametrize("text", ["sí", "todas", "5-1", "1-2-3", "-3", "1, x", ",", "1-5000"])
def test_lo_que_no_son_ids_de_sesion_no_es_una_respuesta(router, text):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.SESSION_IDS))
    assert entry == Answer(valid=False)


@pytest.mark.parametrize("expected", list(ExpectedType))
def test_las_frases_de_control_y_la_de_activacion_valen_en_cualquier_dialogo(router, expected):
    state = S.AWAITING_CONFIRMATION if expected is ExpectedType.BOOLEAN else S.AWAITING_PARAMETER
    ask = dialogue(expected)
    assert router.route("cancelar", state, ask) == Control(ControlKind.CANCELAR)
    assert router.route("gracias jarvis", state, ask) == Control(ControlKind.REPOSO)
    assert router.route("buenas noches jarvis", state, ask) == Control(ControlKind.CERRAR)
    assert router.route("hey jarvis", state, ask) == WakeWord()


def test_sin_pregunta_en_curso_la_respuesta_no_es_valida(router):
    assert router.route("sí", S.AWAITING_CONFIRMATION, None) == Answer(valid=False)


# --- Candidatos de una misma acción ----------------------------------------------------------


class Creator:
    name = "creador"
    title = "Creador"

    def intents(self):
        slots = (Slot("nombre", SlotType.NEW_NAME), Slot("ruta", SlotType.DIR_PATH, optional=True))
        return (
            IntentSpec("crear", ("crea el archivo {nombre}", "crea el archivo {nombre} en {ruta}"),
                       slots),
        )  # fmt: skip


def test_una_ruta_que_no_existe_no_se_lee_como_parte_del_nombre(tmp_path: Path):
    """CU-09 A5: otro patrón de la misma acción no se prueba como alternativa."""
    router = IntentRouter(RouterSettings(), workdir=Workdir(tmp_path))
    router.register(Creator())
    intent = router.route("crea el archivo notas en fotos", S.LISTENING_COMMAND).intent
    assert intent.error == Phrase("ruta.no_existe", {"nombre": "fotos"})


def test_con_la_ruta_existente_se_usa_el_patron_con_ruta(tmp_path: Path):
    (tmp_path / "fotos").mkdir()
    router = IntentRouter(RouterSettings(), workdir=Workdir(tmp_path))
    router.register(Creator())
    intent = router.route("crea el archivo notas en fotos", S.LISTENING_COMMAND).intent
    assert intent.error is None
    assert intent.params == {"nombre": "notas", "ruta": tmp_path / "fotos"}
