"""Registro de apartados de la ventana de configuración.

Igual que `ui.workspace.WINDOWS` declara las ventanas flotantes, `SECTIONS` declara los
apartados, en el orden en que se muestran. Añadir un apartado es añadir aquí su `SectionSpec`,
su clase en `sections/` y su página en `qml/sections/`.

`create` recibe el contexto con el editor de plantillas y los apartados ya creados (los de
arriba en la lista), por si depende de alguno.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from jarvis_assistant.configurator.editor import LayoutEditor
from jarvis_assistant.configurator.sections.base import Section
from jarvis_assistant.configurator.sections.catalog import CatalogSection
from jarvis_assistant.configurator.sections.layouts import LayoutsSection
from jarvis_assistant.configurator.sections.profiles import ProfilesSection
from jarvis_assistant.configurator.sections.sound import SoundSection


@dataclass(frozen=True)
class SectionContext:
    editor: LayoutEditor
    sections: Mapping[str, Section]


@dataclass(frozen=True)
class SectionSpec:
    id: str
    title: str
    icon: str  # de `ui/assets/icons/`
    page: str  # archivo de `qml/sections/`
    create: Callable[[SectionContext], Section]


def _profiles(context: SectionContext) -> Section:
    layouts = context.sections["plantillas"]
    assert isinstance(layouts, LayoutsSection)
    return ProfilesSection(layouts)


SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("plantillas", "Plantillas", "pantalla", "LayoutsPage.qml",
                lambda context: LayoutsSection(context.editor)),
    SectionSpec("perfiles", "Perfiles", "sesion", "ProfilesPage.qml", _profiles),
    SectionSpec("sonido", "Sonido", "silencio", "SoundPage.qml", lambda _context: SoundSection()),
    SectionSpec("aplicaciones", "Aplicaciones", "aplicacion", "CatalogPage.qml",
                lambda _context: CatalogSection()),
)  # fmt: skip
