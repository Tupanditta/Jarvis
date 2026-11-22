"""Apartado Plantillas: crear, editar, duplicar y eliminar plantillas de pantalla.

La plantilla de fábrica siempre está, primera, y no se edita ni se elimina; sí se duplica.
Crear y editar abren el editor a pantalla completa (`editor.LayoutEditor`).
"""
import dataclasses
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from jarvis_assistant.config import FACTORY_LAYOUT, FACTORY_LAYOUT_ID, Config, ScreenLayout
from jarvis_assistant.config.ids import make_id
from jarvis_assistant.config.layouts import dump_layouts
from jarvis_assistant.configurator.editor import LayoutEditor
from jarvis_assistant.configurator.sections.base import Section, comparable


class LayoutsSection(Section):
    itemsChanged = Signal()
    layoutRemoved = Signal(str)  # id: los perfiles que la usaban pasan a la de fábrica

    files = ("layouts.toml",)

    def __init__(self, editor: LayoutEditor) -> None:
        super().__init__()
        self._editor = editor
        self._layouts: list[ScreenLayout] = []
        self._used_by: dict[str, list[str]] = {}  # id → nombres de los perfiles que la usan
        editor.finished.connect(self._commit)

    # --- Section -----------------------------------------------------------------------------

    def load(self, config: Config) -> None:
        self._layouts = list(config.layouts)
        self.itemsChanged.emit()

    def validate(self) -> list[str]:
        problems = []
        seen: set[str] = {comparable(FACTORY_LAYOUT.name)}
        for layout in self._layouts:
            if not layout.name.strip():
                problems.append("Hay una plantilla sin nombre.")
            elif comparable(layout.name) in seen:
                problems.append(f"El nombre de plantilla «{layout.name}» está repetido.")
            seen.add(comparable(layout.name))
        return problems

    def dump(self, documents: Mapping[str, Any]) -> None:
        dump_layouts(documents["layouts.toml"], self._layouts)

    # --- Para otros apartados ----------------------------------------------------------------

    def choices(self) -> list[dict[str, str]]:
        """Las plantillas para elegir, la de fábrica primero: `{id, name}`."""
        return [{"id": "", "name": FACTORY_LAYOUT.name}] + [
            {"id": layout.id, "name": layout.name} for layout in self._layouts
        ]

    def name_of(self, layout_id: str) -> str:
        return next(
            (layout.name for layout in self._layouts if layout.id == layout_id),
            FACTORY_LAYOUT.name,
        )

    def set_usage(self, used_by: dict[str, list[str]]) -> None:
        """Qué perfiles usan cada plantilla, para avisar al eliminarla."""
        self._used_by = used_by
        self.itemsChanged.emit()

    # --- Para QML ----------------------------------------------------------------------------

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list[dict[str, Any]]:
        rows = [{"id": FACTORY_LAYOUT_ID, "name": FACTORY_LAYOUT.name, "factory": True,
                 "usedBy": ", ".join(self._used_by.get("", []))}]  # fmt: skip
        rows += [
            {"id": layout.id, "name": layout.name, "factory": False,
             "usedBy": ", ".join(self._used_by.get(layout.id, []))}
            for layout in self._layouts
        ]  # fmt: skip
        return rows

    @Slot()
    def create(self) -> None:
        """Nueva plantilla a partir de la de fábrica."""
        name = self._free_name("Plantilla nueva")
        new = dataclasses.replace(FACTORY_LAYOUT, id=make_id(name, self._ids()), name=name)
        self._editor.begin(new, self.name_problem)

    @Slot(str)
    def edit(self, layout_id: str) -> None:
        layout = self._find(layout_id)
        if layout is not None:
            self._editor.begin(layout, self.name_problem)

    @Slot(str)
    def duplicate(self, layout_id: str) -> None:
        source = self._find(layout_id) or FACTORY_LAYOUT
        name = self._free_name(f"{source.name} (copia)")
        self._layouts.append(dataclasses.replace(source, id=make_id(name, self._ids()), name=name))
        self.itemsChanged.emit()
        self.touch()

    @Slot(str)
    def remove(self, layout_id: str) -> None:
        if self._find(layout_id) is None:
            return
        self._layouts = [layout for layout in self._layouts if layout.id != layout_id]
        self.itemsChanged.emit()
        self.layoutRemoved.emit(layout_id)
        self.touch()

    def name_problem(self, layout_id: str, name: str) -> str:
        if not name:
            return "Escriba un nombre para la plantilla."
        taken = {comparable(FACTORY_LAYOUT.name)} | {
            comparable(layout.name) for layout in self._layouts if layout.id != layout_id
        }
        if comparable(name) in taken:
            return f"Ya hay una plantilla que se llama «{name}»."
        return ""

    # --- Interno -----------------------------------------------------------------------------

    def _commit(self, layout: ScreenLayout) -> None:
        """El editor ha aceptado: sustituye la plantilla o la añade si es nueva."""
        for index, current in enumerate(self._layouts):
            if current.id == layout.id:
                self._layouts[index] = layout
                break
        else:
            self._layouts.append(layout)
        self.itemsChanged.emit()
        self.touch()

    def _find(self, layout_id: str) -> ScreenLayout | None:
        return next((layout for layout in self._layouts if layout.id == layout_id), None)

    def _ids(self) -> set[str]:
        return {FACTORY_LAYOUT_ID} | {layout.id for layout in self._layouts}

    def _free_name(self, base: str) -> str:
        taken = {comparable(FACTORY_LAYOUT.name)} | {comparable(x.name) for x in self._layouts}
        name, number = base, 2
        while comparable(name) in taken:
            name = f"{base} {number}"
            number += 1
        return name
