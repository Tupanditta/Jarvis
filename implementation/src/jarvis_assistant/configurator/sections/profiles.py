"""Apartado Perfiles: nombre del perfil, nombre del usuario (el de «preséntate»), plantilla
predeterminada y contraseña. Siempre queda al menos uno.

Un perfil protegido con contraseña está bloqueado: no se edita ni duplica hasta
desbloquearlo con su contraseña (`unlock`), y sigue desbloqueado hasta cerrar la ventana. Los
fallos cuentan igual que en la pantalla dormida: el tercero seguido registra un aviso de
intrusión (`core/security.py`). Poner, cambiar o quitar la contraseña se aplica al guardar;
hasta entonces solo se guarda su hash (y su sello para el Acedor) en memoria, nunca el texto.

Cualquiera añade perfiles, pero ninguno se elimina desde aquí: eso solo lo hace el Acedor, en
su sesión. El Acedor tiene su propia tarjeta: se activa poniéndole contraseña y, después, solo
se le cambia dando la actual.

Sin `profiles.toml`, el apartado empieza con el perfil «Predeterminado» que el asistente crea
con `user.name`; el archivo se escribe la primera vez que se guarda un cambio de perfiles.
"""
import dataclasses
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from jarvis_assistant.config import ADMIN_PROFILE_ID, ADMIN_PROFILE_NAME, Config, Profile
from jarvis_assistant.config.ids import make_id
from jarvis_assistant.config.profiles import dump_profiles
from jarvis_assistant.configurator.sections.base import Section, comparable
from jarvis_assistant.configurator.sections.layouts import LayoutsSection
from jarvis_assistant.core.custody import generate_keys, rewrap_private, seal
from jarvis_assistant.core.security import (
    AccessOrigin,
    AttemptOutcome,
    ProfileVault,
    hash_password,
    password_problem,
)

PASSWORDS_DIFFER = "Las contraseñas no coinciden."


class ProfilesSection(Section):
    itemsChanged = Signal()

    files = ("profiles.toml",)

    def __init__(self, layouts: LayoutsSection, vault: ProfileVault | None = None) -> None:
        super().__init__()
        self._layouts = layouts
        self._vault = vault
        self._profiles: list[Profile] = []
        self._loaded: set[str] = set()  # ids al abrir: un perfil nuevo no los reutiliza
        self._stored: frozenset[str] = frozenset()  # protegidos según la base de datos
        self._pending: dict[str, str | None] = {}  # id → hash nuevo, o None: quitarla
        self._sealed: dict[str, str] = {}  # id → contraseña nueva sellada para el Acedor
        # Acedor activado o con contraseña nueva en este borrador: (hash, pública, privada).
        self._pending_admin: tuple[str, str, str] | None = None
        self._unlocked: set[str] = set()
        layouts.layoutRemoved.connect(self._layout_removed)
        layouts.itemsChanged.connect(self.itemsChanged)

    # --- Section -----------------------------------------------------------------------------

    def load(self, config: Config) -> None:
        self._profiles = list(config.all_profiles())
        self._loaded = {profile.id for profile in self._profiles}
        self._stored = self._vault.protected_ids() if self._vault is not None else frozenset()
        self._pending, self._sealed, self._pending_admin = {}, {}, None
        self._changed()

    def validate(self) -> list[str]:
        problems = []
        seen: set[str] = set()
        for profile in self._profiles:
            if not profile.name.strip():
                problems.append("Hay un perfil sin nombre.")
            elif comparable(profile.name) == comparable(ADMIN_PROFILE_NAME):
                problems.append(f"El nombre «{ADMIN_PROFILE_NAME}» está reservado.")
            elif comparable(profile.name) in seen:
                problems.append(f"El nombre de perfil «{profile.name}» está repetido.")
            seen.add(comparable(profile.name))
        return problems

    def dump(self, documents: Mapping[str, Any]) -> None:
        clean = [
            dataclasses.replace(p, name=" ".join(p.name.split()), user_name=p.user_name.strip())
            for p in self._profiles
        ]
        dump_profiles(documents["profiles.toml"], clean)

    def commit(self) -> None:
        """Contraseñas nuevas, cambiadas o quitadas, y perfiles eliminados, en la base de
        datos. Los archivos ya están escritos."""
        if self._vault is None:
            return
        if self._pending_admin is not None:
            self._vault.install_admin(*self._pending_admin)  # antes: los sellos son para él
        current = self._ids()
        for profile_id, password_hash in self._pending.items():
            if profile_id not in current:
                continue
            if password_hash is None:
                self._vault.clear_password(profile_id)
                continue
            self._vault.set_password_hash(profile_id, password_hash)
            sealed = self._sealed.get(profile_id)
            if sealed is not None:
                self._vault.custody.store_sealed(profile_id, sealed)
            else:
                self._vault.custody.discard(profile_id)  # el sello viejo ya no es su contraseña
        self._pending, self._sealed, self._pending_admin = {}, {}, None

    # --- Para QML ----------------------------------------------------------------------------

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list[dict[str, Any]]:
        return [
            {"id": p.id, "name": p.name, "userName": p.user_name, "layout": p.layout,
             "layoutName": self._layouts.name_of(p.layout),
             "protected": self._protected(p.id), "unlocked": self._editable(p.id)}
            for p in self._profiles
        ]  # fmt: skip

    @Property("QVariantList", notify=itemsChanged)
    def layouts(self) -> list[dict[str, str]]:
        return self._layouts.choices()

    @Slot(result=int)
    def add(self) -> int:
        """Perfil nuevo con la plantilla de fábrica. Devuelve su fila."""
        name = self._free_name("Perfil nuevo")
        self._profiles.append(Profile(make_id(name, self._taken_ids()), name))
        self._changed()
        self.touch()
        return len(self._profiles) - 1

    @Property(bool, constant=True)
    def canProtect(self) -> bool:
        """Se pueden poner contraseñas (hay base de datos)."""
        return self._vault is not None

    @Slot(int, str, result=str)
    def unlock(self, row: int, password: str) -> str:
        """Desbloquea un perfil protegido. Devuelve `concedido`, `denegado` o `bloqueado`
        (tercer fallo: aviso de intrusión registrado; la caja se cierra)."""
        if not 0 <= row < len(self._profiles) or self._vault is None:
            return AttemptOutcome.DENIED.value
        profile_id = self._profiles[row].id
        if self._editable(profile_id):
            return AttemptOutcome.GRANTED.value
        outcome = self._vault.attempt(profile_id, password, AccessOrigin.SETTINGS)
        if outcome is AttemptOutcome.GRANTED:
            self._unlocked.add(profile_id)
            self.itemsChanged.emit()
        return outcome.value

    @Slot(int, str, str, result=str)
    def setPassword(self, row: int, password: str, repeated: str) -> str:
        """Pone o cambia la contraseña. Devuelve el problema, o vacío si vale."""
        if not self._can_edit(row) or self._vault is None:
            return "Desbloquee el perfil para cambiar su contraseña."
        problem = password_problem(password)
        if problem:
            return problem
        if password != repeated:
            return PASSWORDS_DIFFER
        profile_id = self._profiles[row].id
        self._pending[profile_id] = hash_password(password)
        public_key = self._admin_public_key()
        if public_key is not None:
            self._sealed[profile_id] = seal(public_key, password)
        else:
            self._sealed.pop(profile_id, None)
        self._unlocked.add(profile_id)
        self._changed()
        self.touch()
        return ""

    @Slot(int)
    def clearPassword(self, row: int) -> None:
        if not self._can_edit(row) or not self._protected(self._profiles[row].id):
            return
        self._pending[self._profiles[row].id] = None
        self._changed()
        self.touch()

    @Slot(int, result=int)
    def duplicate(self, row: int) -> int:
        """Copia el perfil sin su contraseña. Uno protegido, solo desbloqueado."""
        if not self._can_edit(row):
            return -1
        source = self._profiles[row]
        name = self._free_name(f"{source.name} (copia)")
        self._profiles.append(
            dataclasses.replace(source, id=make_id(name, self._taken_ids()), name=name)
        )
        self._changed()
        self.touch()
        return len(self._profiles) - 1

    # --- Acedor ------------------------------------------------------------------------------

    @Property(bool, notify=itemsChanged)
    def adminActive(self) -> bool:
        """El Acedor está activado (o lo estará al guardar)."""
        if self._pending_admin is not None:
            return True
        return self._vault is not None and self._vault.admin_active()

    @Slot(str, str, result=str)
    def activateAdmin(self, password: str, repeated: str) -> str:
        """Activa al Acedor con su contraseña; se aplica al guardar. Devuelve el problema."""
        if self._vault is None:
            return "No se puede activar el Acedor sin base de datos."
        if self.adminActive:
            return "El Acedor ya está activado."
        problem = password_problem(password) or (PASSWORDS_DIFFER if password != repeated else "")
        if problem:
            return problem
        self._pending_admin = (hash_password(password), *generate_keys(password))
        self._changed()
        self.touch()
        return ""

    @Slot(str, str, str, result=str)
    def changeAdminPassword(self, current: str, password: str, repeated: str) -> str:
        """Contraseña nueva del Acedor, dando la actual. Las contraseñas que custodia siguen
        pudiéndose ver. Un fallo cuenta como intento de acceso al Acedor."""
        if self._vault is None or not self.adminActive:
            return "El Acedor no está activado."
        problem = password_problem(password) or (PASSWORDS_DIFFER if password != repeated else "")
        if problem:
            return problem
        if self._pending_admin is not None:  # activado en este borrador: claves nuevas
            self._pending_admin = (hash_password(password), *generate_keys(password))
        else:
            outcome = self._vault.attempt(ADMIN_PROFILE_ID, current, AccessOrigin.SETTINGS)
            private = self._vault.custody.private_key()
            public = self._vault.custody.public_key()
            rewrapped = None
            if outcome is AttemptOutcome.GRANTED and private is not None:
                rewrapped = rewrap_private(private, current, password)
            if rewrapped is None or public is None:
                return "Clave incorrecta. Acceso denegado."
            self._pending_admin = (hash_password(password), public, rewrapped)
        self._changed()
        self.touch()
        return ""

    def _admin_public_key(self) -> str | None:
        if self._pending_admin is not None:
            return self._pending_admin[1]
        if self._vault is None or not self._vault.admin_active():
            return None
        return self._vault.custody.public_key()

    # Se guarda el texto tal cual, también con espacios a medio escribir: si se recortara aquí,
    # el campo lo reescribiría y se comería el espacio. Se limpia al volcar (`dump`).
    @Slot(int, str)
    def setName(self, row: int, name: str) -> None:
        self._update(row, name=name)

    @Slot(int, str)
    def setUserName(self, row: int, user_name: str) -> None:
        self._update(row, user_name=user_name)

    @Slot(int, str)
    def setLayout(self, row: int, layout_id: str) -> None:
        self._update(row, layout=layout_id)

    # --- Interno -----------------------------------------------------------------------------

    def _protected(self, profile_id: str) -> bool:
        if profile_id in self._pending:
            return self._pending[profile_id] is not None
        return profile_id in self._stored

    def _editable(self, profile_id: str) -> bool:
        return profile_id not in self._stored or profile_id in self._unlocked

    def _can_edit(self, row: int) -> bool:
        return 0 <= row < len(self._profiles) and self._editable(self._profiles[row].id)

    def _update(self, row: int, **changes: str) -> None:
        if not self._can_edit(row):
            return
        updated = dataclasses.replace(self._profiles[row], **changes)
        if updated != self._profiles[row]:
            self._profiles[row] = updated
            self._changed()
            self.touch()

    def _layout_removed(self, layout_id: str) -> None:
        changed = False
        for row, profile in enumerate(self._profiles):
            if profile.layout == layout_id:
                self._profiles[row] = dataclasses.replace(profile, layout="")
                changed = True
        if changed:
            self._changed()
            self.touch()

    def _changed(self) -> None:
        usage: dict[str, list[str]] = {}
        for profile in self._profiles:
            usage.setdefault(profile.layout, []).append(profile.name)
        self._layouts.set_usage(usage)
        self.itemsChanged.emit()

    def _ids(self) -> set[str]:
        return {profile.id for profile in self._profiles}

    def _taken_ids(self) -> set[str]:
        """Ids que un perfil nuevo no puede usar: también los de perfiles eliminados en este
        borrador y los protegidos que ya no están en `profiles.toml`. Así no hereda la
        contraseña ni los recordatorios de otro."""
        return self._ids() | self._loaded | set(self._stored) | {ADMIN_PROFILE_ID}

    def _free_name(self, base: str) -> str:
        taken = {comparable(profile.name) for profile in self._profiles}
        name, number = base, 2
        while comparable(name) in taken:
            name = f"{base} {number}"
            number += 1
        return name
