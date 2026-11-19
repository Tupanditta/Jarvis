"""Editor de plantillas: una pantalla de sesión inerte a pantalla completa.

Se ven las ventanas flotantes que la plantilla muestra y las dos barras. Se mueven y se
redimensionan con el ratón; nada más responde: no hay asistente, la caja no admite texto y el
selector no abre ventanas. La disposición vive en un `WorkspaceModel` propio, el mismo modelo
que usa la pantalla de sesión, así lo que se ve es exactamente lo que quedará.

Los medidores no miden aquí: sus modelos solo guardan si la plantilla los muestra.

Aceptar devuelve la plantilla al apartado Plantillas (`finished`); solo queda registrada al
pulsar Guardar en la ventana de configuración.
"""
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from jarvis_assistant.config import FACTORY_LAYOUT, ScreenLayout
from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity
from jarvis_assistant.ui.meter import keep_apart
from jarvis_assistant.ui.noise import NoiseModel
from jarvis_assistant.ui.resources import ResourcesModel
from jarvis_assistant.ui.view_models import AssistantModel
from jarvis_assistant.ui.workspace import WorkspaceModel

NameCheck = Callable[[str, str], str]  # (id, nombre) → motivo por el que no vale, o ""


class LayoutEditor(QObject):
    finished = Signal(object)  # ScreenLayout aceptada
    activeChanged = Signal()
    nameChanged = Signal()
    errorChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.resources = ResourcesModel(parent=self)
        self.noise = NoiseModel(parent=self)
        keep_apart(self.resources, self.noise)
        self.workspace = WorkspaceModel(
            parent=self, meters={"recursos": self.resources, "ruido": self.noise}
        )
        # Los componentes de la pantalla leen el estado del asistente; aquí está siempre
        # escuchando, con la sesión abierta, y lo que publica no va a ninguna parte.
        self.assistant = AssistantModel(parent=self)
        self.assistant.apply(
            events.AssistantActivityChanged("LISTENING_COMMAND", Activity.ESCUCHANDO)
        )
        self._active = False
        self._id = ""
        self._name = ""
        self._error = ""
        self._check: NameCheck = lambda _id, _name: ""

    def begin(self, layout: ScreenLayout, check: NameCheck) -> None:
        """Abre el editor con `layout`. `check` valida el nombre al aceptar."""
        self._id = layout.id
        self._check = check
        self.workspace.apply_layout(layout)
        self._set_name(layout.name)
        self._set_error("")
        self._set_active(True)

    @Property(bool, notify=activeChanged)
    def active(self) -> bool:
        return self._active

    @Property(str, notify=nameChanged)
    def name(self) -> str:
        return self._name

    @Property(str, notify=errorChanged)
    def error(self) -> str:
        return self._error

    @Slot(str)
    def setName(self, name: str) -> None:
        self._set_name(name)
        self._set_error("")

    @Slot()
    def restoreFactory(self) -> None:
        """Vuelve a la disposición de fábrica; el nombre se conserva."""
        self.workspace.apply_layout(FACTORY_LAYOUT)

    @Slot(result=bool)
    def accept(self) -> bool:
        name = " ".join(self._name.split())
        problem = self._check(self._id, name)
        if problem:
            self._set_error(problem)
            return False
        self._set_active(False)
        self.finished.emit(self.workspace.to_layout(self._id, name))
        return True

    @Slot()
    def cancel(self) -> None:
        self._set_active(False)

    def _set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self.activeChanged.emit()

    def _set_name(self, name: str) -> None:
        if name != self._name:
            self._name = name
            self.nameChanged.emit()

    def _set_error(self, error: str) -> None:
        if error != self._error:
            self._error = error
            self.errorChanged.emit()
