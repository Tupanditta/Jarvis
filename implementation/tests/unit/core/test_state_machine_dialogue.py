"""Una prueba por fila de diálogo de la tabla de transiciones (maquina-estados.md, T-4.1)."""
import pytest

from jarvis_assistant.core.action_api import ExpectedType, Phrase
from jarvis_assistant.core.state_machine import (
    Answer,
    AssistantState,
    CancelDialogue,
    CancelTurn,
    CloseSession,
    Control,
    ControlKind,
    DialogueContext,
    DialogueRequested,
    DialogueTimeout,
    ExitProcess,
    IntentMatched,
    NoMatch,
    NoticeReady,
    OpenDialogue,
    RejectDialogue,
    RepeatQuestion,
    ResolveDialogue,
    RestartDialogueTimer,
    SayLifecycle,
    ShutdownRequested,
    SilenceTimeout,
    StateMachine,
    Transition,
    WakeWord,
)

S = AssistantState
AWAITING = (S.AWAITING_CONFIRMATION, S.AWAITING_PARAMETER)


def question(expected: ExpectedType = ExpectedType.BOOLEAN) -> DialogueContext:
    return DialogueContext(Phrase("historial.confirmar_eliminar"), expected)


def awaiting(expected: ExpectedType = ExpectedType.BOOLEAN) -> tuple[StateMachine, DialogueContext]:
    fsm = StateMachine(S.LISTENING_COMMAND)
    dialogue = question(expected)
    fsm.handle(DialogueRequested(dialogue))
    return fsm, dialogue


def test_escucha_con_una_pregunta_de_si_o_no_espera_confirmacion():
    fsm = StateMachine(S.LISTENING_COMMAND)
    dialogue = question(ExpectedType.BOOLEAN)
    assert fsm.handle(DialogueRequested(dialogue)) == [OpenDialogue(dialogue)]
    assert fsm.state is S.AWAITING_CONFIRMATION
    assert fsm.dialogue is dialogue


@pytest.mark.parametrize(
    "expected", [ExpectedType.NEW_FILENAME, ExpectedType.DATETIME, ExpectedType.REMINDER_ACTION]
)
def test_escucha_con_una_pregunta_de_un_dato_espera_el_parametro(expected):
    fsm = StateMachine(S.LISTENING_COMMAND)
    dialogue = question(expected)
    assert fsm.handle(DialogueRequested(dialogue)) == [OpenDialogue(dialogue)]
    assert fsm.state is S.AWAITING_PARAMETER


@pytest.mark.parametrize("expected", [ExpectedType.BOOLEAN, ExpectedType.NEW_FILENAME])
def test_una_respuesta_valida_resuelve_el_dialogo_y_vuelve_a_escucha(expected):
    fsm, _dialogue = awaiting(expected)
    assert fsm.handle(Answer("notas.txt")) == [ResolveDialogue("notas.txt")]
    assert fsm.state is S.LISTENING_COMMAND
    assert fsm.dialogue is None


def test_una_negacion_es_una_respuesta_no_una_cancelacion():
    fsm, _dialogue = awaiting()
    assert fsm.handle(Answer(False)) == [ResolveDialogue(False)]
    assert fsm.state is S.LISTENING_COMMAND


def test_la_primera_respuesta_no_valida_repite_la_pregunta():
    fsm, dialogue = awaiting()
    assert fsm.handle(Answer(valid=False)) == [RepeatQuestion()]
    assert fsm.state is S.AWAITING_CONFIRMATION
    assert dialogue.attempts == 1


def test_la_segunda_respuesta_no_valida_cancela():
    fsm, _dialogue = awaiting()
    fsm.handle(Answer(valid=False))
    assert fsm.handle(Answer(valid=False)) == [CancelDialogue(announce=True)]
    assert fsm.state is S.LISTENING_COMMAND


def test_una_respuesta_valida_tras_una_no_valida_resuelve():
    fsm, _dialogue = awaiting()
    fsm.handle(Answer(valid=False))
    assert fsm.handle(Answer(True)) == [ResolveDialogue(True)]


def test_cada_pregunta_empieza_sin_intentos():
    fsm, _dialogue = awaiting()
    fsm.handle(Answer(valid=False))
    fsm.handle(Answer(True))
    second = question()
    second.attempts = 5
    fsm.handle(DialogueRequested(second))
    assert fsm.handle(Answer(valid=False)) == [RepeatQuestion()]


@pytest.mark.parametrize("entry", [DialogueTimeout(), Control(ControlKind.CANCELAR)])
def test_tiempo_agotado_o_cancelar_cancela_el_dialogo(entry):
    fsm, _dialogue = awaiting(ExpectedType.NEW_FILENAME)
    assert fsm.handle(entry) == [CancelDialogue(announce=True)]
    assert fsm.state is S.LISTENING_COMMAND
    assert fsm.dialogue is None


def test_hey_jarvis_reinicia_el_tiempo_de_espera_sin_voz():
    fsm, dialogue = awaiting()
    assert fsm.handle(WakeWord()) == [RestartDialogueTimer()]
    assert fsm.state is S.AWAITING_CONFIRMATION
    assert fsm.dialogue is dialogue


def test_gracias_jarvis_cancela_el_dialogo_y_el_turno_y_pasa_a_reposo():
    fsm, _dialogue = awaiting()
    assert fsm.handle(Control(ControlKind.REPOSO)) == [
        CancelDialogue(announce=False),
        CancelTurn(announce=False),
        SayLifecycle("ciclo.reposo", Transition.REST_ENTERED),
    ]
    assert fsm.state is S.IDLE
    assert fsm.dialogue is None


def test_buenas_noches_en_espera_cierra_la_sesion():
    fsm, _dialogue = awaiting()
    assert fsm.handle(Control(ControlKind.CERRAR)) == [CloseSession(reason="voz")]
    assert fsm.state is S.DORMIDO
    assert fsm.dialogue is None


def test_salir_en_espera_cierra_sin_frase_y_termina():
    fsm, _dialogue = awaiting()
    assert fsm.handle(ShutdownRequested()) == [
        CloseSession(reason="salida", silent=True), ExitProcess(),
    ]  # fmt: skip
    assert fsm.dialogue is None


@pytest.mark.parametrize(
    "entry",
    [NoticeReady("aviso"), NoticeReady("aviso", reminder=True), SilenceTimeout(),
     IntentMatched("orden"), NoMatch("hola")],
)  # fmt: skip
@pytest.mark.parametrize("expected", [ExpectedType.BOOLEAN, ExpectedType.NEW_FILENAME])
def test_en_espera_los_avisos_esperan_y_no_se_atienden_ordenes(entry, expected):
    fsm, dialogue = awaiting(expected)
    before = fsm.state
    assert fsm.handle(entry) == []
    assert fsm.state is before and fsm.dialogue is dialogue


def test_en_espera_una_segunda_pregunta_se_rechaza():
    fsm, dialogue = awaiting()
    other = question()
    assert fsm.handle(DialogueRequested(other)) == [RejectDialogue(other)]
    assert fsm.dialogue is dialogue


@pytest.mark.parametrize("state", [S.DORMIDO, S.IDLE])
def test_sin_escucha_una_pregunta_se_rechaza(state):
    fsm = StateMachine(state)
    dialogue = question()
    assert fsm.handle(DialogueRequested(dialogue)) == [RejectDialogue(dialogue)]
    assert fsm.state is state


@pytest.mark.parametrize("state", AWAITING)
def test_una_respuesta_sin_pregunta_en_curso_cancela(state):
    """Estado de partida forzado: la FSM no tiene pregunta que repetir."""
    fsm = StateMachine(state)
    assert fsm.handle(Answer(valid=False)) == [CancelDialogue(announce=True)]
    assert fsm.state is S.LISTENING_COMMAND
