"""Toda la interfaz QML sin pantalla (T-2.9) y la caja de texto real (entrada-texto.md).

Se carga cada archivo QML, se crean las dos ventanas y se recorre la vista previa completa,
acelerada: no debe aparecer ningún error ni aviso de QML.
"""
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from jarvis_assistant.config import Config, Profile, UiSettings
from jarvis_assistant.core import events
from jarvis_assistant.core.content import CatalogItem
from jarvis_assistant.core.events import Activity
from jarvis_assistant.ui.app import FONTS_DIR, QML_DIR, UiApp, load_fonts
from jarvis_assistant.ui.preview import PreviewDriver, panel_tour, script
from jarvis_assistant.ui.view_models import (
    PLACEHOLDER_ASLEEP,
    PLACEHOLDER_ATTENDING,
    PLACEHOLDER_RESTING,
)
from jarvis_assistant.ui.workspace import WINDOWS

QML_FILES = sorted(QML_DIR.rglob("*.qml"))


@pytest.fixture
def make_ui(qtbot):
    created = []

    def make(**kwargs):
        published = []
        settings = kwargs.pop("settings", UiSettings())
        ui = UiApp(publish=published.append, settings=settings, **kwargs)
        created.append(ui)
        return ui, published

    yield make
    for ui in created:
        ui.shutdown()
        ui.screen.close()
        ui.hud_window.close()
        ui.engine.deleteLater()


def input_of(window) -> QQuickItem:
    item = window.findChild(QObject, "commandInput")
    assert item is not None
    return item


def type_text(window, text: str) -> None:
    for char in text:
        QTest.keyClick(window, char)


# --- Carga -------------------------------------------------------------------------------------


def test_hay_qml_de_todas_las_partes_de_la_interfaz():
    names = {path.relative_to(QML_DIR).as_posix() for path in QML_FILES}
    assert {
        "Theme.qml", "SessionScreen.qml", "HudOverlay.qml", "orb/Orb.qml", "orb/MiniOrb.qml",
        "components/PanelFrame.qml", "components/TaskCard.qml", "components/StatusDot.qml",
        "components/Subtitles.qml", "components/StateLabel.qml", "components/Badge.qml",
        "components/EmptyState.qml", "components/IconButton.qml", "panels/ActivityPanel.qml",
        "Workspace.qml", "components/FloatingWindow.qml", "components/Dock.qml",
        "components/ToolBar.qml", "components/TextField.qml", "components/Chip.qml",
        "orb/NeuralNet.qml", "orb/GyroArcs.qml", "orb/Satellites.qml", "orb/Glyphs.qml",
        "orb/LifeField.qml", "orb/Constellation.qml", "orb/SatelliteOrbs.qml", "orb/Dust.qml",
        "orb/Lattice.qml", "orb/Accretion.qml", "components/DialogCard.qml",
    } <= names  # fmt: skip


@pytest.mark.parametrize("path", QML_FILES, ids=lambda p: p.relative_to(QML_DIR).as_posix())
def test_cada_archivo_qml_compila_sin_errores(qapp, path: Path):
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
    assert not component.isError(), [error.toString() for error in component.errors()]


def test_las_fuentes_incluidas_se_registran(qapp):
    assert sorted(path.name for path in FONTS_DIR.glob("*.ttf")) == [
        "Inter-Medium.ttf", "Inter-Regular.ttf", "JetBrainsMono-Regular.ttf",
        "Orbitron-Variable.ttf", "Rajdhani-SemiBold.ttf",
    ]  # fmt: skip
    assert {"Inter", "JetBrains Mono", "Orbitron", "Rajdhani"} <= set(load_fonts())


@pytest.mark.parametrize("quality", ["high", "medium", "low"])
@pytest.mark.parametrize("reduce_motion", [False, True])
def test_la_vista_previa_completa_recorre_todo_sin_avisos_de_qml(
    make_ui, qtbot, quality, reduce_motion
):
    ui, _ = make_ui(settings=UiSettings(quality=quality, reduce_motion=reduce_motion), debug=True)
    ui.start()
    seen = set()
    driver = PreviewDriver(lambda e: (ui.on_event(e), seen.add(ui.assistant.activity)),
                           speed=120, loop=False)
    driver.start()
    # Una parte con el HUD a la vista, como si el usuario hubiera pasado a otra ventana.
    qtbot.wait(150)
    ui._execute(ui.controller.screen_active_changed(False))
    # El plazo es solo una red de seguridad: con calidad alta y todo el movimiento, el
    # renderizado sin pantalla retrasa los temporizadores y el recorrido ronda los 20 s.
    qtbot.waitUntil(lambda: driver.finished_rounds == 1, timeout=60_000)
    qtbot.wait(150)
    assert seen == {activity.value for activity in Activity}
    assert ui.warnings == []


def test_el_orbe_distingue_reposo_de_despierto(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    orb = ui.screen.findChild(QObject, "orb")
    assert orb is not None
    ui.on_event(events.AssistantActivityChanged("IDLE", Activity.REPOSO))
    qtbot.wait(600)  # fundido corto (motion.state)
    assert 0 < orb.property("brightness") <= 0.25
    assert orb.property("energy") < 0.1
    assert orb.property("chaos") == 0
    assert orb.property("live") == 0
    ui.on_event(events.AssistantActivityChanged("LISTENING_COMMAND", Activity.PROCESANDO))
    qtbot.wait(600)
    assert orb.property("brightness") == 1
    assert orb.property("energy") == 1
    assert orb.property("chaos") == 1
    assert orb.property("live") == 1


# --- Ventanas ---------------------------------------------------------------------------------


def test_al_arrancar_la_pantalla_se_ve_en_dormido_y_el_hud_no(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    assert ui.screen.isVisible()
    assert not ui.hud_window.isVisible()
    assert ui.screen.visibility() == ui.screen.Visibility.FullScreen
    flags = ui.hud_window.flags()
    for flag in (Qt.WindowType.Tool, Qt.WindowType.FramelessWindowHint,
                 Qt.WindowType.WindowStaysOnTopHint, Qt.WindowType.WindowDoesNotAcceptFocus):
        assert flags & flag


def test_el_hud_aparece_sin_activarse_y_solo_acepta_el_foco_con_un_clic_en_su_caja(
    make_ui, qtbot, tmp_path
):
    from fakes.platform import FakePlatform

    platform = FakePlatform(tmp_path)
    ui, _ = make_ui(platform=platform)
    ui.start()
    assert platform.calls[0][0] == "bring_own_window_to_front"
    ui.on_event(events.SessionOpened(1, "2026-11-14"))
    ui._execute(ui.controller.screen_active_changed(False))
    assert ui.hud_window.isVisible()
    assert ui.hud_window.flags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert platform.calls[-1] == ("make_non_activating", (int(ui.hud_window.winId()), True))
    ui.hudInputPressed()
    assert not ui.hud_window.flags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert platform.calls[-1] == ("make_non_activating", (int(ui.hud_window.winId()), False))


def test_cerrar_la_pantalla_la_oculta_y_mostrar_pantalla_la_devuelve(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-14"))
    assert not ui.screen.close()  # se rechaza: el proceso sigue en la bandeja
    assert not ui.screen.isVisible()
    assert ui.hud_window.isVisible()  # hay sesión
    ui.on_event(events.ShowScreenRequested(True))
    assert ui.screen.isVisible() and not ui.hud_window.isVisible()
    ui.on_event(events.ShowScreenRequested(False))
    assert ui.screen.visibility() == ui.screen.Visibility.Minimized
    assert ui.hud_window.isVisible()


def test_el_boton_del_hud_abre_la_pantalla(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-14"))
    ui._execute(ui.controller.screen_active_changed(False))
    assert ui.hud_window.isVisible()
    button = ui.hud_window.findChild(QObject, "hudOpenScreen")
    assert button is not None and button.property("visible")
    button.clicked.emit()
    assert ui.screen.isVisible() and not ui.hud_window.isVisible()


def test_mostrar_pantalla_tras_minimizarla_la_restaura_antes_de_pantalla_completa(
    make_ui, qtbot, monkeypatch
):
    # En Windows, pasar de minimizada a pantalla completa sin restaurar antes deja la
    # ventana con un tamaño intermedio: solo se veía parte de la pantalla. La plataforma
    # `offscreen` de las pruebas no lo reproduce, así que se comprueba el orden de llamadas.
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-14"))
    ui.on_event(events.ShowScreenRequested(False))
    assert ui.screen.visibility() == ui.screen.Visibility.Minimized
    calls: list[str] = []
    for name in ("showNormal", "showFullScreen"):
        original = getattr(ui.screen, name)
        monkeypatch.setattr(ui.screen, name,
                            lambda n=name, f=original: (calls.append(n), f())[1])
    ui.hudOpenScreen()
    assert calls == ["showNormal", "showFullScreen"]
    assert ui.screen.visibility() == ui.screen.Visibility.FullScreen


def test_mostrar_pantalla_sin_minimizar_no_la_restaura(make_ui, qtbot, monkeypatch):
    # Restaurar a tamaño normal sin necesidad haría parpadear la ventana.
    ui, _ = make_ui()
    ui.start()
    calls: list[str] = []
    monkeypatch.setattr(ui.screen, "showNormal", lambda: calls.append("showNormal"))
    ui.on_event(events.ShowScreenRequested(True))
    assert calls == []
    assert ui.screen.visibility() == ui.screen.Visibility.FullScreen


def test_al_salir_la_pantalla_acepta_el_cierre(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.shutdown()
    assert ui.screen.close()


def test_el_cierre_de_sesion_oculta_el_hud_al_terminar_la_animacion(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-14"))
    ui._execute(ui.controller.screen_active_changed(False))
    ui.on_event(events.SessionClosed())
    assert ui.hud_window.isVisible()
    qtbot.waitUntil(lambda: not ui.hud_window.isVisible(), timeout=3000)
    assert ui.screen.isVisible()  # la pantalla queda en su aspecto de dormido


# --- Ventanas flotantes -----------------------------------------------------------------------

LEFT = Qt.MouseButton.LeftButton
NO_KEYS = Qt.KeyboardModifier.NoModifier
HEADER = 39  # cabecera de la ventana y su línea
PADDING = 12  # margen del contenido


def visual(ui, name: str) -> QQuickItem:
    """Elemento por su `objectName`, por el árbol visual: los delegados de un `Repeater` no
    cuelgan de la ventana como `QObject`."""
    pending = [ui.screen.contentItem()]
    while pending:
        item = pending.pop()
        if item.objectName() == name:
            return item
        pending.extend(item.childItems())
    raise AssertionError(f"No hay ningún elemento «{name}»")


def floating(ui, window_id: str) -> QQuickItem:
    return visual(ui, f"window-{window_id}")


def shown(ui, qtbot, window_id: str) -> QQuickItem:
    """Abre la ventana y espera a que su contenido esté colocado: las filas y columnas de
    QML se colocan en el siguiente fotograma."""
    ui.workspace.show(window_id)
    window = floating(ui, window_id)
    qtbot.waitUntil(window.isVisible, timeout=2000)
    qtbot.wait(150)
    return window


def scene(item: QQuickItem, x: float, y: float) -> QPoint:
    return item.mapToScene(QPointF(x, y)).toPoint()


def click(ui, item: QQuickItem, x: float, y: float) -> None:
    QTest.mouseClick(ui.screen, LEFT, NO_KEYS, scene(item, x, y))


def drag(ui, start: QPoint, dx: int, dy: int) -> None:
    QTest.mousePress(ui.screen, LEFT, NO_KEYS, start)
    QTest.mouseMove(ui.screen, start + QPoint(dx // 2, dy // 2))
    QTest.mouseMove(ui.screen, start + QPoint(dx, dy))
    QTest.mouseRelease(ui.screen, LEFT, NO_KEYS, start + QPoint(dx, dy))


@pytest.fixture
def desk(make_ui, qtbot):
    """Interfaz con la sesión abierta y la ventana de actividad a la vista."""
    ui, published = make_ui(settings=UiSettings(reduce_motion=True))
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-15"))
    qtbot.waitUntil(lambda: floating(ui, "actividad").isVisible(), timeout=3000)
    qtbot.wait(450)  # las ventanas terminan de aparecer
    return ui, published


def test_en_dormido_no_hay_ventanas_flotantes_y_con_la_sesion_se_ve_la_de_actividad(
    make_ui, qtbot
):
    ui, _ = make_ui(settings=UiSettings(reduce_motion=True))
    ui.start()
    assert not floating(ui, "actividad").isVisible()
    ui.on_event(events.SessionOpened(1, "2026-11-15"))
    qtbot.waitUntil(lambda: floating(ui, "actividad").isVisible(), timeout=3000)
    assert not floating(ui, "comandos").isVisible()
    assert ui.warnings == []


def test_un_modulo_que_muestra_algo_abre_su_ventana_encima_de_las_demas(desk, qtbot):
    ui, _ = desk
    ui.on_event(events.PanelActivated("comandos"))
    commands = floating(ui, "comandos")
    qtbot.waitUntil(commands.isVisible, timeout=2000)
    assert commands.z() > floating(ui, "actividad").z()
    assert commands.property("focused") and not floating(ui, "actividad").property("focused")
    assert commands.width() >= 300 and commands.height() >= 220
    assert ui.warnings == []


def test_una_ventana_se_mueve_arrastrando_su_cabecera(desk, qtbot):
    ui, _ = desk
    window = floating(ui, "actividad")
    before = (window.x(), window.y())
    drag(ui, scene(window, 120, 18), 150, 90)
    assert (window.x(), window.y()) == (before[0] + 150, before[1] + 90)
    placement = ui.workspace.placement("actividad")
    area = window.parentItem()
    assert round(placement.x * area.width()) == window.x()
    drag(ui, scene(window, 120, 18), -5000, -5000)  # no sale del área de trabajo
    assert (window.x(), window.y()) == (0, 0)
    assert ui.warnings == []


def test_una_ventana_cambia_de_tamano_desde_un_borde_o_una_esquina(desk, qtbot):
    ui, _ = desk
    window = floating(ui, "actividad")
    width, height = window.width(), window.height()
    drag(ui, scene(window, width - 3, height - 3), 60, -40)  # esquina inferior derecha
    assert (window.width(), window.height()) == (width + 60, height - 40)
    left = window.x()
    drag(ui, scene(window, width + 60 - 2, 120), -5000, 0)  # borde derecho: hasta el mínimo
    assert window.width() == 300 and window.x() == left
    assert ui.warnings == []


def test_una_ventana_se_cierra_con_su_boton_y_vuelve_desde_el_selector(desk, qtbot):
    ui, _ = desk
    window = floating(ui, "actividad")
    click(ui, window, window.width() - 18, 20)
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=2000)
    assert not ui.workspace.placement("actividad").open
    button = visual(ui, "dock-actividad")
    click(ui, button, 20, 18)
    qtbot.waitUntil(window.isVisible, timeout=2000)
    search = visual(ui, "dock-busqueda")
    click(ui, search, 20, 18)  # el selector también añade una ventana que no estaba
    qtbot.waitUntil(floating(ui, "busqueda").isVisible, timeout=2000)
    assert floating(ui, "busqueda").property("focused")
    assert ui.warnings == []


TAB = (184, 40)  # una ventana apartada: solo su cabecera
# Pestaña de arriba a la izquierda: en 800 px no cabe junto al selector y baja una fila.
CORNER = (8, 56)


def test_triple_clic_en_la_cabecera_aparta_la_ventana_y_un_clic_la_recupera(desk, qtbot):
    ui, _ = desk
    window = floating(ui, "actividad")
    size = (window.width(), window.height())
    place = (window.x(), window.y())
    for _ in range(3):
        click(ui, window, 120, 18)
    assert ui.workspace.placement("actividad").aside
    qtbot.waitUntil(lambda: (window.width(), window.height()) == TAB, timeout=2000)
    # Arriba a la izquierda: se aparta a esa esquina.
    qtbot.waitUntil(lambda: (window.x(), window.y()) == CORNER, timeout=2000)
    drag(ui, scene(window, TAB[0] - 3, TAB[1] - 3), 200, 200)  # apartada no cambia de tamaño
    assert (window.width(), window.height()) == TAB
    click(ui, window, 60, 20)
    assert not ui.workspace.placement("actividad").aside
    qtbot.waitUntil(lambda: (window.width(), window.height()) == size, timeout=2000)
    assert (window.x(), window.y()) == place
    assert ui.warnings == []


def test_el_boton_del_selector_aparta_todas_sin_que_se_tapen(desk, qtbot):
    ui, _ = desk
    for window_id in ("historial", "busqueda", "comandos"):
        ui.workspace.show(window_id)
    ui.workspace.move("historial", 0.0, 0.0)  # dos en la misma esquina
    click(ui, visual(ui, "dock-apartar"), 20, 18)
    windows = [floating(ui, name) for name in ("actividad", "historial", "busqueda", "comandos")]
    assert all(ui.workspace.placement(w.property("windowId")).aside for w in windows)
    qtbot.waitUntil(
        lambda: all((w.width(), w.height()) == TAB for w in windows), timeout=2000
    )
    qtbot.wait(50)
    boxes = [(w.x(), w.y(), w.x() + w.width(), w.y() + w.height()) for w in windows]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)
    assert ui.warnings == []


def test_el_mismo_boton_devuelve_si_hay_mas_apartadas(desk, qtbot):
    ui, _ = desk
    ui.workspace.show("busqueda")
    button = visual(ui, "dock-apartar")
    click(ui, button, 20, 18)  # 2 a la vista: aparta
    assert ui.workspace.asideCount == 2
    window = floating(ui, "actividad")
    qtbot.waitUntil(lambda: (window.width(), window.height()) == TAB, timeout=2000)
    click(ui, button, 20, 18)  # 2 apartadas: devuelve
    assert ui.workspace.asideCount == 0
    qtbot.waitUntil(lambda: window.width() > TAB[0], timeout=2000)
    assert ui.warnings == []


def test_aparta_por_orden_escrita(desk, qtbot):
    ui, _ = desk
    ui.on_event(events.WindowAsideRequested("Actividad"))
    window = floating(ui, "actividad")
    qtbot.waitUntil(lambda: (window.width(), window.height()) == TAB, timeout=2000)
    qtbot.waitUntil(lambda: (window.x(), window.y()) == CORNER, timeout=2000)
    click(ui, window, TAB[0] - 18, 20)  # su botón la cierra del todo
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=2000)
    assert not ui.workspace.placement("actividad").open
    assert ui.warnings == []


def test_con_animaciones_la_ventana_viaja_hasta_su_pestana_y_vuelve(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-16"))
    window = floating(ui, "actividad")
    qtbot.waitUntil(lambda: window.isVisible() and window.property("launch") == 1, timeout=5000)
    size = (window.width(), window.height())
    ui.workspace.set_aside("actividad")
    qtbot.wait(100)
    assert TAB[0] < window.width() < size[0]  # a medio camino
    qtbot.waitUntil(lambda: (window.width(), window.height()) == TAB, timeout=2000)
    qtbot.waitUntil(lambda: (window.x(), window.y()) == CORNER, timeout=2000)
    assert window.rotation() == 0
    ui.workspace.restore("actividad")
    qtbot.waitUntil(lambda: (window.width(), window.height()) == size, timeout=2000)
    assert ui.warnings == []


def test_pulsar_una_ventana_la_trae_al_frente(desk, qtbot):
    ui, _ = desk
    ui.workspace.show("historial")
    activity = floating(ui, "actividad")
    assert not activity.property("focused")
    click(ui, activity, 60, activity.height() - 30)
    assert activity.property("focused")
    assert activity.z() > floating(ui, "historial").z()


def test_pulsar_una_ventana_avisa_al_nucleo(desk, qtbot):
    ui, published = desk
    window = floating(ui, "actividad")
    published.clear()
    drag(ui, scene(window, 120, 18), 40, 20)  # mover la cabecera también cuenta
    click(ui, window, 60, window.height() - 30)
    assert [e for e in published if isinstance(e, events.WindowPressed)] == [
        events.WindowPressed(), events.WindowPressed(),
    ]  # fmt: skip
    assert ui.warnings == []


def test_la_barra_de_herramientas_de_comandos_pide_las_acciones_del_modulo(desk, qtbot):
    ui, published = desk
    ui.on_event(events.WorkdirChanged(str(Path("C:/Users/usuario/Proyectos"))))
    window = shown(ui, qtbot, "comandos")
    published.clear()
    for button in range(5):  # subir, inicio, actualizar, árbol y terminal
        click(ui, window, PADDING + 14 + 30 * button, HEADER + PADDING + 14)
    actions = [(e.module, e.action) for e in published if isinstance(e, events.ActionRequested)]
    assert actions == [
        ("comandos", "cd"), ("comandos", "ls"), ("comandos", "cd"), ("comandos", "ls"),
        ("comandos", "ls"), ("comandos", "arbol"), ("comandos", "abrir_consola"),
    ]  # fmt: skip
    assert ui.warnings == []


def test_la_ventana_de_busqueda_busca_lo_que_se_escribe_en_su_campo(desk, qtbot):
    ui, published = desk
    window = shown(ui, qtbot, "busqueda")
    published.clear()
    click(ui, window, 120, HEADER + PADDING + 15)
    type_text(ui.screen, "informe")
    QTest.keyClick(ui.screen, Qt.Key.Key_Return)
    requests = [e for e in published if isinstance(e, events.ActionRequested)]
    assert [(e.module, e.action, dict(e.params)) for e in requests] == [
        ("busqueda", "buscar", {"consulta": "informe", "tipo": "ambos"})
    ]
    assert input_of(ui.screen).property("text") == ""  # no ha ido a la caja de órdenes
    assert ui.warnings == []


def test_un_ejemplo_de_la_ayuda_se_escribe_en_la_caja_de_ordenes_sin_enviarlo(desk, qtbot):
    ui, published = desk
    ui.assistant.suggest("Abre GitHub")
    assert input_of(ui.screen).property("text") == "Abre GitHub"
    assert not [e for e in published if isinstance(e, events.TextSubmitted)]


def test_todas_las_ventanas_abiertas_con_contenido_no_dan_avisos_de_qml(desk, qtbot):
    ui, _ = desk
    for spec_id in ("comandos", "aperturas", "busqueda", "historial", "ayuda"):
        ui.workspace.show(spec_id)
    ui.on_event(events.OrderQueueChanged(("lista", "árbol")))
    for step in panel_tour():
        ui.on_event(step.event)
    qtbot.wait(300)
    assert all(floating(ui, spec.id).isVisible() for spec in WINDOWS if not spec.admin)
    # Las del Acedor no se abren fuera de su sesión.
    assert not any(floating(ui, spec.id).isVisible() for spec in WINDOWS if spec.admin)
    ui.workspace.reset()
    qtbot.wait(300)
    assert floating(ui, "actividad").isVisible() and not floating(ui, "ayuda").isVisible()
    assert ui.warnings == []


def test_el_perfil_elegido_se_ve_en_dormido_y_se_cambia_con_las_flechas(make_ui, qtbot):
    ui, published = make_ui()
    ui.start()
    config = Config(profiles=(Profile("a", "Trabajo"), Profile("b", "Casa")))
    ui.on_event(events.ConfigApplied(config))
    ui.on_event(events.AssistantActivityChanged("DORMIDO", Activity.DORMIDO))
    picker = ui.screen.findChild(QObject, "profilePicker")
    qtbot.waitUntil(lambda: picker.property("opacity") == 1, timeout=2000)
    box = input_of(ui.screen)
    qtbot.waitUntil(lambda: box.hasActiveFocus(), timeout=2000)
    assert visual(ui, "profile-0").property("selected")
    QTest.keyClick(ui.screen, Qt.Key.Key_Right)
    selected = [e.profile_id for e in published if isinstance(e, events.ProfileSelected)]
    assert selected == ["a", "b"]
    assert visual(ui, "profile-1").property("selected")
    assert not visual(ui, "profile-0").property("selected")
    assert ui.warnings == []


def test_al_cerrar_sesion_los_perfiles_esperan_al_final_de_la_animacion(make_ui, qtbot):
    ui, _ = make_ui(open_settings=lambda: None)
    ui.start()
    config = Config(profiles=(Profile("a", "Trabajo"), Profile("b", "Casa")))
    ui.on_event(events.ConfigApplied(config))
    ui.on_event(events.SessionOpened(1, "Trabajo", "a"))
    ui.on_event(events.AssistantActivityChanged("LISTENING_COMMAND", Activity.ESCUCHANDO))
    ui.on_event(events.AssistantActivityChanged("DORMIDO", Activity.DORMIDO))
    ui.on_event(events.SessionClosed())
    picker = ui.screen.findChild(QObject, "profilePicker")
    orb = ui.screen.findChild(QObject, "orb")
    assert orb.property("inTransition")
    assert not picker.property("shown")
    assert not visual(ui, "settingsButton").isVisible()
    qtbot.waitUntil(lambda: picker.property("opacity") == 1, timeout=5000)
    assert not orb.property("inTransition")
    assert visual(ui, "settingsButton").isVisible()
    assert ui.warnings == []


def test_con_un_solo_perfil_no_hay_selector(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.ConfigApplied(Config()))
    picker = ui.screen.findChild(QObject, "profilePicker")
    qtbot.wait(300)
    assert picker.property("opacity") == 0


# --- Caja de texto (entrada-texto.md, criterios de aceptación) --------------------------------


def test_enter_publica_el_texto_y_vacia_la_caja(make_ui, qtbot):
    ui, published = make_ui()
    ui.start()
    box = input_of(ui.screen)
    qtbot.waitUntil(lambda: box.hasActiveFocus(), timeout=2000)
    type_text(ui.screen, "Hey Jarvis")
    QTest.keyClick(ui.screen, Qt.Key.Key_Return)
    assert events.TextSubmitted("Hey Jarvis") in published
    assert box.property("text") == ""
    assert box.hasActiveFocus()  # el foco se queda en la caja


def test_un_envio_vacio_no_publica_nada(make_ui, qtbot):
    ui, published = make_ui()
    ui.start()
    box = input_of(ui.screen)
    qtbot.waitUntil(lambda: box.hasActiveFocus(), timeout=2000)
    QTest.keyClick(ui.screen, Qt.Key.Key_Space)
    QTest.keyClick(ui.screen, Qt.Key.Key_Return)
    assert [e for e in published if isinstance(e, events.TextSubmitted)] == []
    assert box.property("text") == ""


def test_teclear_avisa_como_mucho_una_vez_por_segundo_y_el_codigo_no_cuenta(make_ui, qtbot):
    now = [100.0]
    ui, published = make_ui(monotonic=lambda: now[0])
    ui.start()
    box = input_of(ui.screen)
    qtbot.waitUntil(lambda: box.hasActiveFocus(), timeout=2000)
    box.setProperty("text", "hola")
    assert published == []
    type_text(ui.screen, "abre")
    assert published == [events.UserTyping()]
    now[0] += 1.1
    type_text(ui.screen, " x")
    assert published == [events.UserTyping(), events.UserTyping()]


def test_el_texto_de_ayuda_sigue_al_estado(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    for state, value, placeholder in [
        ("DORMIDO", Activity.DORMIDO, PLACEHOLDER_ASLEEP),
        ("LISTENING_COMMAND", Activity.ESCUCHANDO, PLACEHOLDER_ATTENDING),
        ("AWAITING_PARAMETER", Activity.ESPERANDO, PLACEHOLDER_ATTENDING),
        ("IDLE", Activity.REPOSO, PLACEHOLDER_RESTING),
    ]:
        ui.on_event(events.AssistantActivityChanged(state, value))
        texts = [item.property("text") for item in ui.screen.findChildren(QQuickItem)]
        assert placeholder in texts


def test_dormido_se_ve_lo_que_se_escribe(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    box = input_of(ui.screen)
    ui.on_event(events.AssistantActivityChanged("DORMIDO", Activity.DORMIDO))
    box.setProperty("text", "hy jarvs")
    assert box.property("displayText") == "hy jarvs"


def test_la_configuracion_se_abre_desde_la_pantalla_dormida_y_bloquea_el_inicio(make_ui, qtbot):
    opened = []
    ui, _ = make_ui(open_settings=lambda: opened.append(True))
    ui.start()
    ui.on_event(events.AssistantActivityChanged("DORMIDO", Activity.DORMIDO))
    button = visual(ui, "settingsButton")
    qtbot.waitUntil(button.isVisible, timeout=2000)
    center = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
    QTest.mouseClick(ui.screen, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
    assert opened == [True]
    ui.set_configuring(True)
    assert not input_of(ui.screen).isEnabled()
    ui.set_configuring(False)
    assert input_of(ui.screen).isEnabled()
    ui.on_event(events.AssistantActivityChanged("LISTENING_COMMAND", Activity.ESCUCHANDO))
    qtbot.waitUntil(lambda: not button.isVisible(), timeout=2000)
    assert ui.warnings == []


def test_sin_ventana_de_configuracion_no_hay_boton(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    ui.on_event(events.AssistantActivityChanged("DORMIDO", Activity.DORMIDO))
    qtbot.wait(100)
    assert not visual(ui, "settingsButton").isVisible()


def test_la_vista_previa_tiene_todos_los_estados():
    activities = {step.event.activity for step in script()
                  if isinstance(step.event, events.AssistantActivityChanged)}
    assert activities == set(Activity)
    kinds = {type(step.event) for step in script()}
    assert {events.SessionOpened, events.RestEntered, events.ListeningResumed,
            events.SessionClosed, events.TaskUpdated, events.DialogueOpened} <= kinds


# --- Sincronía de la animación con la frase (RNF-22, T-2.8) -----------------------------------


def test_el_inicio_de_cada_animacion_queda_en_el_registro_con_su_marca_de_tiempo(
    make_ui, qtbot, caplog
):
    now = [42.125]
    ui, _ = make_ui(monotonic=lambda: now[0])
    ui.start()
    with caplog.at_level("DEBUG", logger="jarvis_assistant.ui.app"):
        ui.on_event(events.SessionOpened(1, "2026-11-14"))
        now[0] = 50.5
        ui._execute(ui.controller.screen_active_changed(False))
        ui.on_event(events.RestEntered())
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Inicio")]
    assert lines == [
        "Inicio de la animación wake (pantalla): 42.125",
        "Inicio de la animación sleep_rest (pantalla): 50.500",
        "Inicio de la animación sleep_rest (HUD): 50.500",
    ]


# --- Diálogo (T-4.2) -------------------------------------------------------------------------


def test_la_tarjeta_de_dialogo_muestra_la_pregunta_y_se_retira_al_cerrarla(make_ui, qtbot):
    ui, _ = make_ui()
    ui.start()
    cards = [ui.screen.findChild(QObject, "dialogCard"),
             ui.hud_window.findChild(QObject, "hudDialogCard")]  # fmt: skip
    assert all(card is not None for card in cards)
    assert not any(card.property("shown") for card in cards)
    ui.on_event(events.DialogueOpened("¿Elimino la sesión 12, pruebas?", "BOOLEAN",
                                      ("Sí", "No", "Cancelar"), 20.0,
                                      {"id": 12, "nombre": "pruebas"}))  # fmt: skip
    qtbot.waitUntil(lambda: all(card.property("opacity") == 1 for card in cards), timeout=3000)
    question = ui.screen.findChild(QObject, "dialogQuestion")
    assert question.property("text") == "¿Elimino la sesión 12, pruebas?"
    qtbot.wait(300)
    assert 0 < cards[0].property("remaining") < 1  # la barra se vacía con el tiempo
    ui.on_event(events.DialogueClosed("answered"))
    qtbot.waitUntil(lambda: not any(card.property("visible") for card in cards), timeout=3000)
    assert ui.warnings == []


# --- Perfiles protegidos -----------------------------------------------------------------------


def find_item(ui, name: str) -> QQuickItem:
    item = ui.screen.findChild(QObject, name)
    assert item is not None, name
    return item


def test_la_caja_de_la_contrasena_no_muestra_lo_que_se_escribe_y_lo_envia(make_ui, qtbot):
    ui, published = make_ui(settings=UiSettings(reduce_motion=True))
    ui.start()
    ui.on_event(events.AccessChallenged("secreto", "Confidencial"))
    gate = find_item(ui, "accessGate")
    field = find_item(ui, "accessInput")
    qtbot.waitUntil(lambda: gate.isVisible() and field.hasActiveFocus(), timeout=3000)
    assert not input_of(ui.screen).isEnabled()
    type_text(ui.screen, "abcd")
    assert field.property("displayText") == ""
    QTest.keyClick(ui.screen, Qt.Key.Key_Return)
    assert published[-1] == events.AccessAttempted("abcd")
    assert field.property("text") == ""
    ui.on_event(events.AccessDenied())
    qtbot.waitUntil(
        lambda: find_item(ui, "accessMessage").property("text") != "", timeout=2000
    )
    QTest.keyClick(ui.screen, Qt.Key.Key_Escape)
    assert published[-1] == events.AccessCancelled()
    ui.on_event(events.AccessClosed())
    qtbot.waitUntil(lambda: not gate.isVisible(), timeout=3000)
    assert input_of(ui.screen).isEnabled()
    assert ui.warnings == []


def test_la_tarjeta_de_intrusion_se_confirma_con_entendido(make_ui, qtbot):
    from datetime import UTC, datetime

    from jarvis_assistant.core.content import IntrusionItem

    ui, published = make_ui(settings=UiSettings(reduce_motion=True))
    ui.start()
    ui.on_event(events.SessionOpened(1, "2026-11-17", "secreto"))
    alert = IntrusionItem(3, datetime(2026, 11, 17, 10, 0, tzinfo=UTC), 3, "inicio")
    ui.on_event(events.IntrusionAlertsShown("secreto", (alert,)))
    card = find_item(ui, "intrusionCard")
    qtbot.waitUntil(card.isVisible, timeout=3000)
    button = find_item(ui, "intrusionAcknowledge")
    centre = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
    QTest.mouseClick(ui.screen, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
    qtbot.waitUntil(lambda: not card.isVisible(), timeout=3000)
    assert published[-1] == events.IntrusionAcknowledged((3,))
    assert ui.warnings == []


def test_el_medidor_de_recursos_esta_en_una_esquina_inferior_y_mide_mientras_se_ve(desk, qtbot):
    ui, _ = desk
    meter = visual(ui, "resourceMeter")
    qtbot.waitUntil(lambda: ui.resources.watching, timeout=2000)
    corner = meter.mapToScene(QPointF(0, 0))
    assert corner.x() + meter.width() > ui.screen.width() / 2  # abajo a la derecha
    assert corner.y() + meter.height() > ui.screen.height() * 0.8
    assert visual(ui, "usage-ram").property("value") > 0
    assert "WindowSpec" not in str(ui.workspace.component("recursos"))  # no es una ventana
    assert ui.workspace.component("recursos") == ""
    button = visual(ui, "dock-recursos")
    click(ui, button, 20, 18)
    qtbot.waitUntil(lambda: not meter.isVisible(), timeout=2000)
    assert not ui.resources.watching
    click(ui, button, 20, 18)
    qtbot.waitUntil(lambda: meter.isVisible() and ui.resources.watching, timeout=2000)
    assert ui.warnings == []


def test_un_triple_clic_pasa_el_medidor_a_la_otra_esquina_y_las_pestanas_lo_rodean(desk, qtbot):
    ui, _ = desk
    meter = visual(ui, "resourceMeter")
    size = (meter.width(), meter.height())
    for _ in range(3):
        click(ui, meter, meter.width() / 2, meter.height() / 2)
    assert ui.resources.corner == "left" and ui.noise.corner == "right"  # el de ruido, enfrente
    qtbot.waitUntil(lambda: meter.mapToScene(QPointF(0, 0)).x() < ui.screen.width() / 2,
                    timeout=2000)
    assert (meter.width(), meter.height()) == size  # no cambia de tamaño
    # Abajo a la izquierda: su pestaña queda a la derecha del medidor, sin taparlo.
    ui.workspace.show("busqueda")
    ui.workspace.set_aside("busqueda")
    tab = floating(ui, "busqueda")
    qtbot.waitUntil(lambda: (tab.width(), tab.height()) == TAB, timeout=2000)
    right = meter.mapToScene(QPointF(meter.width(), 0)).x()
    qtbot.waitUntil(lambda: tab.mapToScene(QPointF(0, 0)).x() > right, timeout=2000)
    assert ui.warnings == []


@pytest.fixture
def microphone(monkeypatch):
    """Micrófono falso para el medidor de ruido: guarda los flujos abiertos."""
    import numpy as np

    from jarvis_assistant.ui import noise

    class Stream:
        def __init__(self, on_block) -> None:
            self.on_block = on_block
            self.closed = False

        def stop(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

        def feed(self, amplitude: float) -> None:
            self.on_block(np.full(480, amplitude, dtype=np.float32))

    streams: list[Stream] = []

    def open_input(on_block) -> Stream:
        streams.append(Stream(on_block))
        return streams[-1]

    monkeypatch.setattr(noise, "open_input", open_input)
    return streams


def left_of(item: QQuickItem) -> float:
    return item.mapToScene(QPointF(0, 0)).x()


def test_el_medidor_de_ruido_va_en_la_esquina_opuesta_al_de_recursos_y_mide_mientras_se_ve(
    desk, qtbot, microphone
):
    ui, _ = desk
    resources = visual(ui, "resourceMeter")
    meter = visual(ui, "noiseMeter")
    assert not meter.isVisible() and microphone == []  # empieza oculto, sin micrófono
    button = visual(ui, "dock-ruido")
    click(ui, button, 20, 18)
    qtbot.waitUntil(lambda: meter.isVisible() and ui.noise.watching, timeout=2000)
    assert len(microphone) == 1
    # Los tres círculos no caben en una esquina: abajo a la izquierda, a la misma altura.
    assert ui.noise.corner == "left" and ui.resources.corner == "right"
    qtbot.waitUntil(lambda: left_of(meter) < 60, timeout=2000)
    assert left_of(meter) + meter.width() < left_of(resources)
    bottom = meter.mapToScene(QPointF(0, meter.height())).y()
    assert bottom == pytest.approx(resources.mapToScene(QPointF(0, resources.height())).y())
    microphone[0].feed(0.01)
    qtbot.waitUntil(lambda: visual(ui, "noise-db").property("value") > 0, timeout=2000)
    click(ui, button, 20, 18)
    qtbot.waitUntil(lambda: not meter.isVisible(), timeout=2000)
    assert not ui.noise.watching and microphone[0].closed
    assert ui.warnings == []


def test_el_triple_clic_del_de_ruido_cambia_de_esquina_los_dos_aunque_uno_este_oculto(
    desk, qtbot, microphone
):
    ui, _ = desk
    resources = visual(ui, "resourceMeter")
    meter = visual(ui, "noiseMeter")
    ui.resources.toggle()  # oculta el de recursos
    ui.noise.toggle()
    qtbot.waitUntil(lambda: meter.isVisible() and not resources.isVisible(), timeout=2000)
    qtbot.waitUntil(lambda: left_of(meter) < 60, timeout=2000)  # en su esquina, la izquierda
    for _ in range(3):
        click(ui, meter, meter.width() / 2, meter.height() / 2)
    assert ui.noise.corner == "right" and ui.resources.corner == "left"
    qtbot.waitUntil(lambda: ui.screen.width() - left_of(meter) - meter.width() < 60,
                    timeout=2000)  # en la esquina derecha
    # El de recursos aparece ya en la otra esquina, la izquierda.
    ui.resources.toggle()
    qtbot.waitUntil(resources.isVisible, timeout=2000)
    qtbot.waitUntil(lambda: left_of(resources) < 60, timeout=2000)
    assert left_of(meter) > ui.screen.width() / 2
    # Y vuelta: el triple clic del de recursos los cambia otra vez a los dos.
    for _ in range(3):
        click(ui, resources, resources.width() / 2, resources.height() / 2)
    assert ui.resources.corner == "right" and ui.noise.corner == "left"
    qtbot.waitUntil(lambda: left_of(meter) < 60, timeout=2000)
    # Abajo a la izquierda: su pestaña queda a la derecha del medidor de ruido.
    ui.workspace.show("busqueda")
    ui.workspace.set_aside("busqueda")
    tab = floating(ui, "busqueda")
    qtbot.waitUntil(lambda: (tab.width(), tab.height()) == TAB, timeout=2000)
    edge = meter.mapToScene(QPointF(meter.width(), 0)).x()
    qtbot.waitUntil(lambda: left_of(tab) > edge, timeout=2000)
    assert ui.warnings == []


def test_las_ventanas_del_acedor_muestran_su_contenido_sin_avisos(desk, qtbot):
    from jarvis_assistant.core.content import CredentialItem, NamedItem

    ui, published = desk
    normal = frozenset(spec.id for spec in WINDOWS if not spec.admin) - {"actividad", "ayuda"}
    ui.on_event(events.PermissionsApplied(normal))
    casa = NamedItem("casa", "Casa")
    ui.on_event(events.PermissionsShown(
        (casa,), (NamedItem("comandos", "Comandos"),), frozenset({("casa", "comandos")})
    ))  # fmt: skip
    ui.on_event(events.CredentialsShown((CredentialItem("trabajo", "Trabajo", "abcd"),)))
    ui.on_event(events.ProfilesListed((casa, NamedItem("trabajo", "Trabajo"))))
    for window_id in ("permisos", "credenciales", "perfiles"):
        assert shown(ui, qtbot, window_id).isVisible()
    assert not floating(ui, "comandos").isVisible()
    secret = visual(ui, "credential-trabajo")
    assert secret.property("text") != "abcd"
    eye = visual(ui, "reveal-trabajo")
    click(ui, eye, eye.width() / 2, eye.height() / 2)
    qtbot.waitUntil(lambda: secret.property("text") == "abcd", timeout=2000)
    switch = visual(ui, "permission-casa-comandos")
    click(ui, switch, switch.width() / 2, switch.height() / 2)
    assert published[-1] == events.PermissionChangeRequested("casa", "comandos", True)
    assert ui.warnings == []


def panel_of(window: QQuickItem) -> QQuickItem:
    """El panel cargado en la ventana flotante."""
    pending = [window]
    while pending:
        item = pending.pop()
        if item.property("embedded") is True:
            return item
        pending.extend(item.childItems())
    raise AssertionError("La ventana no tiene panel")


def test_cada_ventana_de_comandos_muestra_su_consola_y_la_copia_se_cierra_del_todo(desk, qtbot):
    ui, published = desk
    home, algebra = str(Path.home()), str(Path.home() / "Algebra")
    ui.on_event(events.WorkdirChanged(home))
    ui.on_event(events.PanelActivated("comandos"))
    ui.on_event(events.ConsoleOpened("comandos:protocolo-a", "Comandos · a"))
    ui.on_event(events.WorkdirChanged(algebra, "comandos:protocolo-a"))
    main, copy = floating(ui, "comandos"), floating(ui, "comandos:protocolo-a")
    qtbot.waitUntil(lambda: main.isVisible() and copy.isVisible(), timeout=2000)
    qtbot.waitUntil(lambda: panel_of(copy).property("windowId") == "comandos:protocolo-a",
                    timeout=2000)  # fmt: skip
    qtbot.waitUntil(lambda: panel_of(main).property("windowId") == "comandos", timeout=2000)
    assert copy.property("title") == "Comandos · a" and copy.property("focused")
    assert panel_of(copy).property("commands").property("path") == algebra
    assert panel_of(main).property("commands").property("path") == home
    click(ui, copy, copy.width() - 18, 20)  # ✕
    qtbot.waitUntil(lambda: "comandos:protocolo-a" not in
                    [spec.id for spec in ui.workspace.specs], timeout=2000)  # fmt: skip
    assert events.ConsoleClosed("comandos:protocolo-a") in published
    assert ui.warnings == []


def test_la_ventana_del_catalogo_anade_con_su_formulario_y_elimina_con_su_boton(desk, qtbot):
    ui, published = desk
    ui.on_event(events.CatalogShown((
        CatalogItem("pagina:GitHub", "pagina", "GitHub", "https://github.com"),
    )))  # fmt: skip
    shown(ui, qtbot, "catalogo")
    published.clear()

    def press(name: str) -> None:
        item = visual(ui, name)
        click(ui, item, item.width() / 2, item.height() / 2)
        qtbot.wait(50)

    press("catalogRemove-pagina:GitHub")
    press("catalogAdd")
    assert visual(ui, "catalogForm").isVisible()
    press("formKind-pagina")
    press("catalogName")
    type_text(ui.screen, "Docs")
    press("catalogTarget")
    type_text(ui.screen, "https://example.com")
    press("catalogSubmit")
    requests = [e for e in published if isinstance(e, events.ActionRequested)]
    assert [(e.module, e.action, dict(e.params)) for e in requests] == [
        ("catalogo", "eliminar", {"entrada": "pagina:GitHub"}),
        ("catalogo", "añadir", {"tipo": "pagina", "nombre": "Docs",
                                "destino": "https://example.com", "alias": ""}),
    ]  # fmt: skip
    assert input_of(ui.screen).property("text") == ""  # no ha ido a la caja de órdenes
    # El módulo responde con la lista nueva: el formulario se cierra.
    ui.on_event(events.CatalogShown((
        CatalogItem("pagina:GitHub", "pagina", "GitHub", "https://github.com"),
        CatalogItem("pagina:Docs", "pagina", "Docs", "https://example.com"),
    )))  # fmt: skip
    qtbot.wait(50)
    assert not visual(ui, "catalogForm").isVisible()
    assert ui.warnings == []
