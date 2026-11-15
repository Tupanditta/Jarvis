"""Bandeja (proceso.md, Interfaz sección 9) y puente del bus a Qt (hud.md, sección 5)."""
from datetime import datetime
from pathlib import Path

from jarvis_assistant.core import events
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Activity
from jarvis_assistant.process.tray import (
    ICON_SIZES,
    ICON_VARIANT_OF,
    ICON_VARIANTS,
    TrayController,
    make_icon,
    tooltip,
)
from jarvis_assistant.ui.bridge import UiBridge


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
    assert set(ICON_VARIANT_OF) == set(Activity)
    assert tooltip(Activity.DORMIDO, None) == "Jarvis: dormido"
    assert tooltip(Activity.REPOSO, "2026-11-14") == "Jarvis: en reposo\n2026-11-14"


def test_cuatro_variantes_del_icono_segun_la_actividad(qapp):
    assert set(ICON_VARIANTS) == {"dormido", "reposo", "activo", "esperando"}
    assert {ICON_VARIANT_OF[a] for a in (Activity.ESCUCHANDO, Activity.PROCESANDO,
                                         Activity.HABLANDO)} == {"activo"}
    tray, _ = make_tray()
    assert tray.variant == "dormido"
    for value, variant in [
        (Activity.REPOSO, "reposo"), (Activity.HABLANDO, "activo"),
        (Activity.ESPERANDO, "esperando"), (Activity.DORMIDO, "dormido"),
    ]:  # fmt: skip
        tray.on_event(activity(value))
        assert tray.variant == variant


def test_el_icono_tiene_tamanos_de_16_a_48(qapp):
    sizes = {(size.width(), size.height()) for size in make_icon("#22D3EE").availableSizes()}
    assert sizes == {(size, size) for size in ICON_SIZES}
    assert min(ICON_SIZES) == 16 and max(ICON_SIZES) == 48


def test_el_menu_cambia_con_la_sesion(qapp):
    tray, _ = make_tray()
    assert tray.open_action.isVisible() and tray.show_action.isVisible()
    assert not tray.hud_action.isVisible()
    tray.on_event(events.SessionOpened(3, "2026-11-14"))
    tray.on_event(activity(Activity.ESCUCHANDO))
    assert not tray.open_action.isVisible() and tray.show_action.isVisible()
    assert tray.hud_action.isVisible()
    assert tray.icon.toolTip() == "Jarvis: escuchando\n2026-11-14"
    tray.on_event(events.SessionChanged(3, "prácticas", False))
    assert tray.icon.toolTip() == "Jarvis: escuchando\nprácticas"
    tray.on_event(events.SessionClosed())
    tray.on_event(activity(Activity.DORMIDO, "DORMIDO"))
    assert tray.open_action.isVisible() and tray.show_action.isVisible()
    assert not tray.hud_action.isVisible()
    assert tray.icon.toolTip() == "Jarvis: dormido"


def test_las_opciones_del_menu_publican_sus_acciones(qapp):
    tray, log = make_tray()
    tray.open_action.trigger()
    tray.show_action.trigger()
    tray.hud_action.trigger()
    tray.config_action.trigger()
    tray.log_action.trigger()
    tray.quit_action.trigger()
    assert log["published"] == [
        events.OpenSessionRequested(), events.ShowScreenRequested(True), events.ShowHudRequested(),
    ]
    assert log["opened"] == [Path("C:/cfg"), Path("C:/logs")]
    assert log["quit"] == [True]
    assert [a.text() for a in tray.menu.actions() if not a.isSeparator()] == [
        "Abrir sesión", "Mostrar pantalla", "Mostrar HUD", "Abrir configuración", "Abrir registro",
        "Salir",
    ]


def test_el_puente_convierte_los_eventos_del_bus_en_senales(qtbot):
    bus = EventBus()
    bridge = UiBridge()
    received = []
    bridge.eventReceived.connect(received.append)
    bridge.attach(bus)
    task = events.TaskUpdated(1, None, "comandos", "ls", "pendiente", None, datetime(2026, 11, 14))
    bus.publish(events.RestEntered())
    bus.publish(events.TextSubmitted("hola"))  # las acciones del usuario no vuelven a la interfaz
    bus.publish(events.CommandReceived("hola", False))
    bus.publish(task)
    bus.publish(events.PanelActivated("comandos"))
    assert received == [
        events.RestEntered(), events.CommandReceived("hola", False), task,
        events.PanelActivated("comandos"),
    ]  # fmt: skip


def test_el_puente_solo_conserva_el_ultimo_nivel_pendiente(qtbot):
    bus = EventBus()
    bridge = UiBridge()
    ready = []
    received = []
    bridge.levelReady.connect(lambda: ready.append(True))
    bridge.eventReceived.connect(received.append)
    bridge.attach(bus)
    for level in (0.2, 0.5, 0.8):
        bus.publish(events.AudioLevel(level, "assistant"))
    assert ready == [True]  # una sola señal hasta que se recoge
    assert received == []  # el nivel no va por la señal de eventos
    assert bridge.take_level() == events.AudioLevel(0.8, "assistant")
    assert bridge.take_level() is None
    bus.publish(events.AudioLevel(0.0, "none"))
    assert ready == [True, True]
