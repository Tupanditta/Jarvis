"""Creación de las ventanas QML y ejecución de lo que decide `window_controller` (hud.md).

Las dos ventanas se crean al arrancar: la pantalla de sesión se muestra y el HUD queda oculto.
Los modelos de vista se registran como propiedades de contexto de QML.
"""
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QMetaObject, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlError
from PySide6.QtQuick import QQuickWindow

from jarvis_assistant.config import UiSettings
from jarvis_assistant.core import events
from jarvis_assistant.ui import window_controller as wc
from jarvis_assistant.ui.meter import keep_apart
from jarvis_assistant.ui.noise import NoiseModel
from jarvis_assistant.ui.panel_models import (
    DEFAULT_OUTPUT_LINES,
    AdminModel,
    CommandsModel,
    HelpModel,
    HistoryModel,
    OpenedModel,
    ProtocolModel,
    RemindersModel,
    SearchModel,
)
from jarvis_assistant.ui.profiles import ProfileMemory, ProfilesModel
from jarvis_assistant.ui.resources import ResourcesModel
from jarvis_assistant.ui.view_models import (
    AccessModel,
    AssistantModel,
    DialogueModel,
    HudModel,
    TaskListModel,
    UiOptions,
)
from jarvis_assistant.ui.workspace import WorkspaceModel

logger = logging.getLogger(__name__)

UI_DIR = Path(__file__).resolve().parent
QML_DIR = UI_DIR / "qml"
FONTS_DIR = UI_DIR / "assets" / "fonts"
TRANSITION_MS = 2000  # motion.transition

Publish = Callable[[events.Event], None]


def load_fonts() -> list[str]:
    """Registra las fuentes incluidas y devuelve sus familias."""
    families: list[str] = []
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            logger.warning("No se ha podido cargar la fuente %s", path.name)
            continue
        families += QFontDatabase.applicationFontFamilies(font_id)
    return families


class UiApp(QObject):
    """Interfaz completa: modelos, ventanas y controlador de ventanas."""

    screenAnimation = Signal(str)
    hudAnimation = Signal(str)
    configuringChanged = Signal()

    def __init__(
        self,
        *,
        publish: Publish,
        settings: UiSettings,
        platform: Any = None,
        debug: bool = False,
        monotonic: Callable[[], float] = time.monotonic,
        output_lines: int = DEFAULT_OUTPUT_LINES,
        profile_path: Path | None = None,
        open_settings: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        """`profile_path`: archivo donde se recuerda el último perfil usado; sin él, dura lo
        que la ejecución. `open_settings`: abre la ventana de configuración desde la pantalla
        dormida; sin él no hay botón."""
        super().__init__(parent)
        self._open_settings = open_settings
        self._configuring = False
        self._platform = platform
        self._monotonic = monotonic
        self._quitting = False
        self.warnings: list[str] = []
        self.assistant = AssistantModel(publish, monotonic, self)
        self.tasks = TaskListModel(self)
        self.dialogue = DialogueModel(self)
        self.hud = HudModel(
            settings.hud_collapse_seconds,
            is_busy=lambda: self.dialogue.active or self.tasks.pendingCount > 0,
            parent=self,
        )
        self.options = UiOptions(settings, debug, self)
        self.commands = CommandsModel(output_lines, self, publish)
        self.opened = OpenedModel(publish, self)
        self.search = SearchModel(self, publish)
        self.history = HistoryModel(self, publish)
        self.reminders = RemindersModel(self, publish)
        self.protocols = ProtocolModel(self, publish)
        self.help = HelpModel(self, publish)
        self.resources = ResourcesModel(parent=self)
        self.noise = NoiseModel(parent=self)
        keep_apart(self.resources, self.noise)
        self.workspace = WorkspaceModel(
            parent=self, meters={"recursos": self.resources, "ruido": self.noise}
        )
        self.profiles = ProfilesModel(publish, ProfileMemory(profile_path), self)
        self.access = AccessModel(publish, self)
        self.admin = AdminModel(self, publish)
        self._models = (
            self.options, self.assistant, self.access, self.tasks, self.dialogue, self.hud,
            self.workspace, self.profiles, self.commands, self.opened, self.search, self.history,
            self.reminders, self.protocols, self.help, self.admin,
        )  # fmt: skip
        self.controller = wc.WindowController()
        self._collapse_timer = self._single_shot(self.hud.collapse)
        self._close_timer = self._single_shot(
            lambda: self._execute(self.controller.close_animation_finished())
        )

        load_fonts()
        self.engine = QQmlApplicationEngine(self)
        self.engine.warnings.connect(self._on_warnings)
        context = self.engine.rootContext()
        for name, model in (
            ("assistant", self.assistant),
            ("tasks", self.tasks),
            ("dialogue", self.dialogue),
            ("hud", self.hud),
            ("commands", self.commands),
            ("opened", self.opened),
            ("search", self.search),
            ("history", self.history),
            ("reminders", self.reminders),
            ("protocols", self.protocols),
            ("help", self.help),
            ("usage", self.resources),
            ("noise", self.noise),
            ("workspace", self.workspace),
            ("profiles", self.profiles),
            ("access", self.access),
            ("admin", self.admin),
            ("ui", self.options),
            ("windows", self),
        ):
            context.setContextProperty(name, model)
        self.screen = self._load("SessionScreen.qml")
        self.hud_window = self._load("HudOverlay.qml")
        self.screen.activeChanged.connect(self._screen_active_changed)
        self.hud_window.activeChanged.connect(self._hud_active_changed)

    def _single_shot(self, callback: Callable[[], None]) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(TRANSITION_MS)
        timer.timeout.connect(callback)
        return timer

    def _load(self, name: str) -> QQuickWindow:
        before = len(self.engine.rootObjects())
        self.engine.load(QUrl.fromLocalFile(str(QML_DIR / name)))
        roots = self.engine.rootObjects()
        if len(roots) == before:
            raise RuntimeError(f"No se ha podido cargar {name}: {'; '.join(self.warnings)}")
        window = roots[-1]
        assert isinstance(window, QQuickWindow)
        return window

    def _on_warnings(self, warnings: list[QQmlError]) -> None:
        for warning in warnings:
            text = warning.toString()
            self.warnings.append(text)
            logger.warning("QML: %s", text)

    # --- Entradas ----------------------------------------------------------------------------

    def start(self) -> None:
        """Muestra la pantalla de sesión en su aspecto de dormido, con el foco en la caja."""
        self._execute(self.controller.start())

    @Slot(object)
    def on_event(self, event: object) -> None:
        for model in self._models:
            model.apply(event)
        self._execute(self.controller.on_event(event))

    def apply_level(self, event: events.AudioLevel | None) -> None:
        if event is not None:
            self.assistant.apply(event)

    def shutdown(self) -> None:
        """Permite cerrar las ventanas. Debe llamarse antes de salir del bucle de Qt: en Qt 6,
        una ventana que rechaza el cierre anula `quit()`."""
        self._quitting = True
        self._collapse_timer.stop()
        self._close_timer.stop()
        self.noise.close()

    @Slot(result=bool)
    def acceptClose(self) -> bool:
        """El usuario cierra la pantalla (✕): se oculta y el proceso sigue en la bandeja."""
        if self._quitting:
            return True
        self._execute(self.controller.screen_closed())
        return False

    # --- Configuración ------------------------------------------------------------------------

    @Property(bool, constant=True)
    def settingsAvailable(self) -> bool:
        return self._open_settings is not None

    @Property(bool, notify=configuringChanged)
    def configuring(self) -> bool:
        """La ventana de configuración está abierta: no se puede iniciar sesión."""
        return self._configuring

    def set_configuring(self, configuring: bool) -> None:
        if configuring != self._configuring:
            self._configuring = configuring
            self.configuringChanged.emit()

    @Slot()
    def openSettings(self) -> None:
        """Botón «Configuración» de la pantalla dormida."""
        if self._open_settings is not None:
            self._open_settings()

    @Slot(str)
    def copyText(self, text: str) -> None:
        """Copia `text` al portapapeles (rutas y salidas de las ventanas)."""
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    @Slot()
    def hudInputPressed(self) -> None:
        """Clic en la caja de texto del HUD: la única vez que el HUD acepta el foco."""
        self.hud_window.setFlag(Qt.WindowType.WindowDoesNotAcceptFocus, False)
        self._non_activating(self.hud_window, False)
        self.hud_window.requestActivate()

    @Slot()
    def hudOpenScreen(self) -> None:
        """Botón del HUD que abre la pantalla de sesión."""
        self._execute(self.controller.show_screen())

    @Slot()
    def hudDismissed(self) -> None:
        """Botón de ocultar del HUD."""
        self._execute(self.controller.hud_dismissed())

    def _screen_active_changed(self) -> None:
        self._execute(self.controller.screen_active_changed(self.screen.isActive()))

    def _hud_active_changed(self) -> None:
        if not self.hud_window.isActive():
            self.hud_window.setFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
            self._non_activating(self.hud_window, True)

    # --- Acciones ----------------------------------------------------------------------------

    def _execute(self, actions: list[wc.Action]) -> None:
        for action in actions:
            self._run(action)

    def _run(self, action: wc.Action) -> None:
        match action:
            case wc.BringScreenToFront():
                self._bring_screen_to_front()
            case wc.MinimizeScreen():
                self.screen.showMinimized()
            case wc.HideScreen():
                self.screen.hide()
            case wc.ShowHud():
                # El estilo se aplica antes de mostrarlo: así no se activa ni al aparecer.
                self.hud_window.setFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
                self._non_activating(self.hud_window, True)
                self.hud_window.show()
            case wc.HideHud():
                self.hud_window.hide()
            case wc.AnimateScreen(animation=animation):
                self._log_animation("pantalla", animation)
                self.screenAnimation.emit(animation.value)
            case wc.AnimateHud(animation=animation):
                self._log_animation("HUD", animation)
                self.hudAnimation.emit(animation.value)
            case wc.CollapseHudAfterAnimation():
                self._collapse_timer.start()
            case wc.HideHudAfterAnimation():
                self._close_timer.start()

    def _log_animation(self, surface: str, animation: wc.Animation) -> None:
        # Para medir la sincronía con el inicio de la frase (RNF-22).
        logger.debug("Inicio de la animación %s (%s): %.3f", animation.value, surface,
                     self._monotonic())

    def _bring_screen_to_front(self) -> None:
        """La pantalla pasa al frente y pide el foco para la caja; el foco no se fuerza."""
        if self.screen.windowStates() & Qt.WindowState.WindowMinimized:
            # En Windows, pasar de minimizada a pantalla completa sin restaurar antes deja
            # la ventana con un tamaño intermedio y solo se ve parte de la pantalla.
            self.screen.showNormal()
        self.screen.showFullScreen()
        self.screen.raise_()
        if self._platform is not None:
            self._platform.bring_own_window_to_front(int(self.screen.winId()))
        self.screen.requestActivate()
        QMetaObject.invokeMethod(self.screen, "focusInput")

    def _non_activating(self, window: QWindow, enabled: bool) -> None:
        if self._platform is not None:
            self._platform.make_non_activating(int(window.winId()), enabled)
