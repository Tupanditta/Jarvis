"""Módulo Catálogo: añadir y eliminar aplicaciones, páginas y comandos, con `ContextRig`."""
import dataclasses

import pytest

from fakes.context import CANCEL, ContextRig
from jarvis_assistant.action_modules.catalog_manager import ENTRIES, CatalogManager
from jarvis_assistant.config import AppEntry, Binary, Catalog, Config, PageEntry, RouterSettings
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import ExpectedType, Phrase
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.intent_router.router import IntentRouter

CATALOG = Catalog(
    discover_installed_apps=False,
    apps=(AppEntry("Editor", "C:/editor.exe", ("el editor",), ("--nuevo",)),),
    pages=(PageEntry("GitHub", "https://github.com", ("git hub",)),),
)
BINARIES = (Binary("git", "git", ("guit",)), Binary("npm", "npm", timeout_seconds=60))


class Saver:
    """`ctx.save_launchers` de mentira: guarda lo que recibe y aplica el cambio en `ctx`."""

    def __init__(self, rig: ContextRig) -> None:
        self.rig = rig
        self.calls: list[tuple[Catalog | None, tuple[Binary, ...] | None]] = []
        self.failure = ""

    async def __call__(self, catalog=None, binaries=None) -> str:
        self.calls.append((catalog, binaries))
        if self.failure:
            return self.failure
        changes = {}
        if catalog is not None:
            changes["catalog"] = catalog
        if binaries is not None:
            changes["binaries"] = tuple(binaries)
        self.rig.ctx.config = dataclasses.replace(self.rig.ctx.config, **changes)
        return ""


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path, config=Config(catalog=CATALOG, binaries=BINARIES))
    rig.saver = Saver(rig)
    rig.ctx.save_launchers = rig.saver
    yield rig
    rig.close()


@pytest.fixture
async def module(rig):
    module = CatalogManager()
    await module.on_session_opened(rig.ctx)
    return module


def shown(rig) -> events.CatalogShown:
    return rig.last(events.CatalogShown)


def ids(rig) -> list[str]:
    return [item.id for item in shown(rig).items]


async def add(module, rig, **params):
    return await module.execute("añadir", params, rig.ctx)


# --- Ver -------------------------------------------------------------------------------------


async def test_al_abrir_la_sesion_la_ventana_recibe_todo_el_catalogo(rig, module):
    assert ids(rig) == ["aplicacion:Editor", "pagina:GitHub", "comando:git", "comando:npm"]
    editor = shown(rig).items[0]
    assert (editor.kind, editor.target, editor.aliases, editor.args) == (
        "aplicacion", "C:/editor.exe", ("el editor",), ("--nuevo",),
    )  # fmt: skip
    assert shown(rig).items[2].target == "git"
    assert shown(rig).problem == ""


async def test_ver_el_catalogo(rig, module):
    result = await module.execute("ver", {}, rig.ctx)
    assert result.status == "completado"
    assert result.speech == Phrase("catalogo.mostrado")


# --- Añadir ----------------------------------------------------------------------------------


async def test_anadir_una_aplicacion_la_guarda_con_sus_alias_y_argumentos(rig, module):
    result = await add(
        module, rig, tipo="aplicacion", nombre="  Visual   Code ", destino=" code.exe ",
        alias="code, vs code\nel código", argumentos="-n\n--wait",
    )  # fmt: skip
    assert result.status == "completado"
    assert result.speech == Phrase("catalogo.anadido", {"nombre": "Visual Code"})
    ((catalog, binaries),) = rig.saver.calls
    assert binaries is None
    assert catalog.apps[-1] == AppEntry(
        "Visual Code", "code.exe", ("code", "vs code", "el código"), ("-n", "--wait")
    )
    assert catalog.pages == CATALOG.pages
    assert catalog.discover_installed_apps is False  # lo demás del catálogo se conserva
    assert ids(rig)[1] == "aplicacion:Visual Code"


async def test_anadir_una_pagina_y_un_comando(rig, module):
    await add(module, rig, tipo="pagina", nombre="Docs", destino="https://example.com/docs")
    await add(module, rig, tipo="comando", nombre="cargo", destino="C:/rust/cargo.exe",
              alias="cargou")  # fmt: skip
    (catalog, _), (_, binaries) = rig.saver.calls
    assert catalog.pages[-1] == PageEntry("Docs", "https://example.com/docs")
    assert binaries == (*BINARIES, Binary("cargo", "C:/rust/cargo.exe", ("cargou",)))
    assert ids(rig)[-1] == "comando:cargo"
    assert "pagina:Docs" in ids(rig)


@pytest.mark.parametrize("params, fragment", [
    ({"tipo": "aplicacion", "nombre": "", "destino": "x.exe"}, "nombre"),
    ({"tipo": "aplicacion", "nombre": "X", "destino": ""}, "ruta"),
    ({"tipo": "pagina", "nombre": "P", "destino": "example.com"}, "http"),
    ({"tipo": "comando", "nombre": "cargo", "destino": " "}, "ejecutable"),
    ({"tipo": "pagina", "nombre": "Otra", "destino": "https://x.com", "alias": "EL EDITOR"},
     "ya es el nombre de otra aplicación o página"),
    ({"tipo": "aplicacion", "nombre": "github", "destino": "gh.exe"}, "ya es el nombre"),
    ({"tipo": "comando", "nombre": "Guit", "destino": "git2"}, "ya es el nombre de otro comando"),
])  # fmt: skip
async def test_lo_que_no_vale_no_se_guarda_y_la_ventana_recibe_el_motivo(
    rig, module, params, fragment
):
    result = await module.execute("añadir", params, rig.ctx)
    assert result.status == "error"
    assert result.speech == Phrase("catalogo.no_valido")
    assert fragment in result.detail
    assert fragment in shown(rig).problem
    assert rig.saver.calls == []


async def test_un_comando_puede_llamarse_como_una_aplicacion(rig, module):
    result = await add(module, rig, tipo="comando", nombre="Editor", destino="vim")
    assert result.status == "completado"


async def test_si_no_se_puede_guardar_nada_cambia(rig, module):
    rig.saver.failure = "catalog.toml: disco lleno"
    result = await add(module, rig, tipo="pagina", nombre="Docs", destino="https://e.com")
    assert result.status == "error"
    assert result.speech == Phrase("catalogo.no_guardado")
    assert "disco lleno" in shown(rig).problem
    assert "pagina:Docs" not in ids(rig)


async def test_anadir_por_voz_pide_usar_la_ventana(rig, module):
    result = await module.execute("añadir", {}, rig.ctx)
    assert result.status == "completado"
    assert result.speech == Phrase("catalogo.usar_ventana")
    assert rig.saver.calls == []


# --- Eliminar --------------------------------------------------------------------------------


async def test_eliminar_desde_la_ventana_pregunta_y_quita_la_entrada(rig, module):
    rig.answers = [True]
    result = await module.execute("eliminar", {"entrada": "pagina:GitHub"}, rig.ctx)
    assert result.status == "completado"
    assert result.speech == Phrase("catalogo.eliminado", {"nombre": "GitHub"})
    (asked,) = rig.asked
    assert asked.question == Phrase("catalogo.confirmar", {"nombre": "GitHub"})
    assert asked.expected_type is ExpectedType.BOOLEAN
    ((catalog, binaries),) = rig.saver.calls
    assert catalog.pages == () and catalog.apps == CATALOG.apps and binaries is None
    assert "pagina:GitHub" not in ids(rig)


async def test_eliminar_un_comando_por_uno_de_sus_nombres(rig, module):
    rig.answers = [True]
    await module.execute("eliminar", {"entrada": "Guit"}, rig.ctx)
    ((catalog, binaries),) = rig.saver.calls
    assert catalog is None
    assert binaries == (BINARIES[1],)


async def test_si_no_se_confirma_no_se_elimina(rig, module):
    rig.answers = [CANCEL]
    result = await module.execute("eliminar", {"entrada": "aplicacion:Editor"}, rig.ctx)
    assert result.detail == "cancelada"
    rig.answers = [False]
    await module.execute("eliminar", {"entrada": "aplicacion:Editor"}, rig.ctx)
    assert rig.saver.calls == []


async def test_eliminar_algo_que_ya_no_esta(rig, module):
    result = await module.execute("eliminar", {"entrada": "aplicacion:Nada"}, rig.ctx)
    assert result.status == "error"
    assert result.speech == Phrase("catalogo.no_encontrado")
    assert rig.asked == []


# --- Órdenes ---------------------------------------------------------------------------------


def test_las_ordenes_de_voz_resuelven_contra_el_catalogo(rig):
    module = CatalogManager()
    module._catalog, module._binaries = CATALOG, BINARIES
    router = IntentRouter(RouterSettings())
    router.register(module)
    routed = router.route("quita git hub del catálogo", AssistantState.LISTENING_COMMAND)
    assert (routed.intent.action, routed.intent.params) == ("eliminar", {"entrada": "git hub"})
    shown_ = router.route("muestra el catálogo", AssistantState.LISTENING_COMMAND)
    assert shown_.intent.action == "ver"
    assert set(module.catalogs()) == {ENTRIES}
