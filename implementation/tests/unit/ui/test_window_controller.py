"""Qué superficie se muestra y cuándo: una prueba por fila de la tabla de hud.md, sección 2."""
from jarvis_assistant.core import events
from jarvis_assistant.ui.window_controller import (
    AnimateHud,
    AnimateScreen,
    Animation,
    BringScreenToFront,
    CollapseHudAfterAnimation,
    HideHud,
    HideHudAfterAnimation,
    HideScreen,
    MinimizeScreen,
    ShowHud,
    WindowController,
)


def opened(*, screen_active=True):
    """Controlador con la sesión abierta y la pantalla activa o no."""
    controller = WindowController()
    controller.start()
    controller.on_event(events.SessionOpened(1, "2026-11-14"))
    if not screen_active:
        controller.screen_active_changed(False)
    return controller


def test_arranque_y_dormido_pantalla_visible_con_el_foco_y_hud_oculto():
    controller = WindowController()
    assert controller.start() == [BringScreenToFront()]
    assert not controller.hud_visible
    # En dormido el HUD no se muestra aunque la pantalla deje de ser la ventana activa.
    assert controller.screen_active_changed(False) == []
    assert controller.screen_closed() == [HideScreen()]
    assert not controller.hud_visible


def test_session_opened_pantalla_al_frente_con_despertar_y_hud_oculto():
    controller = WindowController()
    controller.start()
    controller.screen_active_changed(False)
    actions = controller.on_event(events.SessionOpened(1, "2026-11-14"))
    assert actions == [BringScreenToFront(), AnimateScreen(Animation.WAKE)]
    assert not controller.hud_visible


def test_sesion_abierta_y_pantalla_activa_hud_oculto():
    controller = opened()
    assert controller.screen_active_changed(True) == []
    assert not controller.hud_visible


def test_sesion_abierta_y_pantalla_no_activa_hud_visible_y_pantalla_sin_cambios():
    controller = opened()
    assert controller.screen_active_changed(False) == [ShowHud()]
    assert controller.hud_visible
    assert controller.screen_active_changed(False) == []  # sin repetir la orden
    assert controller.screen_active_changed(True) == [HideHud()]


def test_listening_resumed_con_la_pantalla_activa_anima_la_pantalla():
    controller = opened()
    assert controller.on_event(events.ListeningResumed()) == [
        AnimateScreen(Animation.WAKE_FROM_REST)
    ]
    assert not controller.hud_visible


def test_listening_resumed_con_la_pantalla_no_activa_anima_el_mini_orbe():
    controller = opened(screen_active=False)
    assert controller.on_event(events.ListeningResumed()) == [
        AnimateHud(Animation.WAKE_FROM_REST)
    ]
    assert controller.hud_visible


def test_rest_entered_anima_las_dos_superficies_y_el_hud_se_contrae_despues():
    controller = opened(screen_active=False)
    assert controller.on_event(events.RestEntered()) == [
        AnimateScreen(Animation.SLEEP_REST),
        AnimateHud(Animation.SLEEP_REST),
        CollapseHudAfterAnimation(),
    ]
    assert controller.hud_visible  # la interfaz sigue visible


def test_muestra_la_pantalla_la_trae_al_frente_y_oculta_el_hud():
    controller = opened(screen_active=False)
    assert controller.on_event(events.ShowScreenRequested(True)) == [
        BringScreenToFront(),
        HideHud(),
    ]
    assert not controller.hud_visible
    asleep = WindowController()
    asleep.start()
    assert asleep.on_event(events.ShowScreenRequested(True)) == [BringScreenToFront()]


def test_oculta_la_pantalla_la_minimiza_y_muestra_el_hud():
    controller = opened()
    assert controller.on_event(events.ShowScreenRequested(False)) == [MinimizeScreen(), ShowHud()]
    assert controller.hud_visible


def test_cerrar_la_ventana_la_oculta_y_el_hud_se_ve_si_hay_sesion():
    controller = opened()
    assert controller.screen_closed() == [HideScreen(), ShowHud()]
    assert controller.hud_visible


def test_session_closed_anima_y_al_terminar_oculta_el_hud():
    controller = opened(screen_active=False)
    assert controller.on_event(events.SessionClosed()) == [
        AnimateScreen(Animation.SLEEP_CLOSE),
        AnimateHud(Animation.SLEEP_CLOSE),
        HideHudAfterAnimation(),
    ]
    assert controller.hud_visible  # sigue a la vista mientras dura la animación
    assert controller.close_animation_finished() == [HideHud()]
    assert not controller.hud_visible
    assert controller.screen_active_changed(False) == []  # dormido: el HUD no vuelve


def test_session_closed_con_la_pantalla_activa_solo_anima_la_pantalla():
    controller = opened()
    assert controller.on_event(events.SessionClosed()) == [AnimateScreen(Animation.SLEEP_CLOSE)]
    assert controller.close_animation_finished() == []


def test_session_opened_durante_la_animacion_de_cierre_la_funde_con_el_despertar():
    controller = opened(screen_active=False)
    controller.on_event(events.SessionClosed())
    assert controller.on_event(events.SessionOpened(2, "2026-11-14")) == [
        BringScreenToFront(),
        AnimateScreen(Animation.WAKE),
        HideHud(),
    ]
    # El fin de la animación de cierre ya no oculta nada: hay una sesión nueva.
    assert controller.close_animation_finished() == []
    assert controller.screen_active_changed(False) == [ShowHud()]


def test_los_demas_eventos_no_mueven_las_ventanas():
    controller = opened()
    assert controller.on_event(events.CommandReceived("hola", False)) == []
