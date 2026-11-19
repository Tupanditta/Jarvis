"""Modelos de vista de los paneles de los módulos: cada uno refleja sus eventos."""
from datetime import UTC, datetime
from pathlib import Path

from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import HelpEntry, HelpGroup
from jarvis_assistant.core.content import (
    CatalogItem,
    Entry,
    LaunchTarget,
    OpenedItem,
    ProtocolRow,
    ReminderItem,
    SearchResult,
    TreeNode,
)
from jarvis_assistant.core.repositories import ActivityRow, SessionRow
from jarvis_assistant.ui.bridge import UI_EVENTS
from jarvis_assistant.ui.panel_models import (
    CatalogModel,
    CommandsModel,
    ConsolesModel,
    HelpModel,
    HistoryModel,
    OpenedModel,
    ProtocolModel,
    RemindersModel,
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
    assert model.results[1] == {
        "index": 2, "name": "informes", "isDir": True, "folder": "C:/Docs",
        "path": "C:/Docs/informes",
    }  # fmt: skip
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


# --- Acciones de las ventanas ----------------------------------------------------------------


def requested(published) -> list[tuple[str, str, dict]]:
    assert all(isinstance(event, events.ActionRequested) for event in published)
    return [(event.module, event.action, dict(event.params)) for event in published]


def test_comandos_la_ruta_se_navega_carpeta_a_carpeta():
    published = []
    model = CommandsModel(publish=published.append)
    assert model.crumbs == [] and not model.canGoUp
    model.apply(events.WorkdirChanged(str(Path("C:/Users/usuario"))))
    model.apply(events.WorkdirChanged(str(Path("C:/Users/usuario/Proyectos"))))
    assert [crumb["name"] for crumb in model.crumbs] == ["C:", "Users", "usuario", "Proyectos"]
    assert model.crumbs[2]["path"] == str(Path("C:/Users/usuario")) and model.canGoUp
    model.goTo(model.crumbs[1]["path"])
    model.up()
    model.home()  # la carpeta en la que empezó la sesión
    model.enter("jarvis")
    assert requested(published) == [
        ("comandos", "cd", {"ruta": Path("C:/Users")}), ("comandos", "ls", {}),
        ("comandos", "cd", {"ruta": Path("C:/Users/usuario")}), ("comandos", "ls", {}),
        ("comandos", "cd", {"ruta": Path("C:/Users/usuario")}), ("comandos", "ls", {}),
        ("comandos", "cd", {"ruta": Path("C:/Users/usuario/Proyectos/jarvis")}),
        ("comandos", "ls", {}),
    ]  # fmt: skip


def test_comandos_la_barra_de_herramientas_pide_las_acciones_del_modulo():
    published = []
    model = CommandsModel(publish=published.append)
    for action in (model.refresh, model.tree, model.clear, model.terminal, model.reveal):
        action()
    assert requested(published) == [
        ("comandos", "ls", {}), ("comandos", "arbol", {}), ("comandos", "clear", {}),
        ("comandos", "abrir_consola", {}), ("apertura", "abrir_carpeta", {}),
    ]  # fmt: skip
    model.up()  # sin directorio de trabajo no hay adónde subir
    assert len(published) == 5


def test_comandos_la_salida_se_puede_copiar_como_texto():
    model = CommandsModel()
    model.apply(events.CommandOutputAppended(4, "git status", ("uno", "dos"), "out"))
    assert model.outputText().splitlines() == ["uno", "dos"]


def test_aperturas_acceso_rapido_al_catalogo():
    published = []
    model = OpenedModel(published.append)
    model.apply(events.LaunchTargetsChanged(
        (LaunchTarget("GitHub", "pagina"), LaunchTarget("Bloc de notas", "aplicacion"))
    ))  # fmt: skip
    assert model.targets == [
        {"name": "GitHub", "kind": "pagina"}, {"name": "Bloc de notas", "kind": "aplicacion"},
    ]  # fmt: skip
    model.launch("GitHub")
    model.launch("")
    assert requested(published) == [("apertura", "abrir", {"objetivo": "GitHub"})]


def test_busqueda_desde_la_ventana():
    published = []
    model = SearchModel(publish=published.append)
    model.run("  informe ", "archivos")
    model.run("informe", "otra cosa")  # un tipo desconocido busca de todo
    model.run("   ", "ambos")  # sin texto no se busca
    model.open(2)
    model.reveal(2)
    assert requested(published) == [
        ("busqueda", "buscar", {"consulta": "informe", "tipo": "archivos"}),
        ("busqueda", "buscar", {"consulta": "informe", "tipo": "ambos"}),
        ("busqueda", "abrir_resultado", {"n": 2}), ("busqueda", "abrir_ubicacion", {"n": 2}),
    ]  # fmt: skip


def test_historial_y_ayuda_desde_sus_ventanas():
    published = []
    history = HistoryModel(publish=published.append)
    history.refresh()
    history.open(12)
    HelpModel(publish=published.append).load()
    assert requested(published) == [
        ("historial", "mostrar", {}), ("historial", "actividades", {"id": 12}),
        ("nucleo", "ayuda", {}),
    ]  # fmt: skip
    current = session(12, "redes")
    history.apply(events.SessionActivitiesShown(current, (
        ActivityRow(1, 12, None, "comandos", "git status", "completado", WHEN, None),
        ActivityRow(2, 12, None, "apertura", "abrir GitHub", "error", WHEN, None),
    )))  # fmt: skip
    assert history.errorCount == 1


# --- Puente ----------------------------------------------------------------------------------


def test_el_puente_entrega_los_eventos_de_contenido_de_los_paneles():
    assert {
        events.WorkdirChanged, events.DirectoryListed, events.DirectoryTreeBuilt,
        events.CommandOutputAppended, events.CommandPanelCleared, events.OpenedItemsChanged,
        events.SearchResultsReady, events.HistoryShown, events.SessionActivitiesShown,
        events.HelpShown, events.LaunchTargetsChanged, events.OrderQueueChanged,
    } <= set(UI_EVENTS)  # fmt: skip


def test_recordatorios_lista_numerada_con_vencidos_y_destacado():
    published: list[events.Event] = []
    model = RemindersModel(publish=published.append)
    assert model.items == []
    model.apply(events.RemindersChanged((
        ReminderItem(1, 4, "Llamar a Ana", "activo", WHEN, None, highlighted=True),
        ReminderItem(2, 9, "Pagar", "vencido", None, WHEN),
    )))  # fmt: skip
    first, second = model.items
    assert (first["index"], first["content"], first["highlighted"]) == (1, "Llamar a Ana", True)
    assert first["next"] == WHEN.astimezone().strftime("%d/%m %H:%M")
    assert (first["deadline"], first["overdue"]) == ("", False)
    assert (second["next"], second["overdue"]) == ("", True)
    assert model.overdueCount == 1
    model.refresh()
    assert published == [events.ActionRequested("recordatorio", "mostrar")]
    assert events.RemindersChanged in UI_EVENTS


def _step(task_id: int, status: str, description: str, detail: str | None = None):
    return events.TaskUpdated(task_id, 5, "comandos", description, status, detail, WHEN)


def test_protocolo_tareas_y_progreso_en_tiempo_real():
    """RF-53, RF-57: todas en `pendiente` al empezar; cada una cambia en cuanto cambia."""
    model = ProtocolModel()
    assert (model.mode, model.hasRun, model.steps) == ("", False, [])
    model.apply(events.ProtocolStarted(5, "modo trabajo", ("cd jarvis", "ejecutar git status"),
                                       (6, 7)))
    assert (model.mode, model.name, model.running) == ("run", "modo trabajo", True)
    assert [s["status"] for s in model.steps] == ["pendiente", "pendiente"]
    assert (model.doneCount, model.progress) == (0, 0.0)
    model.apply(_step(6, "completado", "cd Jarvis"))
    assert model.steps[0]["description"] == "cd Jarvis"
    assert (model.doneCount, model.progress) == (1, 0.5)
    model.apply(_step(99, "error", "otra tarea"))  # no es del protocolo
    model.apply(_step(7, "error", "git status", "git ha terminado con 1"))
    assert model.steps[1]["detail"] == "git ha terminado con 1"
    assert (model.doneCount, model.errorCount, model.progress) == (2, 1, 1.0)
    model.apply(events.ProtocolFinished(5, 1, 1))
    assert not model.running
    model.apply(events.SessionOpened(2, "otra"))
    assert (model.mode, model.hasRun) == ("", False)


def test_protocolo_listado_y_acciones_de_la_ventana():
    published: list[events.Event] = []
    model = ProtocolModel(publish=published.append)
    model.apply(events.ProtocolStarted(5, "modo trabajo", ("cd jarvis",), (6,)))
    model.apply(events.ProtocolsListed((
        ProtocolRow("modo-trabajo", "modo trabajo", ("a trabajar",), True, ("cd jarvis",)),
    )))  # fmt: skip
    assert model.mode == "list"
    assert model.protocols == [{"name": "modo trabajo", "aliases": "a trabajar",
                                "important": True, "steps": 1, "summary": "cd jarvis"}]
    model.showRun()
    assert model.mode == "run"
    model.refresh()
    model.run("modo trabajo")
    assert published == [
        events.ActionRequested("protocolos", "listar"),
        events.ActionRequested("protocolos", "ejecutar", {"protocolo": "modo trabajo"}),
    ]
    assert {events.ProtocolStarted, events.ProtocolFinished, events.ProtocolsListed} <= set(
        UI_EVENTS
    )


# --- Varias consolas de Comandos -------------------------------------------------------------


def test_comandos_cada_consola_solo_atiende_sus_eventos_y_pide_en_la_suya():
    published = []
    consoles = ConsolesModel(publish=published.append)
    consoles.apply(events.WorkdirChanged(str(Path("C:/Users/usuario"))))
    consoles.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    copy = consoles.get("comandos:protocolo-a")
    assert copy is not consoles.main and consoles.get("otra") is consoles.main
    consoles.apply(events.WorkdirChanged(str(Path("C:/Algebra")), "comandos:protocolo-a"))
    consoles.apply(events.CommandOutputAppended(3, "git pull", ("ok",), "out",
                                                "comandos:protocolo-a"))  # fmt: skip
    assert copy.path == str(Path("C:/Algebra")) and copy.mode == "output"
    assert consoles.main.path == str(Path("C:/Users/usuario")) and consoles.main.mode == ""
    copy.refresh()
    copy.reveal()
    copy.home()  # la carpeta personal de la sesión, aunque la copia naciera después
    copy.duplicate()
    assert published == [
        events.ActionRequested("comandos", "ls", {}, "comandos:protocolo-a"),
        events.ActionRequested("apertura", "abrir_carpeta", {}, "comandos:protocolo-a"),
        events.ActionRequested("comandos", "cd", {"ruta": Path("C:/Users/usuario")},
                               "comandos:protocolo-a"),
        events.ActionRequested("comandos", "ls", {}, "comandos:protocolo-a"),
        events.ConsoleRequested("comandos:protocolo-a"),
    ]  # fmt: skip


def test_comandos_la_consola_cerrada_o_la_sesion_nueva_quitan_los_paneles_extra():
    consoles = ConsolesModel()
    consoles.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    consoles.apply(events.ConsoleOpened("comandos:2", "Comandos 2"))
    consoles.apply(events.ConsoleClosed("comandos:protocolo-a"))
    assert "comandos:protocolo-a" not in consoles and "comandos:2" in consoles
    consoles.apply(events.SessionOpened(2, "nueva"))
    assert "comandos:2" not in consoles and "comandos" in consoles


# --- Catálogo --------------------------------------------------------------------------------

CATALOG_ITEMS = (
    CatalogItem("aplicacion:Editor", "aplicacion", "Editor", "C:/editor.exe",
                ("ed", "el editor"), ("-n", "--wait")),
    CatalogItem("comando:git", "comando", "git", "git"),
)  # fmt: skip


def test_catalogo_lista_completa_con_alias_y_argumentos():
    assert events.CatalogShown in UI_EVENTS
    model = CatalogModel()
    model.apply(events.CatalogShown(CATALOG_ITEMS))
    assert model.items == [
        {"id": "aplicacion:Editor", "kind": "aplicacion", "name": "Editor",
         "target": "C:/editor.exe", "aliases": "ed, el editor", "args": "-n --wait"},
        {"id": "comando:git", "kind": "comando", "name": "git", "target": "git",
         "aliases": "", "args": ""},
    ]  # fmt: skip
    assert model.problem == ""


def test_catalogo_anadir_y_eliminar_piden_la_accion_del_modulo():
    published: list = []
    model = CatalogModel(publish=published.append)
    model.add("aplicacion", "Editor", "C:/editor.exe", "ed", "-n")
    model.add("pagina", "Docs", "https://example.com", "", "  ")
    model.remove("comando:git")
    assert requested(published) == [
        ("catalogo", "añadir", {"tipo": "aplicacion", "nombre": "Editor",
                                "destino": "C:/editor.exe", "alias": "ed", "argumentos": "-n"}),
        ("catalogo", "añadir", {"tipo": "pagina", "nombre": "Docs",
                                "destino": "https://example.com", "alias": ""}),
        ("catalogo", "eliminar", {"entrada": "comando:git"}),
    ]  # fmt: skip


def test_catalogo_el_formulario_se_vacia_solo_si_se_ha_anadido(qtbot):
    model = CatalogModel()
    added: list = []
    model.added.connect(lambda: added.append(True))
    model.add("pagina", "Docs", "docs", "", "")
    model.apply(events.CatalogShown(CATALOG_ITEMS, "La dirección debe empezar por http://."))
    assert added == [] and model.problem.startswith("La dirección")
    model.add("pagina", "Docs", "https://example.com", "", "")
    assert model.problem == ""
    model.apply(events.CatalogShown(CATALOG_ITEMS))
    assert added == [True]
    model.apply(events.CatalogShown(CATALOG_ITEMS))  # una lista que no responde a un envío
    assert added == [True]
