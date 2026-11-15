"""Modelos de vista de los paneles de los módulos: cada uno refleja sus eventos."""
from datetime import UTC, datetime

from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import HelpEntry, HelpGroup
from jarvis_assistant.core.content import Entry, OpenedItem, SearchResult, TreeNode
from jarvis_assistant.core.repositories import ActivityRow, SessionRow
from jarvis_assistant.ui.bridge import UI_EVENTS
from jarvis_assistant.ui.panel_models import (
    CommandsModel,
    HelpModel,
    HistoryModel,
    OpenedModel,
    SearchModel,
)

WHEN = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def task(task_id: int, status: str) -> events.TaskUpdated:
    return events.TaskUpdated(task_id, None, "comandos", "git status", status, None, WHEN)


def session(session_id: int, name: str, important: bool = False) -> SessionRow:
    return SessionRow(session_id, name, WHEN, None, None, important, False, False, False, None,
                      False)  # fmt: skip


# --- Comandos --------------------------------------------------------------------------------


def test_comandos_directorio_de_trabajo_y_listado(qtbot):
    model = CommandsModel()
    with qtbot.waitSignal(model.changed):
        model.apply(events.WorkdirChanged("C:/Proyectos"))
    assert (model.path, model.mode) == ("C:/Proyectos", "")
    model.apply(
        events.DirectoryListed("C:/Proyectos", (Entry("jarvis", True), Entry("a.txt", False)), 5)
    )
    assert model.mode == "listing"
    assert model.entries == [{"name": "jarvis", "isDir": True}, {"name": "a.txt", "isDir": False}]
    assert model.hiddenEntries == 3


def test_comandos_arbol_con_marca_de_recortado():
    model = CommandsModel()
    nodes = (TreeNode("src", 1, True), TreeNode("main.py", 2, False))
    model.apply(events.DirectoryTreeBuilt("C:/Proyectos", nodes, 1, 1, True))
    assert model.mode == "tree" and model.truncated
    assert model.nodes == [
        {"name": "src", "depth": 1, "isDir": True}, {"name": "main.py", "depth": 2, "isDir": False},
    ]  # fmt: skip
    assert model.entries == []


def test_comandos_salida_de_un_binario_y_su_estado():
    model = CommandsModel()
    model.apply(events.CommandOutputAppended(4, "git status", (), "out"))
    assert (model.mode, model.command, model.commandStatus) == ("output", "git status", "pendiente")
    model.apply(events.CommandOutputAppended(4, "git status", ("uno", "dos"), "out"))
    model.apply(events.CommandOutputAppended(4, "git status", ("mal",), "err"))
    assert model.lines == [
        {"text": "uno", "error": False}, {"text": "dos", "error": False},
        {"text": "mal", "error": True},
    ]  # fmt: skip
    model.apply(task(9, "error"))  # otra tarea: no es la del binario
    assert model.commandStatus == "pendiente"
    model.apply(task(4, "completado"))
    assert model.commandStatus == "completado"
    model.apply(events.CommandOutputAppended(5, "git log", ("otro",), "out"))  # otro binario
    assert (model.command, model.lines) == ("git log", [{"text": "otro", "error": False}])


def test_comandos_conserva_solo_las_ultimas_lineas():
    model = CommandsModel(output_lines=3)
    model.apply(events.CommandOutputAppended(4, "make", tuple(str(n) for n in range(10)), "out"))
    assert [line["text"] for line in model.lines] == ["7", "8", "9"]


def test_comandos_clear_vacia_el_resultado_y_conserva_el_directorio():
    model = CommandsModel()
    model.apply(events.WorkdirChanged("C:/Proyectos"))
    model.apply(events.DirectoryListed("C:/Proyectos", (Entry("a", True),), 1))
    model.apply(events.CommandPanelCleared())
    assert (model.mode, model.entries, model.path) == ("", [], "C:/Proyectos")
    model.apply(events.SessionOpened(2, "otra"))
    assert model.path == ""


# --- Aperturas -------------------------------------------------------------------------------


def test_aperturas_lista_completa_la_mas_reciente_arriba(qtbot):
    model = OpenedModel()
    items = (
        OpenedItem(1, "GitHub", "pagina", "completado", True),
        OpenedItem(2, "Docs", "carpeta", "error", False),
    )
    with qtbot.waitSignal(model.changed):
        model.apply(events.OpenedItemsChanged(items))
    assert [item["title"] for item in model.items] == ["Docs", "GitHub"]
    assert model.items[1] == {
        "id": 1, "title": "GitHub", "kind": "pagina", "status": "completado", "canFocus": True,
    }  # fmt: skip
    assert model.focusSupported
    model.apply(events.OpenedItemsChanged((), can_focus_windows=False))
    assert model.items == [] and not model.focusSupported


def test_aperturas_el_boton_publica_la_accion_del_usuario():
    published = []
    OpenedModel(published.append).focus(3)
    assert published == [events.FocusItemRequested(3)]


# --- Búsqueda --------------------------------------------------------------------------------


def test_busqueda_resultados_numerados():
    model = SearchModel()
    assert not model.active
    results = (
        SearchResult(1, "informe.txt", False, "C:/Docs", "C:/Docs/informe.txt"),
        SearchResult(2, "informes", True, "C:/Docs", "C:/Docs/informes"),
    )
    model.apply(events.SearchResultsReady("informe", "ambos", results, 14, True))
    assert (model.active, model.query, model.total, model.limited) == (True, "informe", 14, True)
    assert model.results[1] == {"index": 2, "name": "informes", "isDir": True, "folder": "C:/Docs"}
    model.apply(events.SessionOpened(2, "otra"))
    assert not model.active and model.results == []


# --- Historial -------------------------------------------------------------------------------


def test_historial_tabla_de_sesiones_con_la_actual_marcada():
    model = HistoryModel()
    model.apply(events.HistoryShown((session(12, "redes", True), session(11, "2026-11-14")), 12))
    assert model.mode == "sessions"
    first, second = model.sessions
    assert (first["id"], first["name"], first["important"], first["current"]) == (
        12, "redes", True, True,
    )  # fmt: skip
    assert (second["important"], second["current"]) == (False, False)
    assert first["date"] == WHEN.astimezone().strftime("%d/%m/%Y %H:%M")


def test_historial_actividades_de_una_sesion_la_mas_reciente_arriba():
    model = HistoryModel()
    rows = (
        ActivityRow(1, 12, None, "comandos", "ls", "completado", WHEN, None),
        ActivityRow(2, 12, None, "apertura", "abrir GitHub", "error", WHEN, None),
    )
    model.apply(events.SessionActivitiesShown(session(12, "redes"), rows))
    assert (model.mode, model.sessionTitle) == ("activities", "12 · redes")
    assert [a["description"] for a in model.activities] == ["abrir GitHub", "ls"]
    assert model.activities[0]["status"] == "error"
    assert model.activities[0]["time"] == WHEN.astimezone().strftime("%H:%M")


# --- Ayuda -----------------------------------------------------------------------------------


def test_ayuda_grupos_con_sus_ordenes_y_ejemplos():
    model = HelpModel()
    groups = (
        HelpGroup("comandos", "Comandos", (HelpEntry("Listar", "Qué hay aquí"),)),
        HelpGroup("apertura", "Aperturas", (HelpEntry("Abrir", "Abre GitHub"),)),
    )
    model.apply(events.HelpShown(groups))
    assert model.rows == [
        {"header": True, "title": "Comandos", "example": ""},
        {"header": False, "title": "Listar", "example": "Qué hay aquí"},
        {"header": True, "title": "Aperturas", "example": ""},
        {"header": False, "title": "Abrir", "example": "Abre GitHub"},
    ]


# --- Puente ----------------------------------------------------------------------------------


def test_el_puente_entrega_los_eventos_de_contenido_de_los_paneles():
    assert {
        events.WorkdirChanged, events.DirectoryListed, events.DirectoryTreeBuilt,
        events.CommandOutputAppended, events.CommandPanelCleared, events.OpenedItemsChanged,
        events.SearchResultsReady, events.HistoryShown, events.SessionActivitiesShown,
        events.HelpShown,
    } <= set(UI_EVENTS)  # fmt: skip
