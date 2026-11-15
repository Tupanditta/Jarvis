"""Bandeja, ventana mínima con la caja de texto y puente del bus a Qt (proceso.md)."""
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton

from jarvis_assistant.core import events
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Activity
from jarvis_assistant.process.tray import ICON_COLORS, TrayController, tooltip
from jarvis_assistant.ui.bridge import UiBridge
from jarvis_assistant.ui.status_window import (
    PLACEHOLDER_ASLEEP,
    PLACEHOLDER_ATTENDING,
    PLACEHOLDER_RESTING,
    StatusWindow,
)


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
    assert {a.value for a in Activity} == set(ICON_COLORS)
    assert tooltip(Activity.DORMIDO, None) == "Jarvis: dormido"
    assert tooltip(Activity.REPOSO, "2026-11-14") == "Jarvis: en reposo\n2026-11-14"


def test_el_menu_cambia_con_la_sesion(qapp):
    tray, _ = make_tray()
    assert tray.open_action.isVisible() and tray.show_action.isVisible()
    tray.on_event(events.SessionOpened(3, "2026-11-14"))
    tray.on_event(activity(Activity.ESCUCHANDO))
    assert not tray.open_action.isVisible() and tray.show_action.isVisible()
    assert tray.icon.toolTip() == "Jarvis: escuchando\n2026-11-14"
    tray.on_event(events.SessionChanged(3, "prácticas", False))
    assert tray.icon.toolTip() == "Jarvis: escuchando\nprácticas"
    tray.on_event(events.SessionClosed())
    tray.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert tray.open_action.isVisible() and tray.show_action.isVisible()
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


def make_window(qtbot, now=None):
    published = []
    kwargs = {} if now is None else {"monotonic": lambda: now[0]}
    window = StatusWindow(publish=published.append, **kwargs)
    qtbot.addWidget(window)
    return window, published


def test_la_ventana_se_ve_tambien_en_dormido_y_muestra_el_estado_en_texto(qtbot):
    window, _ = make_window(qtbot)
    window.show_and_focus()
    assert window.isVisible()
    assert window.state_label.text() == "Dormido"
    window.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert window.isVisible()
    # La frase empieza a sonar justo antes de anunciarse la sesión: su texto no se borra.
    window.on_event(events.SpeechStarted("Sesión iniciada. Le escucho.", False))
    window.on_event(events.SessionOpened(7, "2026-11-14"))
    assert window.session_label.text() == "Sesión 7: 2026-11-14"
    assert window.text_label.text() == "Sesión iniciada. Le escucho."
    window.on_event(activity(Activity.ESCUCHANDO))
    assert window.state_label.text() == "Escuchando"
    window.on_event(events.CommandReceived("qué tiempo hace", False))
    assert window.text_label.text() == "«qué tiempo hace» (no reconocido)"
    window.on_event(events.CommandReceived("gracias jarvis", True))
    assert window.text_label.text() == "«gracias jarvis»"
    window.on_event(activity(Activity.REPOSO, "IDLE"))
    assert window.isVisible() and window.state_label.text() == "En reposo"
    window.on_event(events.SessionClosed())
    window.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert window.isVisible()  # cerrar la sesión no oculta la ventana
    assert window.session_label.text() == ""


def test_el_texto_de_ayuda_de_la_caja_depende_del_estado(qtbot):
    window, _ = make_window(qtbot)
    assert window.input.placeholderText() == PLACEHOLDER_ASLEEP
    window.on_event(activity(Activity.HABLANDO, "LISTENING_COMMAND"))
    assert window.input.placeholderText() == PLACEHOLDER_ATTENDING
    window.on_event(activity(Activity.ESPERANDO, "AWAITING_CONFIRMATION"))
    assert window.input.placeholderText() == PLACEHOLDER_ATTENDING
    window.on_event(activity(Activity.REPOSO, "IDLE"))
    assert window.input.placeholderText() == PLACEHOLDER_RESTING
    window.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert window.input.placeholderText() == PLACEHOLDER_ASLEEP


def test_enter_envia_el_texto_y_vacia_la_caja(qtbot):
    window, published = make_window(qtbot)
    window.show_and_focus()
    qtbot.keyClicks(window.input, "Hey Jarvis")
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert events.TextSubmitted("Hey Jarvis") in published
    assert window.input.text() == ""


@pytest.mark.parametrize("text", ["", "   "])
def test_un_envio_vacio_no_publica_nada(qtbot, text):
    window, published = make_window(qtbot)
    window.input.setText(text)
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert published == []
    assert window.input.text() == ""


def test_teclear_avisa_como_mucho_una_vez_por_segundo(qtbot):
    now = [100.0]
    window, published = make_window(qtbot, now)
    qtbot.keyClicks(window.input, "abre")
    assert published == [events.UserTyping()]
    now[0] += 0.9
    qtbot.keyClicks(window.input, " el")
    assert published == [events.UserTyping()]
    now[0] += 0.2
    qtbot.keyClicks(window.input, " navegador")
    assert published == [events.UserTyping(), events.UserTyping()]
    qtbot.keyClick(window.input, Qt.Key.Key_Return)  # tras enviar, la siguiente tecla avisa
    qtbot.keyClicks(window.input, "x")
    assert published[-2:] == [events.TextSubmitted("abre el navegador"), events.UserTyping()]


def test_cambiar_el_texto_por_codigo_no_cuenta_como_teclear(qtbot):
    window, published = make_window(qtbot)
    window.input.setText("hola")
    assert published == []


def test_cerrar_la_ventana_la_oculta_y_mostrar_pantalla_la_devuelve(qtbot):
    window, _ = make_window(qtbot)
    window.show_and_focus()
    assert not window.close()  # el cierre se rechaza: el proceso sigue en la bandeja
    assert not window.isVisible()
    window.on_event(events.ShowScreenRequested(True))
    assert window.isVisible()
    window.hide()
    window.on_event(events.SessionOpened(8, "2026-11-14"))  # «Abrir sesión» en la bandeja
    assert window.isVisible()


def test_la_ventana_no_tiene_botones(qtbot):
    window, _ = make_window(qtbot)
    assert window.findChildren(QAbstractButton) == []


def test_el_puente_convierte_los_eventos_del_bus_en_senales(qtbot):
    bus = EventBus()
    bridge = UiBridge()
    received = []
    bridge.eventReceived.connect(received.append)
    bridge.attach(bus)
    bus.publish(events.RestEntered())
    bus.publish(events.AudioLevel(0.5, "assistant"))  # el nivel no lo usa la ventana mínima
    bus.publish(events.TextSubmitted("hola"))  # ni las acciones del usuario
    bus.publish(events.CommandReceived("hola", False))
    assert received == [events.RestEntered(), events.CommandReceived("hola", False)]
