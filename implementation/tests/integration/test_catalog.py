"""Módulo Catálogo de principio a fin, con dobles: lo que se añade o se elimina desde su
ventana se escribe en los archivos y vale en la misma sesión."""
import pytest

from fakes.context import settle
from integration.test_orders import Rig, said
from jarvis_assistant import config as cfg
from jarvis_assistant.config.writer import save_launchers
from jarvis_assistant.core import events
from jarvis_assistant.core.state_machine import AssistantState


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    rig = Rig(tmp_path, monkeypatch)
    rig.config_dir = tmp_path / "config"
    rig.app.orchestrator._save_launchers_file = lambda catalog, binaries: save_launchers(
        rig.config_dir, catalog, binaries
    )
    rig.shown = []
    rig.app.bus.subscribe(events.CatalogShown, rig.shown.append)
    await rig.start()
    await rig.open_session()
    yield rig
    await rig.stop()


def request(rig, action: str, **params) -> None:
    rig.app.bus.publish(events.ActionRequested("catalogo", action, params))


def on_disk(rig) -> cfg.Config:
    config, errors = cfg.load(rig.config_dir)
    assert [error for error in errors if not error.warning] == []
    return config


async def test_una_pagina_anadida_se_abre_en_la_misma_sesion(rig):
    request(rig, "añadir", tipo="pagina", nombre="Docs", destino="https://example.com/docs",
            alias="la documentación")  # fmt: skip
    await rig.advance(1.0)
    assert rig.tasks()[-1] == ("catalogo", "Página Docs añadida al catálogo", "completado")
    assert said("catalogo.anadido", nombre="Docs") in rig.spoken()
    assert on_disk(rig).catalog.pages[-1] == cfg.PageEntry(
        "Docs", "https://example.com/docs", ("la documentación",)
    )
    assert rig.shown[-1].problem == ""
    await rig.order("abre la documentación")
    assert ("open_url_in_edge", ("https://example.com/docs",)) in rig.platform.calls


async def test_un_comando_anadido_se_ejecuta_en_la_misma_sesion(rig):
    request(rig, "añadir", tipo="comando", nombre="cargo", destino="C:/rust/cargo.exe")
    await rig.advance(1.0)
    assert on_disk(rig).binaries[-1] == cfg.Binary("cargo", "C:/rust/cargo.exe")
    await rig.write("ejecuta cargo build")
    await rig.advance(0.5)
    assert len(rig.processes) == 1
    assert rig.tasks()[-1][:2] == ("comandos", "cargo build")


async def test_eliminar_pide_confirmacion_y_lo_quita_del_archivo(rig):
    request(rig, "eliminar", entrada="pagina:GitHub")
    await rig.advance(1.0)
    assert rig.state is AssistantState.AWAITING_CONFIRMATION
    assert said("catalogo.confirmar", nombre="GitHub") in rig.spoken()
    await rig.write("sí")
    await rig.advance(1.0)
    assert on_disk(rig).catalog.pages == ()
    assert [item.id for item in rig.shown[-1].items if item.kind == "pagina"] == []
    await rig.order("abre GitHub")
    assert "open_url_in_edge" not in [name for name, _ in rig.platform.calls]


async def test_un_formulario_no_valido_no_escribe_nada(rig):
    request(rig, "añadir", tipo="pagina", nombre="Otra", destino="example.com")
    await rig.advance(1.0)
    await settle()
    assert "http" in rig.shown[-1].problem
    assert rig.tasks()[-1][2] == "error"
    assert not rig.config_dir.exists()
