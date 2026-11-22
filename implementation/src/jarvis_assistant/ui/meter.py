"""Estado de un medidor de la pantalla de sesión, común al de recursos y al de ruido.

Un medidor está a la vista u oculto (`shown`, botón del selector) y en una esquina inferior
(`corner`, triple clic). Al abrir sesión la plantilla del perfil dice si está a la vista
(`set_shown`) y los permisos si el perfil puede usarlo (`set_allowed`): sin permiso no se ve ni
se ofrece en el selector.
"""
from PySide6.QtCore import Property, QObject, Signal, Slot


class MeterModel(QObject):
    shownChanged = Signal()
    cornerChanged = Signal()
    allowedChanged = Signal()

    def __init__(self, shown: bool, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._shown = shown
        self._allowed = True
        self._corner = "right"

    @Slot()
    def toggle(self) -> None:
        """Botón del selector: muestra u oculta el medidor."""
        if self._allowed:
            self.set_shown(not self._shown)

    def set_shown(self, shown: bool) -> None:
        if shown != self._shown:
            self._shown = shown
            self.shownChanged.emit()

    def set_allowed(self, allowed: bool) -> None:
        if allowed != self._allowed:
            self._allowed = allowed
            self.allowedChanged.emit()
            self.shownChanged.emit()

    @Slot()
    def switchCorner(self) -> None:
        """Triple clic: a la otra esquina inferior."""
        self._corner = "left" if self._corner == "right" else "right"
        self.cornerChanged.emit()

    @Property(bool, notify=shownChanged)
    def shown(self) -> bool:
        """A la vista: lo ha pedido el usuario o la plantilla, y el perfil puede usarlo."""
        return self._shown and self._allowed

    @property
    def wanted(self) -> bool:
        """A la vista según la plantilla y el selector, tenga o no permiso."""
        return self._shown

    @Property(bool, notify=allowedChanged)
    def allowed(self) -> bool:
        return self._allowed

    @Property(str, notify=cornerChanged)
    def corner(self) -> str:
        """`left` o `right`: la esquina inferior donde está el medidor."""
        return self._corner


def keep_apart(first: MeterModel, second: MeterModel) -> None:
    """Pone dos medidores en esquinas inferiores opuestas y los mantiene así: si uno cambia de
    esquina, el otro pasa a la que deja libre. Juntos no caben en una esquina."""

    def follow(moved: MeterModel, other: MeterModel) -> None:
        if other.corner == moved.corner:
            other.switchCorner()

    first.cornerChanged.connect(lambda: follow(first, second))
    second.cornerChanged.connect(lambda: follow(second, first))
    follow(first, second)
