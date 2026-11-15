"""Toda la interfaz QML sin pantalla (T-2.9) y la caja de texto real (entrada-texto.md).

Se carga cada archivo QML, se crean las dos ventanas y se recorre la vista previa completa,
acelerada: no debe aparecer ningún error ni aviso de QML.
"""
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from jarvis_assistant.config import UiSettings
from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity
from jarvis_assistant.ui.app import FONTS_DIR, QML_DIR, UiApp, load_fonts
from jarvis_assistant.ui.preview import PreviewDriver, script
from jarvis_assistant.ui.view_models import (
    PLACEHOLDER_ASLEEP,
    PLACEHOLDER_ATTENDING,
    PLACEHOLDER_RESTING,
)

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
        "orb/NeuralNet.qml", "orb/GyroArcs.qml", "orb/Satellites.qml", "orb/Glyphs.qml",
        "orb/LifeField.qml", "orb/Constellation.qml", "orb/SatelliteOrbs.qml", "orb/Dust.qml",
        "orb/Lattice.qml", "orb/Accretion.qml",
    } <= names  # fmt: skip


@pytest.mark.parametrize("path", QML_FILES, ids=lambda p: p.relative_to(QML_DIR).as_posix())
def test_cada_archivo_qml_compila_sin_errores(qapp, path: Path):
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
    assert not component.isError(), [error.toString() for error in component.errors()]


def test_las_fuentes_incluidas_se_registran(qapp):
    assert sorted(path.name for path in FONTS_DIR.glob("*.ttf")) == [
        "Inter-Medium.ttf", "Inter-Regular.ttf", "JetBrainsMono-Regular.ttf",
        "Rajdhani-SemiBold.ttf",
    ]  # fmt: skip
    assert {"Inter", "JetBrains Mono", "Rajdhani"} <= set(load_fonts())


@pytest.mark.parametrize("quality", ["high", "medium", "low"])
@pytest.mark.parametrize("reduce_motion", [False, True])
def test_la_vista_previa_completa_recorre_todo_sin_avisos_de_qml(
    make_ui, qtbot, quality, reduce_motion
):
    ui, _ = make_ui(settings=UiSettings(quality=quality, reduce_motion=reduce_motion), debug=True)
    ui.start()
    seen = set()
    driver = PreviewDriver(lambda e: (ui.on_event(e), seen.add(ui.assistant.activity)),
                           speed=40, loop=False)
    driver.start()
    # Una parte con el HUD a la vista, como si el usuario hubiera pasado a otra ventana.
    qtbot.wait(150)
    ui._execute(ui.controller.screen_active_changed(False))
    qtbot.waitUntil(lambda: driver.finished_rounds == 1, timeout=10_000)
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
