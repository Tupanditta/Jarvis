"""Apartado Perfiles: nombre del perfil, nombre del usuario (el de «preséntate») y plantilla
predeterminada. Siempre queda al menos uno.

Sin `profiles.toml`, el apartado empieza con el perfil «Predeterminado» que el asistente crea
con `user.name`; el archivo se escribe la primera vez que se guarda un cambio de perfiles.
"""
import dataclasses
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from jarvis_assistant.config import Config, Profile
from jarvis_assistant.config.ids import make_id
from jarvis_assistant.config.profiles import dump_profiles
from jarvis_assistant.configurator.sections.base import Section, comparable
from jarvis_assistant.configurator.sections.layouts import LayoutsSection


class ProfilesSection(Section):
    itemsChanged = Signal()

    files = ("profiles.toml",)

    def __init__(self, layouts: LayoutsSection) -> None:
        super().__init__()
        self._layouts = layouts
        self._profiles: list[Profile] = []
        layouts.layoutRemoved.connect(self._layout_removed)
        layouts.itemsChanged.connect(self.itemsChanged)

    # --- Section -----------------------------------------------------------------------------

    def load(self, config: Config) -> None:
        self._profiles = list(config.all_profiles())
        self._changed()

    def validate(self) -> list[str]:
        problems = []
        seen: set[str] = set()
        for profile in self._profiles:
            if not profile.name.strip():
                problems.append("Hay un perfil sin nombre.")
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

    # --- Para QML ----------------------------------------------------------------------------

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list[dict[str, Any]]:
        return [
            {"id": p.id, "name": p.name, "userName": p.user_name, "layout": p.layout,
             "layoutName": self._layouts.name_of(p.layout)}
            for p in self._profiles
        ]  # fmt: skip

    @Property("QVariantList", notify=itemsChanged)
    def layouts(self) -> list[dict[str, str]]:
        return self._layouts.choices()

    @Slot(result=int)
    def add(self) -> int:
        """Perfil nuevo con la plantilla de fábrica. Devuelve su fila."""
        name = self._free_name("Perfil nuevo")
        self._profiles.append(Profile(make_id(name, self._ids()), name))
        self._changed()
        self.touch()
        return len(self._profiles) - 1

    @Slot(int, result=int)
    def duplicate(self, row: int) -> int:
        if not 0 <= row < len(self._profiles):
            return -1
        source = self._profiles[row]
        name = self._free_name(f"{source.name} (copia)")
        self._profiles.append(
            dataclasses.replace(source, id=make_id(name, self._ids()), name=name)
        )
        self._changed()
        self.touch()
        return len(self._profiles) - 1

    @Slot(int)
    def remove(self, row: int) -> None:
        """Elimina el perfil; el último no se puede eliminar."""
        if 0 <= row < len(self._profiles) and len(self._profiles) > 1:
            del self._profiles[row]
            self._changed()
            self.touch()

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

    def _update(self, row: int, **changes: str) -> None:
        if not 0 <= row < len(self._profiles):
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

    def _free_name(self, base: str) -> str:
        taken = {comparable(profile.name) for profile in self._profiles}
        name, number = base, 2
        while comparable(name) in taken:
            name = f"{base} {number}"
            number += 1
        return name
