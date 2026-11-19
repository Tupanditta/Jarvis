"""Ventanas flotantes: registro, disposición y plantillas (`ui/workspace.py`)."""

import pytest

from jarvis_assistant.config import (
    FACTORY_LAYOUT,
    BarPosition,
    Config,
    Profile,
    ScreenLayout,
    WindowPlacement,
)
from jarvis_assistant.config.layouts import MIN_INPUT_WIDTH
from jarvis_assistant.core import events
from jarvis_assistant.ui.meter import MeterModel
from jarvis_assistant.ui.workspace import (
    WINDOWS,
    WindowSpec,
    WorkspaceModel,
)

SPECS = (
    WindowSpec("actividad", "Actividad", "tarea", "ActivityPanel.qml", 0.0, 0.0, 0.2, 0.5,
               open=True),
    WindowSpec("comandos", "Comandos", "comandos", "CommandsPanel.qml", 0.7, 0.0, 0.3, 0.5),
    WindowSpec("busqueda", "Búsqueda", "busqueda", "SearchPanel.qml", 0.0, 0.5, 0.2, 0.5),
)  # fmt: skip


def rows(model, role):
    number = next(key for key, name in model.roleNames().items() if bytes(name).decode() == role)
    return [model.data(model.index(row), number) for row in range(model.rowCount())]


def geometry(model, window_id):
    p = model.placement(window_id)
    return tuple(round(value, 3) for value in (p.x, p.y, p.width, p.height))


@pytest.fixture
def model():
    return WorkspaceModel(SPECS)


# --- Registro --------------------------------------------------------------------------------


def test_hay_una_ventana_por_modulo_con_su_panel_y_caben_en_el_area():
    assert [spec.id for spec in WINDOWS] == [
        "actividad", "comandos", "aperturas", "busqueda", "historial", "ayuda", "recordatorios",
        "protocolo", "permisos", "credenciales", "perfiles",
    ]  # fmt: skip
    assert [spec.id for spec in WINDOWS if spec.admin] == ["permisos", "credenciales", "perfiles"]
    for spec in WINDOWS:
        assert spec.title and spec.icon and spec.component.endswith("Panel.qml")
        assert spec.x >= 0 and spec.x + spec.width <= 1
        assert spec.y >= 0 and spec.y + spec.height <= 1


def test_cada_ventana_tiene_su_archivo_de_panel_y_su_icono():
    from jarvis_assistant.ui.app import QML_DIR, UI_DIR

    for spec in WINDOWS:
        assert (QML_DIR / "panels" / spec.component).is_file(), spec.component
        assert (UI_DIR / "assets" / "icons" / f"{spec.icon}.svg").is_file(), spec.icon


def test_el_modelo_expone_el_registro_en_su_orden(model):
    assert rows(model, "windowId") == ["actividad", "comandos", "busqueda"]
    assert rows(model, "title") == ["Actividad", "Comandos", "Búsqueda"]
    assert rows(model, "open") == [True, False, False]
    assert rows(model, "focused") == [True, False, False]
    assert model.component("comandos") == "CommandsPanel.qml"
    assert model.component("nadie") == ""
    assert model.openCount == 1


# --- Abrir, cerrar y traer al frente ---------------------------------------------------------


def test_un_modulo_que_muestra_algo_abre_su_ventana_y_la_trae_al_frente(model, qtbot):
    with qtbot.waitSignal(model.changed):
        model.apply(events.PanelActivated("comandos"))
    assert rows(model, "open") == [True, True, False]
    assert rows(model, "focused") == [False, True, False]
    model.apply(events.PanelActivated("prueba"))  # un panel sin ventana no hace nada
    assert model.openCount == 2


def test_el_selector_abre_trae_al_frente_y_cierra(model):
    model.toggle("comandos")  # cerrada: se abre encima
    assert rows(model, "focused") == [False, True, False]
    model.toggle("actividad")  # abierta pero debajo: pasa al frente
    assert rows(model, "open") == [True, True, False]
    assert rows(model, "focused") == [True, False, False]
    model.toggle("actividad")  # abierta y encima: se cierra
    assert rows(model, "open") == [False, True, False]
    assert rows(model, "focused") == [False, True, False]  # el frente pasa a la siguiente


def test_cerrar_la_unica_ventana_deja_el_area_vacia(model):
    model.close("actividad")
    assert model.openCount == 0 and rows(model, "focused") == [False, False, False]
    model.close("nadie")
    model.show("nadie")


def test_traer_al_frente_la_que_ya_esta_encima_no_cambia_nada(model, qtbot):
    with qtbot.assertNotEmitted(model.changed):
        model.show("actividad")


# --- Mover y cambiar de tamaño ---------------------------------------------------------------


def test_mover_y_cambiar_de_tamano(model, qtbot):
    with qtbot.waitSignal(model.dataChanged):
        model.move("actividad", 0.4, 0.25)
    assert geometry(model, "actividad") == (0.4, 0.25, 0.2, 0.5)
    model.resize("actividad", 0.1, 0.1, 0.5, 0.6)
    assert geometry(model, "actividad") == (0.1, 0.1, 0.5, 0.6)


def test_una_ventana_no_sale_del_area_ni_se_queda_sin_tamano(model):
    model.move("actividad", 0.95, -0.3)
    assert geometry(model, "actividad") == (0.8, 0.0, 0.2, 0.5)
    model.resize("actividad", 0.5, 0.5, 0.9, 0.001)
    assert geometry(model, "actividad") == (0.1, 0.5, 0.9, 0.08)


def test_restablecer_vuelve_a_la_disposicion_inicial(model, qtbot):
    model.move("actividad", 0.5, 0.5)
    model.show("busqueda")
    with qtbot.waitSignal(model.dataChanged):
        model.reset()
    assert geometry(model, "actividad") == (0.0, 0.0, 0.2, 0.5)
    assert rows(model, "open") == [True, False, False]


# --- Apartar --------------------------------------------------------------------------------


def test_apartar_conserva_la_disposicion_y_pasa_el_frente_a_otra(model):
    model.show("comandos")
    before = geometry(model, "comandos")
    model.set_aside("comandos")
    assert rows(model, "aside") == [False, True, False]
    assert rows(model, "open") == [True, True, False]
    assert rows(model, "focused") == [True, False, False]
    assert geometry(model, "comandos") == before
    assert model.spreadCount == 1


def test_solo_se_aparta_una_ventana_abierta(model, qtbot):
    with qtbot.assertNotEmitted(model.changed):
        model.set_aside("busqueda")
        model.set_aside("nadie")
    assert rows(model, "aside") == [False, False, False]


def test_recuperar_una_apartada_la_devuelve_a_su_sitio_encima(model):
    model.show("comandos")
    model.set_aside("comandos")
    model.restore("comandos")
    assert rows(model, "aside") == [False, False, False]
    assert rows(model, "focused") == [False, True, False]


def test_pulsar_una_apartada_la_pone_encima_sin_recuperarla(model):
    model.show("comandos")
    model.set_aside("comandos")
    model.raise_window("comandos")
    assert rows(model, "aside") == [False, True, False]
    assert model.placement("comandos").order > model.placement("actividad").order
    assert rows(model, "focused") == [True, False, False]


def test_apartar_todas_aparta_solo_las_abiertas(model):
    model.show("comandos")
    model.set_aside_all()
    assert rows(model, "aside") == [True, True, False]
    assert rows(model, "focused") == [False, False, False]
    assert model.spreadCount == 0 and model.openCount == 2


def test_cerrar_una_apartada_y_volver_a_abrirla_la_abre_entera(model):
    model.set_aside("actividad")
    model.close("actividad")
    assert model.openCount == 0
    model.toggle("actividad")
    assert rows(model, "open") == [True, False, False]
    assert rows(model, "aside") == [False, False, False]


def test_el_selector_y_un_modulo_que_muestra_algo_recuperan_la_apartada(model):
    model.set_aside("actividad")
    model.toggle("actividad")
    assert rows(model, "aside") == [False, False, False]
    assert rows(model, "open") == [True, False, False]
    model.set_aside("actividad")
    model.apply(events.PanelActivated("actividad"))
    assert rows(model, "aside") == [False, False, False]


def test_aparta_por_titulo_o_todas(model):
    model.show("busqueda")
    model.apply(events.WindowAsideRequested("Búsqueda"))
    assert rows(model, "aside") == [False, False, True]
    model.apply(events.WindowAsideRequested("Comandos"))  # cerrada: nada
    model.apply(events.WindowAsideRequested("Nadie"))
    assert rows(model, "aside") == [False, False, True]
    model.apply(events.WindowAsideRequested())
    assert rows(model, "aside") == [True, False, True]


def test_devolver_todas_recupera_las_apartadas_en_su_orden(model):
    model.show("comandos")
    model.show("busqueda")
    model.set_aside_all()
    model.restore_all()
    assert rows(model, "aside") == [False, False, False]
    assert rows(model, "focused") == [False, False, True]  # la que estaba encima, encima
    assert model.asideCount == 0 and model.spreadCount == 3


def test_el_boton_aparta_si_no_hay_mas_apartadas_que_a_la_vista(model):
    model.show("comandos")  # 2 a la vista, 0 apartadas: aparta
    model.toggle_aside_all()
    assert rows(model, "aside") == [True, True, False]
    model.show("busqueda")  # 1 a la vista, 2 apartadas: devuelve
    model.toggle_aside_all()
    assert rows(model, "aside") == [False, False, False]
    model.set_aside("actividad")
    model.show("busqueda")
    model.close("comandos")  # 1 a la vista, 1 apartada: a la par, aparta
    assert (model.spreadCount, model.asideCount) == (1, 1)
    model.toggle_aside_all()
    assert rows(model, "aside") == [True, False, True]


def test_desaparta_por_titulo_o_todas(model):
    model.show("comandos")
    model.set_aside_all()
    model.apply(events.WindowAsideRequested("Comandos", aside=False))
    assert rows(model, "aside") == [True, False, False]
    model.apply(events.WindowAsideRequested(aside=False))
    assert rows(model, "aside") == [False, False, False]


def test_restablecer_recupera_las_apartadas(model):
    model.set_aside("actividad")
    model.reset()
    assert rows(model, "aside") == [False, False, False]


# --- Plantillas -----------------------------------------------------------------------------


LAYOUT = ScreenLayout(
    "programar", "Programar",
    dock=BarPosition(0.2, 0.9), input=BarPosition(0.5, 0.1), input_width=0.5,
    windows={
        "comandos": WindowPlacement(True, 0.3, 0.2, 0.3, 0.5, 3),
        "actividad": WindowPlacement(False, 0.0, 0.0, 0.2, 0.5, 0),
        "antigua": WindowPlacement(True, 0.1, 0.1, 0.2, 0.2, 1),
    },
)  # fmt: skip
CONFIG = Config(
    profiles=(Profile("a", "A"), Profile("b", "B", layout="programar")), layouts=(LAYOUT,)
)


def test_sin_plantilla_empieza_en_la_disposicion_de_fabrica(model):
    assert rows(model, "open") == [True, False, False]
    assert (model.dockX, model.dockY) == (FACTORY_LAYOUT.dock.x, FACTORY_LAYOUT.dock.y)
    assert model.inputWidth == FACTORY_LAYOUT.input_width


def test_una_plantilla_pone_ventanas_y_barras_y_las_que_no_nombra_van_de_fabrica(model):
    model.apply_layout(LAYOUT)
    assert rows(model, "open") == [False, True, False]
    assert geometry(model, "comandos") == (0.3, 0.2, 0.3, 0.5)
    assert geometry(model, "busqueda") == (0.0, 0.5, 0.2, 0.5)  # no está en la plantilla
    assert (model.dockX, model.dockY, model.inputX, model.inputY, model.inputWidth) == (
        0.2, 0.9, 0.5, 0.1, 0.5
    )


def test_restablecer_vuelve_a_la_plantilla_y_no_a_la_de_fabrica(model):
    model.apply_layout(LAYOUT)
    model.move("comandos", 0.0, 0.0)
    model.placeInput(0.1, 0.1, 0.9)
    model.reset()
    assert geometry(model, "comandos") == (0.3, 0.2, 0.3, 0.5)
    assert model.inputWidth == 0.5


def test_al_abrir_sesion_se_toma_la_plantilla_del_perfil(model):
    model.apply(events.ConfigApplied(CONFIG))
    model.apply(events.SessionOpened(1, "hoy", "b"))
    assert geometry(model, "comandos") == (0.3, 0.2, 0.3, 0.5)
    model.apply(events.SessionOpened(2, "hoy", "a"))  # sin plantilla: la de fábrica
    assert rows(model, "open") == [True, False, False]


def test_dormido_elegir_perfil_pone_sus_barras_y_en_sesion_no_cambia_nada(model):
    model.apply(events.ConfigApplied(CONFIG))
    model.apply(events.ProfileSelected("b"))
    assert model.inputY == 0.1
    model.apply(events.SessionOpened(1, "hoy", "a"))
    model.apply(events.ProfileSelected("b"))
    assert model.inputY == FACTORY_LAYOUT.input.y
    model.apply(events.SessionClosed())
    model.apply(events.ProfileSelected("b"))
    assert model.inputY == 0.1


def test_la_disposicion_vuelve_a_ser_plantilla_con_todas_las_ventanas(model):
    model.apply_layout(LAYOUT)
    model.set_open("busqueda", True)
    model.set_aside("comandos")
    model.moveDock(1.4, -0.2)  # fuera de la pantalla: se recoloca
    layout = model.to_layout("nueva", "Nueva")
    assert (layout.id, layout.name) == ("nueva", "Nueva")
    assert set(layout.windows) == {"actividad", "comandos", "busqueda"}
    assert layout.windows["busqueda"].open
    assert layout.windows["comandos"] == WindowPlacement(True, 0.3, 0.2, 0.3, 0.5, 3)
    assert layout.dock == BarPosition(1.0, 0.0)


def test_aplicar_una_plantilla_no_reinicia_el_modelo_ni_avisa_si_no_cambia(model, qtbot):
    resets, changes = [], []
    model.modelReset.connect(lambda: resets.append(True))
    model.dataChanged.connect(lambda *_args: changes.append(True))
    model.apply_layout(LAYOUT)
    model.apply_layout(LAYOUT)
    assert resets == [] and len(changes) == 1


def with_meters():
    meters = {"recursos": MeterModel(False), "ruido": MeterModel(False)}
    return WorkspaceModel(SPECS, meters=meters), meters


def test_los_medidores_empiezan_como_de_fabrica_y_la_plantilla_dice_si_se_ven():
    model, meters = with_meters()
    assert (meters["recursos"].shown, meters["ruido"].shown) == (True, False)
    model.apply_layout(ScreenLayout("a", "A", meters={"recursos": False, "ruido": True}))
    assert (meters["recursos"].shown, meters["ruido"].shown) == (False, True)
    meters["ruido"].toggle()
    model.reset()  # restablecer vuelve a lo que dice la plantilla
    assert meters["ruido"].shown


def test_la_plantilla_guarda_los_medidores():
    model, meters = with_meters()
    meters["ruido"].toggle()
    assert model.to_layout("n", "N").meters == {"recursos": True, "ruido": True}


def test_un_medidor_restringido_no_se_ve_ni_se_puede_mostrar():
    model, meters = with_meters()
    model.apply(events.PermissionsApplied(frozenset({"recursos"})))
    assert not meters["recursos"].allowed and not meters["recursos"].shown
    meters["recursos"].toggle()
    assert not meters["recursos"].shown
    model.apply(events.PermissionsApplied(frozenset()))
    assert meters["recursos"].shown  # vuelve como lo dejó la plantilla


def test_la_caja_de_texto_tiene_un_ancho_minimo(model):
    model.placeInput(0.5, 0.5, 0.0)
    assert model.inputWidth == MIN_INPUT_WIDTH


def test_cada_ventana_tiene_una_forma_de_marco_conocida_y_el_modelo_la_expone():
    from jarvis_assistant.ui.workspace import FRAME_STYLES

    assert {spec.style for spec in WINDOWS} <= set(FRAME_STYLES)
    assert len({spec.style for spec in WINDOWS}) > 1  # no son todas iguales
    full = WorkspaceModel(WINDOWS)
    assert rows(full, "style") == [spec.style for spec in WINDOWS]


# --- Copias de la ventana de Comandos --------------------------------------------------------


def test_una_consola_nueva_abre_una_copia_de_comandos_encima(model):
    published = []
    model = WorkspaceModel(SPECS, publish=published.append)
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    assert rows(model, "windowId")[-1] == "comandos:protocolo-a"
    assert rows(model, "title")[-1] == "Comandos · a"
    assert rows(model, "component")[-1] == "CommandsPanel.qml"
    copy = model.placement("comandos:protocolo-a")
    assert copy.open and rows(model, "focused")[-1]
    assert geometry(model, "comandos:protocolo-a") != geometry(model, "comandos")
    assert published == [events.ConsoleFocused("comandos:protocolo-a")]


def test_la_misma_consola_reutiliza_su_ventana(model):
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    model.show("busqueda")
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    assert rows(model, "windowId").count("comandos:protocolo-a") == 1
    assert rows(model, "focused")[-1]


def test_varias_copias_son_ventanas_independientes(model):
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    model.apply(events.ConsoleOpened("comandos:protocolo-b", "Comandos · b"))
    assert rows(model, "windowId")[-2:] == ["comandos:protocolo-a", "comandos:protocolo-b"]
    model.move("comandos:protocolo-a", 0.1, 0.1)
    assert geometry(model, "comandos:protocolo-a")[:2] == (0.1, 0.1)
    assert geometry(model, "comandos:protocolo-b")[:2] != (0.1, 0.1)


def test_cerrar_una_copia_la_quita_y_avisa_al_nucleo():
    published = []
    model = WorkspaceModel(SPECS, publish=published.append)
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    published.clear()
    model.close("comandos:protocolo-a")
    assert "comandos:protocolo-a" not in rows(model, "windowId")
    assert published == [
        events.ConsoleFocused("comandos"), events.ConsoleClosed("comandos:protocolo-a")
    ]
    model.close("comandos")  # la principal solo se cierra
    assert "comandos" in rows(model, "windowId")


def test_la_consola_activa_es_la_de_la_ventana_de_comandos_de_delante():
    published = []
    model = WorkspaceModel(SPECS, publish=published.append)
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    model.apply(events.ConsoleOpened("comandos:protocolo-b", "Comandos · b"))
    model.show("busqueda")  # otra ventana delante no cambia la consola
    model.raise_window("comandos:protocolo-a")
    model.set_aside("comandos:protocolo-a")
    assert published == [
        events.ConsoleFocused("comandos:protocolo-a"),
        events.ConsoleFocused("comandos:protocolo-b"),
        events.ConsoleFocused("comandos:protocolo-a"),
        events.ConsoleFocused("comandos:protocolo-b"),
    ]


def test_las_copias_no_entran_en_la_plantilla_y_desaparecen_con_la_sesion(model):
    model.apply(events.ConfigApplied(Config()))
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    assert "comandos:protocolo-a" not in model.to_layout("mia", "Mía").windows
    model.reset()  # la plantilla no se lleva las copias
    assert model.placement("comandos:protocolo-a").open
    model.apply(events.SessionOpened(1, "", ""))
    assert "comandos:protocolo-a" not in rows(model, "windowId")


def test_una_copia_no_se_ve_si_el_perfil_no_puede_usar_comandos(model):
    model.apply(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    model.apply(events.PermissionsApplied(frozenset({"comandos"})))
    assert not model.placement("comandos:protocolo-a").open
    assert rows(model, "available")[-1] is False
