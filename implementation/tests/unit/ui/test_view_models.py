"""Cada modelo de vista refleja sus eventos (hud.md, criterios de aceptación)."""
from datetime import datetime

import pytest
from PySide6.QtCore import Qt

from jarvis_assistant.config import UiSettings
from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity
from jarvis_assistant.ui.view_models import (
    PLACEHOLDER_ASLEEP,
    PLACEHOLDER_ATTENDING,
    PLACEHOLDER_RESTING,
    AssistantModel,
    DialogueModel,
    HudModel,
    TaskListModel,
    UiOptions,
)


def activity(value: Activity, state: str = "LISTENING_COMMAND"):
    return events.AssistantActivityChanged(state, value)


def task(task_id, status="pendiente", *, parent=None, description="git status", detail=None):
    at = datetime(2026, 11, 14, 18, 30 + task_id)
    return events.TaskUpdated(task_id, parent, "comandos", description, status, detail, at)


# --- Asistente -----------------------------------------------------------------------------------


def test_estado_actividad_y_texto_de_ayuda_siguen_al_estado(qtbot):
    model = AssistantModel()
    assert (model.state, model.activity, model.stateText) == ("DORMIDO", "dormido", "Dormido")
    assert model.placeholder == PLACEHOLDER_ASLEEP
    with qtbot.waitSignal(model.stateChanged):
        model.apply(activity(Activity.HABLANDO))
    assert (model.activity, model.stateText) == ("hablando", "Hablando")
    assert model.placeholder == PLACEHOLDER_ATTENDING
    model.apply(activity(Activity.ESPERANDO, "AWAITING_CONFIRMATION"))
    assert model.placeholder == PLACEHOLDER_ATTENDING
    model.apply(activity(Activity.REPOSO, "IDLE"))
    assert (model.stateText, model.placeholder) == ("En reposo", PLACEHOLDER_RESTING)
    model.apply(activity(Activity.DORMIDO, "DORMIDO"))
    assert model.placeholder == PLACEHOLDER_ASLEEP


def test_sesion_nombre_e_importancia(qtbot):
    model = AssistantModel()
    assert not model.sessionOpen
    with qtbot.waitSignal(model.sessionChanged):
        model.apply(events.SessionOpened(7, "2026-11-14"))
    assert (model.sessionOpen, model.sessionName, model.sessionImportant) == (
        True, "2026-11-14", False,
    )  # fmt: skip
    model.apply(events.SessionChanged(7, "prácticas", True))
    assert (model.sessionName, model.sessionImportant) == ("prácticas", True)
    model.apply(events.SessionClosed())
    assert (model.sessionOpen, model.sessionName, model.sessionImportant) == (False, "", False)


def test_subtitulos_ultima_orden_y_ultima_respuesta(qtbot):
    model = AssistantModel()
    model.apply(events.CommandReceived("ejecuta git status", True))
    model.apply(events.SpeechStarted("Ejecutando git status.", True))
    assert (model.commandText, model.commandRecognized) == ("ejecuta git status", True)
    assert model.responseText == "Ejecutando git status."
    serial = model.subtitleSerial
    with qtbot.waitSignal(model.subtitlesChanged):
        model.apply(events.CommandReceived("qué tiempo hace", False))
    assert (model.commandText, model.commandRecognized) == ("qué tiempo hace", False)
    assert model.responseText == ""  # la respuesta anterior no era de esta orden
    assert model.subtitleSerial > serial  # reinicia el desvanecido de 6 s


def test_nivel_de_la_voz_y_boton_de_silencio(qtbot):
    model = AssistantModel()
    model.apply(events.SpeechStarted("Sesión iniciada. Le escucho.", False))
    assert model.speaking and not model.canSilence  # las frases del ciclo de vida no se cortan
    with qtbot.waitSignal(model.levelChanged):
        model.apply(events.AudioLevel(0.6, "assistant"))
    assert model.level == pytest.approx(0.6)
    model.apply(events.AudioLevel(0.3, "none"))
    assert model.level == 0.0
    model.apply(events.AudioLevel(0.8, "assistant"))
    model.apply(events.SpeechFinished(False))
    assert not model.speaking and model.level == 0.0  # sin locución, el núcleo queda quieto
    model.apply(events.SpeechStarted("Ejecutando git status.", True))
    assert model.canSilence


def test_panel_activo_es_el_ultimo_activado_y_se_vacia_con_la_sesion_nueva(qtbot):
    model = AssistantModel()
    assert model.activePanel == ""
    with qtbot.waitSignal(model.activePanelChanged):
        model.apply(events.PanelActivated("comandos"))
    model.apply(events.PanelActivated("recordatorios"))
    assert model.activePanel == "recordatorios"
    model.apply(events.SessionOpened(8, "2026-11-15"))
    assert model.activePanel == ""


def test_enviar_publica_el_texto_tal_cual_y_un_envio_vacio_no_publica_nada():
    published = []
    model = AssistantModel(publish=published.append)
    model.submit("Hey,  Jarvis.")
    model.submit("")
    model.submit("   ")
    assert published == [events.TextSubmitted("Hey,  Jarvis.")]


def test_teclear_avisa_como_mucho_una_vez_por_segundo():
    now = [100.0]
    published = []
    model = AssistantModel(publish=published.append, monotonic=lambda: now[0])
    model.typing()
    now[0] += 0.9
    model.typing()
    assert published == [events.UserTyping()]
    now[0] += 0.2
    model.typing()
    assert published == [events.UserTyping(), events.UserTyping()]
    model.submit("abre el navegador")  # tras enviar, la siguiente tecla avisa
    model.typing()
    assert published[-2:] == [events.TextSubmitted("abre el navegador"), events.UserTyping()]


def test_el_boton_de_silencio_publica_su_accion():
    published = []
    AssistantModel(publish=published.append).silence()
    assert published == [events.SilenceRequested()]


# --- Tareas --------------------------------------------------------------------------------------


def rows(model, role="taskId"):
    number = next(key for key, name in model.roleNames().items() if bytes(name).decode() == role)
    return [model.data(model.index(row), number) for row in range(model.rowCount())]


def test_tareas_la_mas_reciente_arriba_y_actualizacion_en_su_sitio(qtbot):
    model = TaskListModel()
    model.apply(task(1))
    with qtbot.waitSignal(model.rowsInserted):
        model.apply(task(2, description="abrir VS Code"))
    assert rows(model) == [2, 1]
    assert model.pendingCount == 2
    with qtbot.waitSignal(model.dataChanged):
        model.apply(task(1, "error", detail="No existe el comando"))
    assert rows(model) == [2, 1]
    assert rows(model, "status") == ["pendiente", "error"]
    assert rows(model, "detail") == ["", "No existe el comando"]
    assert rows(model, "description") == ["abrir VS Code", "git status"]
    assert rows(model, "module") == ["comandos", "comandos"]
    assert rows(model, "time") == ["18:32", "18:31"]
    assert (model.count, model.pendingCount) == (2, 1)
    assert model.data(model.index(0), Qt.ItemDataRole.DisplayRole) is None
    assert model.data(model.index(9), model._FIRST_ROLE) is None


def test_tareas_de_un_protocolo_bajo_la_suya_en_orden(qtbot):
    model = TaskListModel()
    model.apply(task(1))
    model.apply(task(2, description="protocolo trabajo"))
    model.apply(task(3, parent=2))
    model.apply(task(4, parent=2))
    model.apply(task(5))
    assert rows(model) == [5, 2, 3, 4, 1]
    assert rows(model, "child") == [False, False, True, True, False]
    assert rows(model, "parentId") == [-1, -1, 2, 2, -1]


def test_la_cola_de_ordenes_y_el_recuento_de_errores(qtbot):
    model = TaskListModel()
    model.apply(task(1, "error"))
    model.apply(task(2))
    assert (model.errorCount, model.pendingCount) == (1, 1)
    with qtbot.waitSignal(model.queueChanged):
        model.apply(events.OrderQueueChanged(("lista", "árbol")))
    assert model.queue == ["lista", "árbol"]
    with qtbot.assertNotEmitted(model.queueChanged):
        model.apply(events.OrderQueueChanged(("lista", "árbol")))
    with qtbot.waitSignal(model.queueChanged):
        model.apply(events.SessionOpened(2, "2026-11-15"))
    assert model.queue == []


def test_una_ventana_propone_una_orden_para_la_caja_de_texto(qtbot):
    published = []
    model = AssistantModel(published.append)
    with qtbot.waitSignal(model.suggested) as signal:
        model.suggest("Abre GitHub")
    assert signal.args == ["Abre GitHub"] and published == []  # se escribe, no se envía


def test_la_lista_de_tareas_se_vacia_al_abrir_otra_sesion(qtbot):
    model = TaskListModel()
    model.apply(task(1))
    with qtbot.waitSignal(model.modelReset):
        model.apply(events.SessionOpened(2, "2026-11-15"))
    assert (model.rowCount(), model.pendingCount) == (0, 0)


# --- Diálogo -------------------------------------------------------------------------------------


def test_dialogo_refleja_la_pregunta_y_su_cierre(qtbot):
    model = DialogueModel()
    assert not model.active and model.question == "" and model.hints == []
    with qtbot.waitSignal(model.changed):
        model.apply(
            events.DialogueOpened(
                "¿Elimino la sesión?", "CONFIRMATION", ("Sí", "No", "Cancelar"), 15.0,
                {"id": 12, "name": "prácticas"},
            )
        )
    assert model.active
    assert model.question == "¿Elimino la sesión?"
    assert model.expectedType == "CONFIRMATION"
    assert model.hints == ["Sí", "No", "Cancelar"]
    assert model.subject == "12 · prácticas"
    assert model.timeoutSeconds == 15.0
    serial = model.serial
    model.apply(events.DialogueOpened("¿Qué nombre?", "TEXT", ("Cancelar",), 15.0))
    assert model.serial > serial and model.subject == ""
    with qtbot.waitSignal(model.changed):
        model.apply(events.DialogueClosed("answered"))
    assert not model.active and model.timeoutSeconds == 0.0
    with qtbot.assertNotEmitted(model.changed):
        model.apply(events.DialogueClosed("cancelled"))
        model.apply(events.RestEntered())


def test_cerrar_la_sesion_cierra_el_dialogo(qtbot):
    model = DialogueModel()
    model.apply(events.DialogueOpened("¿Qué nombre?", "TEXT", (), 15.0))
    model.apply(events.SessionClosed())
    assert not model.active


# --- HUD contraído o expandido -------------------------------------------------------------------


def test_el_hud_se_expande_con_eventos_de_contenido_y_se_contrae_sin_ellos(qtbot):
    hud = HudModel(collapse_seconds=0.05)
    assert not hud.expanded
    hud.apply(events.CommandReceived("hola", False))
    assert not hud.expanded  # los subtítulos caben en la cabecera
    with qtbot.waitSignal(hud.expandedChanged):
        hud.apply(task(1, "completado"))
    assert hud.expanded
    qtbot.waitUntil(lambda: not hud.expanded, timeout=1000)
    for event in (
        events.DialogueOpened("¿Qué nombre?", "TEXT", (), 15.0),
        events.DialogueClosed("answered"),
        events.PanelActivated("comandos"),
    ):
        hud.collapse()
        hud.apply(event)
        assert hud.expanded


def test_el_hud_no_se_contrae_con_un_dialogo_abierto_o_una_tarea_pendiente(qtbot):
    busy = [True]
    hud = HudModel(collapse_seconds=0.02, is_busy=lambda: busy[0])
    hud.apply(task(1))
    qtbot.wait(120)
    assert hud.expanded
    busy[0] = False
    qtbot.waitUntil(lambda: not hud.expanded, timeout=1000)


def test_boton_de_expandir_o_contraer_y_cierre_de_sesion(qtbot):
    hud = HudModel(collapse_seconds=60)
    hud.toggle()
    assert hud.expanded
    hud.toggle()
    assert not hud.expanded
    hud.toggle()
    hud.apply(events.SessionClosed())
    assert not hud.expanded


def test_opciones_de_la_interfaz():
    options = UiOptions(UiSettings(hud_corner="bottom-left", quality="low", reduce_motion=True))
    assert (options.quality, options.reduceMotion, options.hudCorner, options.debug) == (
        "low", True, "bottom-left", False,
    )  # fmt: skip
    assert UiOptions(UiSettings(), debug=True).debug
