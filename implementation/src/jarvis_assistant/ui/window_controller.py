"""Qué superficie se muestra y cuándo (hud.md, sección 2).

Lógica pura, sin Qt: recibe los eventos del ciclo de vida, si la pantalla de sesión es la
ventana activa y las peticiones de mostrar u ocultar, y devuelve las acciones que la capa de
ventanas ejecuta en orden.
"""
from dataclasses import dataclass
from enum import StrEnum

from jarvis_assistant.core import events


class Animation(StrEnum):
    WAKE = "wake"  # al abrir la sesión: del vacío al orbe formado
    WAKE_FROM_REST = "wake_from_rest"
    SLEEP_REST = "sleep_rest"
    SLEEP_CLOSE = "sleep_close"


@dataclass(frozen=True)
class Action:
    """Base de las acciones sobre las ventanas."""


@dataclass(frozen=True)
class BringScreenToFront(Action):
    """La pantalla de sesión pasa al frente y pide el foco para la caja de texto."""


@dataclass(frozen=True)
class MinimizeScreen(Action):
    pass


@dataclass(frozen=True)
class HideScreen(Action):
    pass


@dataclass(frozen=True)
class ShowHud(Action):
    """Mostrar el HUD sin activarlo (RNF-13)."""


@dataclass(frozen=True)
class HideHud(Action):
    pass


@dataclass(frozen=True)
class AnimateScreen(Action):
    animation: Animation


@dataclass(frozen=True)
class AnimateHud(Action):
    animation: Animation


@dataclass(frozen=True)
class CollapseHudAfterAnimation(Action):
    """Contraer el HUD cuando termine la animación de dormirse."""


@dataclass(frozen=True)
class HideHudAfterAnimation(Action):
    """Avisar con `close_animation_finished` cuando termine la animación de cierre."""


class WindowController:
    def __init__(self) -> None:
        self._session_open = False
        self._screen_active = False
        self._hud_visible = False
        self._closing = False  # animación de cierre en curso con el HUD a la vista
        self._hud_dismissed = False  # el usuario ha ocultado el HUD con su botón

    @property
    def hud_visible(self) -> bool:
        return self._hud_visible

    def start(self) -> list[Action]:
        """Arranque: la pantalla se muestra en su aspecto de dormido, con el foco."""
        self._screen_active = True
        return [BringScreenToFront()]

    def on_event(self, event: object) -> list[Action]:
        if isinstance(event, events.SessionOpened):
            self._session_open = True
            self._closing = False
            self._hud_dismissed = False
            self._screen_active = True
            return [BringScreenToFront(), AnimateScreen(Animation.WAKE), *self._sync_hud()]
        if isinstance(event, events.ListeningResumed):
            if self._screen_active:
                return [AnimateScreen(Animation.WAKE_FROM_REST)]
            return [AnimateHud(Animation.WAKE_FROM_REST)]
        if isinstance(event, events.RestEntered):
            return [
                AnimateScreen(Animation.SLEEP_REST),
                AnimateHud(Animation.SLEEP_REST),
                CollapseHudAfterAnimation(),
            ]
        if isinstance(event, events.SessionClosed):
            self._session_open = False
            actions: list[Action] = [AnimateScreen(Animation.SLEEP_CLOSE)]
            if self._hud_visible:
                self._closing = True
                actions += [AnimateHud(Animation.SLEEP_CLOSE), HideHudAfterAnimation()]
            return actions
        if isinstance(event, events.ShowScreenRequested):
            if event.visible:
                return self.show_screen()
            self._screen_active = False
            return [MinimizeScreen(), *self._sync_hud()]
        if isinstance(event, events.ShowHudRequested):
            self._hud_dismissed = False
            return self._sync_hud()
        return []

    def screen_active_changed(self, active: bool) -> list[Action]:
        """La pantalla de sesión ha pasado a ser, o ha dejado de ser, la ventana activa."""
        self._screen_active = active
        if active:
            self._hud_dismissed = False  # al volver a salir de la pantalla, el HUD reaparece
        return self._sync_hud()

    def show_screen(self) -> list[Action]:
        """La pantalla de sesión pasa al frente («muestra la pantalla», «Mostrar pantalla» en
        la bandeja o el botón del HUD); el HUD se oculta."""
        self._screen_active = True
        self._hud_dismissed = False
        return [BringScreenToFront(), *self._sync_hud()]

    def hud_dismissed(self) -> list[Action]:
        """El usuario oculta el HUD con su botón. Vuelve a mostrarse al abrir otra sesión, al
        pasar por la pantalla de sesión o con «Mostrar HUD» en la bandeja."""
        self._hud_dismissed = True
        return self._sync_hud()

    def screen_closed(self) -> list[Action]:
        """El usuario cierra la ventana: se oculta y el proceso sigue en la bandeja."""
        self._screen_active = False
        return [HideScreen(), *self._sync_hud()]

    def close_animation_finished(self) -> list[Action]:
        if not self._closing:
            return []
        self._closing = False
        return self._sync_hud()

    def _sync_hud(self) -> list[Action]:
        """El HUD se ve con la sesión abierta, la pantalla sin ser la ventana activa y sin que
        el usuario lo haya ocultado. Durante la animación de cierre sigue a la vista hasta que
        termina."""
        if self._closing:
            return []
        wanted = self._session_open and not self._screen_active and not self._hud_dismissed
        if wanted == self._hud_visible:
            return []
        self._hud_visible = wanted
        return [ShowHud() if wanted else HideHud()]
