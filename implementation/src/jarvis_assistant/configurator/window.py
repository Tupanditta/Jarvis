"""La ventana de configuración y su editor de plantillas (configurador.md).

Solo se abre desde la pantalla dormida. Quien monta la aplicación la crea al abrirla y la
destruye al cerrarla (`closed`): mientras hay sesión no queda nada de ella en memoria. Al
guardar llama a `on_saved` (publicar `ConfigSaved` en el bus).

`owner`: la pantalla de sesión. La ventana queda siempre encima de ella aunque esté a
pantalla completa. `vault`: las contraseñas de los perfiles, con su propia conexión a la base
de datos en el hilo de la interfaz.
"""
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QWindow
from PySide6.QtQml import QQmlApplicationEngine, QQmlError
from PySide6.QtQuick import QQuickWindow

from jarvis_assistant.config import UiSettings
from jarvis_assistant.configurator.draft import Draft
from jarvis_assistant.configurator.editor import LayoutEditor
from jarvis_assistant.configurator.registry import SECTIONS, SectionContext, SectionSpec
from jarvis_assistant.configurator.sections.base import Section
from jarvis_assistant.core.security import ProfileVault
from jarvis_assistant.ui.app import load_fonts
from jarvis_assistant.ui.noise import NoiseModel
from jarvis_assistant.ui.resources import ResourcesModel
from jarvis_assistant.ui.view_models import UiOptions

logger = logging.getLogger(__name__)

QML_DIR = Path(__file__).resolve().parent / "qml"


class ConfigWindow(QObject):
    dirtyChanged = Signal()
    problemsChanged = Signal()
    savedChanged = Signal()
    closed = Signal()  # la ventana se ha cerrado: se puede destruir

    def __init__(
        self,
        config_dir: Path,
        on_saved: Callable[[], None] = lambda: None,
        specs: tuple[SectionSpec, ...] = SECTIONS,
        owner: QWindow | None = None,
        parent: QObject | None = None,
        vault: ProfileVault | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_saved = on_saved
        self._owner = owner
        self._specs = specs
        self.editor = LayoutEditor(self)
        self.sections: dict[str, Section] = {}
        for spec in specs:
            section = spec.create(SectionContext(self.editor, self.sections, vault))
            section.setParent(self)
            section.dirtyChanged.connect(self.dirtyChanged)
            self.sections[spec.id] = section
        self.draft = Draft(config_dir, self.sections)
        self._problems: list[str] = []
        self._saved = False
        self.warnings: list[str] = []
        self._engine: QQmlApplicationEngine | None = None
        self.window: QQuickWindow | None = None
        self.editor_window: QQuickWindow | None = None
        self._options = UiOptions(UiSettings(), parent=self)

    # --- Para quien monta la aplicación ------------------------------------------------------

    def show(self) -> None:
        """Muestra la ventana con la configuración guardada; si ya está abierta, la trae al
        frente sin perder los cambios pendientes."""
        if self.window is None:
            self._load()
        assert self.window is not None
        if not self.window.isVisible():
            self.draft.open()
            self._set_problems([])
            self._set_saved(False)
        self.window.show()
        self.window.raise_()
        self.window.requestActivate()

    # --- Para QML ----------------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def sectionList(self) -> list[dict[str, Any]]:
        return [
            {"id": spec.id, "title": spec.title, "icon": spec.icon, "page": spec.page}
            for spec in self._specs
        ]

    @Slot(str, result=QObject)
    def section(self, section_id: str) -> QObject | None:
        return self.sections.get(section_id)

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self.draft.dirty

    @Property("QVariantList", notify=problemsChanged)
    def problems(self) -> list[str]:
        return self._problems

    @Property(bool, notify=savedChanged)
    def saved(self) -> bool:
        """Se acaba de guardar (para el aviso «Guardado»). Se apaga con el siguiente cambio."""
        return self._saved

    @Slot(result=bool)
    def save(self) -> bool:
        result = self.draft.save()
        self._set_problems(result.problems)
        if result.saved:
            self._set_saved(True)
            self._on_saved()
        return result.saved

    @Slot()
    def discard(self) -> None:
        """Salir sin guardar: se descarta el borrador y se cierra."""
        self.draft.open()
        self._set_problems([])
        self.editor.cancel()
        if self.window is not None:
            self.window.hide()

    @Slot(result=bool)
    def canClose(self) -> bool:
        """Cerrar sin preguntar solo si no hay cambios; si los hay, QML pregunta."""
        return not self.draft.dirty

    # --- Interno -----------------------------------------------------------------------------

    def _set_problems(self, problems: list[str]) -> None:
        if problems != self._problems:
            self._problems = problems
            self.problemsChanged.emit()

    def _set_saved(self, saved: bool) -> None:
        if saved != self._saved:
            self._saved = saved
            self.savedChanged.emit()

    def _load(self) -> None:
        load_fonts()
        engine = QQmlApplicationEngine(self)
        engine.warnings.connect(self._on_warnings)
        context = engine.rootContext()
        for name, value in (
            ("settingsWindow", self),
            ("editor", self.editor),
            # Lo que necesitan los componentes de la pantalla de sesión en el editor.
            ("workspace", self.editor.workspace),
            ("assistant", self.editor.assistant),
            # Los botones de los medidores de recursos y de ruido del selector. Aquí no hay
            # medidores: no miden nada.
            ("usage", ResourcesModel(parent=self)),
            ("noise", NoiseModel(parent=self)),
            ("ui", self._options),
        ):
            context.setContextProperty(name, value)
        self.dirtyChanged.connect(lambda: self._set_saved(False) if self.dirty else None)
        for name in ("ConfigWindow.qml", "LayoutEditor.qml"):
            before = len(engine.rootObjects())
            engine.load(QUrl.fromLocalFile(str(QML_DIR / name)))
            if len(engine.rootObjects()) == before:
                raise RuntimeError(f"No se ha podido cargar {name}: {'; '.join(self.warnings)}")
        roots = engine.rootObjects()
        self.window, self.editor_window = roots[-2], roots[-1]  # type: ignore[assignment]
        self._engine = engine
        if self._owner is not None:
            self.window.setTransientParent(self._owner)
        self.editor_window.setTransientParent(self.window)
        self.window.visibleChanged.connect(self._visible_changed)

    def _visible_changed(self, visible: bool) -> None:
        if not visible:
            self.editor.cancel()
            self.closed.emit()

    def _on_warnings(self, warnings: list[QQmlError]) -> None:
        for warning in warnings:
            text = warning.toString()
            self.warnings.append(text)
            logger.warning("QML: %s", text)
