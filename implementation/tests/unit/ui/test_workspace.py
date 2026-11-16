"""Ventanas flotantes: registro, disposición y guardado (`ui/workspace.py`)."""
import json

import pytest

from jarvis_assistant.core import events
from jarvis_assistant.ui.workspace import (
    WINDOWS,
    LayoutStore,
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
        "protocolo",
    ]  # fmt: skip
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
    with qtbot.waitSignal(model.modelReset):
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


# --- Guardado --------------------------------------------------------------------------------


def test_la_disposicion_se_guarda_y_se_recupera(tmp_path):
    path = tmp_path / "datos" / "ventanas.json"
    model = WorkspaceModel(SPECS, LayoutStore(path))
    model.show("comandos")
    model.move("comandos", 0.3, 0.2)
    model.close("actividad")
    model.save()
    restored = WorkspaceModel(SPECS, LayoutStore(path))
    assert rows(restored, "open") == [False, True, False]
    assert geometry(restored, "comandos") == (0.3, 0.2, 0.3, 0.5)
    assert rows(restored, "focused") == [False, True, False]


def test_los_cambios_se_guardan_solos_al_cabo_de_un_momento(tmp_path, qtbot):
    path = tmp_path / "ventanas.json"
    model = WorkspaceModel(SPECS, LayoutStore(path))
    model._save_timer.setInterval(10)
    model.move("actividad", 0.5, 0.5)
    qtbot.waitUntil(path.is_file, timeout=2000)
    assert json.loads(path.read_text(encoding="utf-8"))["windows"]["actividad"]["x"] == 0.5


@pytest.mark.parametrize(
    "content",
    [
        "esto no es JSON",
        "[]",
        '{"windows": []}',
        '{"windows": {"actividad": {"open": true}}}',
        '{"windows": {"actividad": {"open": true, "x": "a", "y": 0, "width": 1, "height": 1, '
        '"order": 0}}}',
    ],
)
def test_un_archivo_ilegible_o_incompleto_deja_la_disposicion_inicial(tmp_path, content):
    path = tmp_path / "ventanas.json"
    path.write_text(content, encoding="utf-8")
    model = WorkspaceModel(SPECS, LayoutStore(path))
    assert geometry(model, "actividad") == (0.0, 0.0, 0.2, 0.5)
    assert rows(model, "open") == [True, False, False]


def test_una_disposicion_guardada_fuera_del_area_se_recoloca_y_una_ventana_nueva_usa_la_inicial(
    tmp_path,
):
    path = tmp_path / "ventanas.json"
    saved = {"open": True, "x": 3.0, "y": -1.0, "width": 0.5, "height": 0.5, "order": 4}
    path.write_text(json.dumps({"windows": {"comandos": saved, "antigua": saved}}), "utf-8")
    model = WorkspaceModel(SPECS, LayoutStore(path))
    assert geometry(model, "comandos") == (0.5, 0.0, 0.5, 0.5)
    assert geometry(model, "busqueda") == (0.0, 0.5, 0.2, 0.5)  # no estaba en el archivo


def test_una_ventana_apartada_sigue_apartada_al_volver(tmp_path):
    path = tmp_path / "ventanas.json"
    model = WorkspaceModel(SPECS, LayoutStore(path))
    model.set_aside("actividad")
    model.save()
    again = WorkspaceModel(SPECS, LayoutStore(path))
    assert rows(again, "aside") == [True, False, False]


def test_una_disposicion_guardada_sin_apartar_se_lee_como_no_apartada(tmp_path):
    path = tmp_path / "ventanas.json"
    saved = {"open": True, "x": 0.1, "y": 0.1, "width": 0.3, "height": 0.3, "order": 0}
    path.write_text(json.dumps({"windows": {"actividad": saved}}), encoding="utf-8")
    assert rows(WorkspaceModel(SPECS, LayoutStore(path)), "aside") == [False, False, False]


def test_sin_archivo_no_se_guarda_nada(model):
    model.move("actividad", 0.5, 0.5)
    model.save()
    assert not model._save_timer.isActive()


def test_cada_ventana_tiene_una_forma_de_marco_conocida_y_el_modelo_la_expone():
    from jarvis_assistant.ui.workspace import FRAME_STYLES

    assert {spec.style for spec in WINDOWS} <= set(FRAME_STYLES)
    assert len({spec.style for spec in WINDOWS}) > 1  # no son todas iguales
    full = WorkspaceModel(WINDOWS)
    assert rows(full, "style") == [spec.style for spec in WINDOWS]
