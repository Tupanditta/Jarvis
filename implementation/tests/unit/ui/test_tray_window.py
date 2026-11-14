"""Bandeja, ventana mínima de estado y puente del bus a Qt (proceso.md)."""
from pathlib import Path

from jarvis_assistant.core import events
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Activity
from jarvis_assistant.process.tray import (
    ICON_COLORS,
    MIC_UNAVAILABLE,
    TrayController,
    icon_key,
    tooltip,
)
from jarvis_assistant.ui.bridge import UiBridge
from jarvis_assistant.ui.status_window import StatusWindow


def activity(value: Activity, state: str = "LISTENING_COMMAND"):
    return events.AssistantActivityChanged(state, value)


def make_tray():
    log = {"published": [], "opened": [], "quit": []}
    tray = TrayController(
        publish=log["published"].append,
        request_quit=lambda: log["quit"].append(True),
        config_dir=Path("C:/cfg"),
        log_dir=Path("C:/logs"),
        open_folder=log["opened"].append,
    )
    return tray, log


def test_icono_y_texto_emergente():
    assert {a.value for a in Activity} | {MIC_UNAVAILABLE} == set(ICON_COLORS)
    assert icon_key(Activity.ESCUCHANDO, True) == "escuchando"
    assert icon_key(Activity.ESCUCHANDO, False) == MIC_UNAVAILABLE
    assert tooltip(Activity.DORMIDO, True, None) == "Jarvis: dormido"
    assert tooltip(Activity.REPOSO, True, "2026-11-14") == "Jarvis: en reposo\n2026-11-14"
    assert tooltip(Activity.DORMIDO, False, None) == "Jarvis: micrófono no disponible"


def test_el_menu_cambia_con_la_sesion(qapp):
    tray, _ = make_tray()
    assert tray.open_action.isVisible() and not tray.show_action.isVisible()
    tray.on_event(events.SessionOpened(3, "2026-11-14"))
    tray.on_event(activity(Activity.ESCUCHANDO))
    assert not tray.open_action.isVisible() and tray.show_action.isVisible()
    assert tray.icon.toolTip() == "Jarvis: escuchando\n2026-11-14"
    tray.on_event(events.SessionChanged(3, "prácticas", False))
    assert tray.icon.toolTip() == "Jarvis: escuchando\nprácticas"
    tray.on_event(events.MicStatusChanged(False))
    assert "micrófono no disponible" in tray.icon.toolTip()
    tray.on_event(events.MicStatusChanged(True))
    tray.on_event(events.SessionClosed())
    tray.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert tray.open_action.isVisible() and not tray.show_action.isVisible()
    assert tray.icon.toolTip() == "Jarvis: dormido"


def test_las_opciones_del_menu_publican_sus_acciones(qapp):
    tray, log = make_tray()
    tray.open_action.trigger()
    tray.show_action.trigger()
    tray.config_action.trigger()
    tray.log_action.trigger()
    tray.quit_action.trigger()
    assert log["published"] == [events.OpenSessionRequested(), events.ShowScreenRequested(True)]
    assert log["opened"] == [Path("C:/cfg"), Path("C:/logs")]
    assert log["quit"] == [True]
    assert [a.text() for a in tray.menu.actions() if not a.isSeparator()] == [
        "Abrir sesión", "Mostrar pantalla", "Abrir configuración", "Abrir registro", "Salir",
    ]


def test_la_ventana_solo_se_ve_con_sesion_y_muestra_el_estado_en_texto(qtbot):
    window = StatusWindow()
    qtbot.addWidget(window)
    assert not window.isVisible()
    window.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert not window.isVisible()  # nada visible en modo dormido
    window.on_event(events.SessionOpened(7, "2026-11-14"))
    assert window.isVisible()
    assert window.session_label.text() == "Sesión 7: 2026-11-14"
    window.on_event(events.SpeechStarted("Sesión iniciada. Le escucho.", False))
    assert window.text_label.text() == "Sesión iniciada. Le escucho."
    window.on_event(activity(Activity.ESCUCHANDO))
    assert window.state_label.text() == "Escuchando"
    window.on_event(events.TranscriptReady("qué tiempo hace", False))
    assert window.text_label.text() == "«qué tiempo hace» (no reconocido)"
    window.on_event(activity(Activity.REPOSO, "IDLE"))
    assert window.isVisible() and window.state_label.text() == "En reposo"
    window.hide()
    window.on_event(events.ShowScreenRequested(True))
    assert window.isVisible()
    window.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert not window.isVisible()


def test_el_puente_convierte_los_eventos_del_bus_en_senales(qtbot):
    bus = EventBus()
    bridge = UiBridge()
    received = []
    bridge.eventReceived.connect(received.append)
    bridge.attach(bus)
    bus.publish(events.RestEntered())
    bus.publish(events.AudioLevel(0.5, "mic"))  # el nivel no lo usa la ventana mínima
    bus.publish(events.MicStatusChanged(False))
    assert received == [events.RestEntered(), events.MicStatusChanged(False)]
