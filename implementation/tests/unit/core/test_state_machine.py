"""Una prueba por fila, no de diálogo, de la tabla de transiciones (maquina-estados.md)."""
import pytest

from jarvis_assistant.core.state_machine import (
    AssistantState,
    CancelTurn,
    CloseSession,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    DeliverNotice,
    DeliverPendingNotices,
    ExitProcess,
    IntentMatched,
    LoadTranscriber,
    NoMatch,
    NoticeReady,
    OpenSession,
    OpenSessionRequested,
    PublishListeningResumed,
    PublishUnrecognized,
    RestartSilenceTimer,
    RunTurn,
    SayLifecycle,
    ShutdownRequested,
    SilenceTimeout,
    StateMachine,
    StopInterruptibleSpeech,
    Transition,
    WakeWord,
)

S = AssistantState
WITH_SESSION = (S.IDLE, S.LISTENING_COMMAND, S.AWAITING_CONFIRMATION, S.AWAITING_PARAMETER)


def machine(state: AssistantState) -> StateMachine:
    return StateMachine(state)


def test_el_estado_inicial_es_dormido():
    assert StateMachine().state is S.DORMIDO


def test_dormido_con_hey_jarvis_abre_sesion_y_escucha():
    fsm = machine(S.DORMIDO)
    effects = fsm.handle(WakeWord())
    assert fsm.state is S.LISTENING_COMMAND
    assert effects == [
        OpenSession(),
        LoadTranscriber(),
        SayLifecycle("ciclo.apertura", Transition.SESSION_OPENED),
        DeliverPendingNotices(),
        RestartSilenceTimer(),
    ]


def test_abrir_sesion_desde_la_bandeja_equivale_a_hey_jarvis_en_dormido():
    fsm = machine(S.DORMIDO)
    assert fsm.handle(OpenSessionRequested()) == machine(S.DORMIDO).handle(WakeWord())
    assert fsm.state is S.LISTENING_COMMAND


@pytest.mark.parametrize("state", WITH_SESSION)
def test_abrir_sesion_desde_la_bandeja_no_hace_nada_con_sesion(state):
    fsm = machine(state)
    assert fsm.handle(OpenSessionRequested()) == []
    assert fsm.state is state


@pytest.mark.parametrize(
    "entry",
    [
        Control(ControlKind.REPOSO),
        Control(ControlKind.CERRAR),
        Control(ControlKind.CANCELAR),
        NoMatch("jarvis"),
        IntentMatched(object()),
        ClosingPhraseInIdle(),
        SilenceTimeout(),
        NoticeReady(object(), reminder=True),
    ],
)
def test_dormido_ignora_cualquier_otra_entrada(entry):
    fsm = machine(S.DORMIDO)
    assert fsm.handle(entry) == []
    assert fsm.state is S.DORMIDO


def test_reposo_con_hey_jarvis_vuelve_a_escucha():
    fsm = machine(S.IDLE)
    effects = fsm.handle(WakeWord())
    assert fsm.state is S.LISTENING_COMMAND
    assert effects == [
        SayLifecycle("ciclo.escucha", Transition.LISTENING_RESUMED),
        RestartSilenceTimer(),
    ]


def test_reposo_con_la_frase_de_cierre_cierra_la_sesion():
    fsm = machine(S.IDLE)
    assert fsm.handle(ClosingPhraseInIdle()) == [CloseSession(reason="voz", silent=False)]
    assert fsm.state is S.DORMIDO


def test_reposo_con_aviso_de_recordatorio_pasa_a_escucha_sin_frase():
    notice = object()
    fsm = machine(S.IDLE)
    effects = fsm.handle(NoticeReady(notice, reminder=True))
    assert fsm.state is S.LISTENING_COMMAND
    assert effects == [
        PublishListeningResumed(silent=True),
        DeliverNotice(notice),
        RestartSilenceTimer(),
    ]


def test_reposo_ignora_gracias_jarvis_y_el_silencio():
    fsm = machine(S.IDLE)
    assert fsm.handle(Control(ControlKind.REPOSO)) == []
    assert fsm.handle(SilenceTimeout()) == []
    assert fsm.state is S.IDLE


def test_escucha_con_intencion_ejecuta_el_turno():
    intent = object()
    fsm = machine(S.LISTENING_COMMAND)
    assert fsm.handle(IntentMatched(intent)) == [RunTurn(intent)]
    assert fsm.state is S.LISTENING_COMMAND


def test_escucha_con_frase_no_reconocida_la_publica_y_reinicia_la_cuenta():
    fsm = machine(S.LISTENING_COMMAND)
    assert fsm.handle(NoMatch("qué tiempo hace")) == [
        PublishUnrecognized("qué tiempo hace"),
        RestartSilenceTimer(),
    ]
    assert fsm.state is S.LISTENING_COMMAND


def test_escucha_con_hey_jarvis_calla_y_reinicia_la_cuenta_sin_frase():
    fsm = machine(S.LISTENING_COMMAND)
    assert fsm.handle(WakeWord()) == [StopInterruptibleSpeech(), RestartSilenceTimer()]
    assert fsm.state is S.LISTENING_COMMAND


def test_escucha_con_cancelar_cancela_el_turno_en_curso():
    fsm = machine(S.LISTENING_COMMAND)
    assert fsm.handle(Control(ControlKind.CANCELAR)) == [CancelTurn(announce=True)]
    assert fsm.state is S.LISTENING_COMMAND


@pytest.mark.parametrize("entry", [Control(ControlKind.REPOSO), SilenceTimeout()])
def test_escucha_pasa_a_reposo_con_gracias_jarvis_o_con_el_silencio(entry):
    fsm = machine(S.LISTENING_COMMAND)
    effects = fsm.handle(entry)
    assert fsm.state is S.IDLE
    assert effects == [
        CancelTurn(announce=False),
        SayLifecycle("ciclo.reposo", Transition.REST_ENTERED),
    ]


@pytest.mark.parametrize("state", WITH_SESSION)
def test_con_sesion_buenas_noches_la_cierra(state):
    fsm = machine(state)
    assert fsm.handle(Control(ControlKind.CERRAR)) == [CloseSession(reason="voz", silent=False)]
    assert fsm.state is S.DORMIDO


@pytest.mark.parametrize("state", (S.LISTENING_COMMAND, S.AWAITING_CONFIRMATION))
def test_con_sesion_un_aviso_espera_en_la_cola(state):
    fsm = machine(state)
    assert fsm.handle(NoticeReady(object(), reminder=True)) == []
    assert fsm.state is state


def test_reposo_un_aviso_que_no_es_de_recordatorio_espera_en_la_cola():
    fsm = machine(S.IDLE)
    assert fsm.handle(NoticeReady(object(), reminder=False)) == []
    assert fsm.state is S.IDLE


@pytest.mark.parametrize("state", WITH_SESSION)
def test_con_sesion_salir_la_cierra_sin_frase_y_termina(state):
    fsm = machine(state)
    assert fsm.handle(ShutdownRequested()) == [
        CloseSession(reason="salida", silent=True),
        ExitProcess(),
    ]
    assert fsm.state is S.DORMIDO


def test_dormido_salir_termina_el_proceso():
    fsm = machine(S.DORMIDO)
    assert fsm.handle(ShutdownRequested()) == [ExitProcess()]
    assert fsm.state is S.DORMIDO


def test_tras_cerrar_hey_jarvis_abre_una_sesion_nueva():
    fsm = machine(S.LISTENING_COMMAND)
    fsm.handle(Control(ControlKind.CERRAR))
    assert fsm.handle(WakeWord())[0] == OpenSession()
    assert fsm.state is S.LISTENING_COMMAND
