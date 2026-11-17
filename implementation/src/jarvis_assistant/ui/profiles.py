"""Selector de perfiles de la pantalla dormida.

Los perfiles llegan con `ConfigApplied`. El elegido se publica con `ProfileSelected`: la
próxima sesión se abre con él. El perfil con el que se abrió la última sesión se recuerda
entre ejecuciones (`ProfileMemory`); no es configuración, es estado de la aplicación.

Los perfiles protegidos con contraseña llegan con `ProtectedProfilesChanged` y se muestran con
un candado (`locked`).
"""
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

from jarvis_assistant.config import Profile, admin_profile
from jarvis_assistant.core import events

logger = logging.getLogger(__name__)

_Index = QModelIndex | QPersistentModelIndex


class ProfileMemory:
    """El último perfil usado, en un archivo JSON. Un archivo ilegible se ignora."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def load(self) -> str | None:
        if self._path is None:
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            logger.warning("No se ha podido leer el último perfil usado: %s", self._path)
            return None
        value = data.get("profile") if isinstance(data, dict) else None
        return value if isinstance(value, str) else None

    def save(self, profile_id: str) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"profile": profile_id}), encoding="utf-8")
        except OSError:
            logger.warning("No se ha podido guardar el último perfil usado: %s", self._path)


class ProfilesModel(QAbstractListModel):
    """Los perfiles y el elegido. Sin reglas de negocio: solo elige y avisa."""

    changed = Signal()

    ROLES = ("profileId", "name", "selected", "locked")
    _FIRST_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        publish: Callable[[events.Event], None],
        memory: ProfileMemory | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._publish = publish
        self._memory = memory or ProfileMemory(None)
        self._profiles: tuple[Profile, ...] = ()
        self._current = -1
        self._published: str | None = None
        self._protected: frozenset[str] = frozenset()
        self._configured: tuple[Profile, ...] = ()
        self._admin_active = False

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self._FIRST_ROLE + i: QByteArray(name.encode()) for i, name in enumerate(self.ROLES)
        }

    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._profiles)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._profiles):
            return None
        profile = self._profiles[index.row()]
        name = self.ROLES[role - self._FIRST_ROLE] if role >= self._FIRST_ROLE else ""
        match name:
            case "profileId":
                return profile.id
            case "name":
                return profile.name
            case "selected":
                return index.row() == self._current
            case "locked":
                return profile.id in self._protected
        return None

    # --- Eventos del núcleo ------------------------------------------------------------------

    def apply(self, event: object) -> None:
        if isinstance(event, events.ConfigApplied):
            self._configured = event.config.all_profiles()
            self._set_profiles(self._offered())
        elif isinstance(event, events.SessionOpened) and event.profile_id:
            self._memory.save(event.profile_id)
        elif isinstance(event, events.ProtectedProfilesChanged):
            admin_changed = event.admin_active != self._admin_active
            self._admin_active = event.admin_active
            if admin_changed:
                self._set_profiles(self._offered())
            if event.profile_ids != self._protected:
                self._protected = event.profile_ids
                if self._profiles:
                    self.dataChanged.emit(self.index(0), self.index(len(self._profiles) - 1))
                self.changed.emit()

    def _offered(self) -> tuple[Profile, ...]:
        """Los de la configuración y, si está activado, el Acedor al final."""
        return (*self._configured, admin_profile()) if self._admin_active else self._configured

    def _set_profiles(self, profiles: tuple[Profile, ...]) -> None:
        wanted = self.currentId or self._memory.load()
        self.beginResetModel()
        self._profiles = profiles
        ids = [profile.id for profile in profiles]
        self._current = ids.index(wanted) if wanted in ids else (0 if ids else -1)
        self.endResetModel()
        self.changed.emit()
        self._announce()

    def _announce(self) -> None:
        current = self.currentId
        if current and current != self._published:
            self._published = current
            self._publish(events.ProfileSelected(current))

    # --- Acciones del usuario ----------------------------------------------------------------

    @Slot(int)
    def select(self, row: int) -> None:
        if not 0 <= row < len(self._profiles) or row == self._current:
            return
        self._current = row
        self.dataChanged.emit(self.index(0), self.index(len(self._profiles) - 1))
        self.changed.emit()
        self._announce()

    @Slot(int)
    def step(self, delta: int) -> None:
        """Pasa al perfil siguiente (1) o al anterior (-1), dando la vuelta."""
        if self._profiles:
            self.select((self._current + delta) % len(self._profiles))

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._profiles)

    @Property(int, notify=changed)
    def currentIndex(self) -> int:
        return self._current

    @Property(bool, notify=changed)
    def currentLocked(self) -> bool:
        """El perfil elegido pide contraseña."""
        return self.currentId in self._protected

    @Property(str, notify=changed)
    def currentId(self) -> str:
        return self._profiles[self._current].id if self._current >= 0 else ""
