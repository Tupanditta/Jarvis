"""Módulo Apertura (apertura-apps.md) con `FakePlatform`."""
from pathlib import Path

import pytest

from fakes.context import ContextRig, settle
from jarvis_assistant.action_modules.app_launcher import MAX_ITEMS, OPENED, TARGETS, AppLauncher
from jarvis_assistant.config import AppEntry, Catalog, Config, PageEntry, RouterSettings
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.core.content import OpenedItem
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.intent_router.router import IntentRouter
from jarvis_assistant.os_adapters.base import AppTarget, DiscoveredApp

CATALOG = Catalog(
    apps=(
        AppEntry("Visual Studio Code", "code.exe", aliases=("code", "el editor"), args=("-n",)),
        AppEntry("Notas", "notas-catalogo.exe"),
    ),
    pages=(
        PageEntry("GitHub", "https://github.com", aliases=("git hub",)),
        PageEntry("Notas", "https://notas.example.com"),
    ),
)


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path, config=Config(catalog=CATALOG))
    rig.platform.discovered = [
        DiscoveredApp("Calculadora", "calc.lnk"), DiscoveredApp("Notas", "notas.lnk"),
    ]  # fmt: skip
    yield rig
    rig.close()


@pytest.fixture
async def module(rig):
    module = AppLauncher()
    module._catalog = CATALOG
    await module.discover(rig.platform)
    rig.platform.calls.clear()
    return module


def items(rig) -> tuple[OpenedItem, ...]:
    return rig.last(events.OpenedItemsChanged).items


def resolve(module, text):
    router = IntentRouter(RouterSettings())
    router.register(module)
    return router.route(text, AssistantState.LISTENING_COMMAND).intent


# --- Qué se puede abrir (RN-49) --------------------------------------------------------------


async def test_abre_una_aplicacion_del_catalogo(rig, module):
    result = await module.execute("abrir", {"objetivo": "el editor"}, rig.ctx)
    await settle()
    assert result.status == "completado"
    assert result.speech == Phrase("apertura.abriendo", {"nombre": "Visual Studio Code"})
    assert rig.platform.calls[0] == (
        "launch_app", (AppTarget("Visual Studio Code", "code.exe", ("-n",)),)
    )
    assert items(rig) == (OpenedItem(1, "Visual Studio Code", "aplicacion", "completado", True),)


async def test_abre_una_pagina_del_catalogo_con_edge(rig, module):
    result = await module.execute("abrir", {"objetivo": "GitHub"}, rig.ctx)
    await settle()
    assert result.speech == Phrase("apertura.abriendo", {"nombre": "GitHub"})
    assert rig.platform.calls[0] == ("open_url_in_edge", ("https://github.com",))
    assert items(rig)[0].kind == "pagina"
    # Solo se abren las URLs del catálogo y solo con Edge.
    assert [name for name, _ in rig.platform.calls] == ["open_url_in_edge", "wait_for_window"]


async def test_abre_una_aplicacion_descubierta(rig, module):
    result = await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    assert result.status == "completado"
    assert rig.platform.calls[0] == ("launch_app", (AppTarget("Calculadora", "calc.lnk"),))


async def test_orden_de_resolucion_aplicaciones_paginas_descubiertas(rig, module):
    # «Notas» está en las tres fuentes: gana el catálogo de aplicaciones.
    assert resolve(module, "abre notas").params == {"objetivo": "Notas"}
    await module.execute("abrir", {"objetivo": "Notas"}, rig.ctx)
    assert rig.platform.calls[0] == ("launch_app", (AppTarget("Notas", "notas-catalogo.exe"),))
    # Sin esa aplicación, gana la página; sin la página, la descubierta.
    module._catalog = Catalog(pages=CATALOG.pages)
    rig.ctx.config = Config(catalog=module._catalog)
    rig.platform.calls.clear()
    await module.execute("abrir", {"objetivo": "Notas"}, rig.ctx)
    assert rig.platform.calls[0] == ("open_url_in_edge", ("https://notas.example.com",))
    module._catalog = Catalog()
    rig.ctx.config = Config()
    rig.platform.calls.clear()
    await module.execute("abrir", {"objetivo": "Notas"}, rig.ctx)
    assert rig.platform.calls[0] == ("launch_app", (AppTarget("Notas", "notas.lnk"),))


async def test_las_fuentes_del_catalogo_van_en_orden(module):
    apps, pages, discovered = (provider() for provider in module.catalogs()[TARGETS])
    assert apps == ["Visual Studio Code", "code", "el editor", "Notas"]
    assert pages == ["GitHub", "git hub", "Notas"]
    assert discovered == ["Calculadora", "Notas"]


async def test_sin_descubrimiento_no_se_ofrecen_las_aplicaciones_instaladas(rig, module):
    module._catalog = Catalog(discover_installed_apps=False)
    assert module.catalogs()[TARGETS][2]() == []
    rig.ctx.config = Config(catalog=module._catalog)
    result = await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    assert result.status == "error"


async def test_nombre_sin_coincidencia(rig, module):
    intent = resolve(module, "abre el navegador")
    assert intent.error == Phrase("entidad.no_encontrado", {"nombre": "el navegador"})
    result = await module.execute("abrir", {"objetivo": "Navegador"}, rig.ctx)
    assert result.speech == Phrase("entidad.no_encontrado", {"nombre": "Navegador"})
    assert rig.platform.calls == []


async def test_edge_no_instalado(rig, module):
    rig.platform.edge_available = False
    result = await module.execute("abrir", {"objetivo": "GitHub"}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("apertura.sin_edge"))
    assert items(rig) == (OpenedItem(1, "GitHub", "pagina", "error", False),)


async def test_fallo_al_lanzar(rig, module):
    rig.platform.launch_error = OSError("no arranca")
    result = await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    assert (result.status, result.speech) == (
        "error", Phrase("apertura.fallo", {"nombre": "Calculadora"}),
    )  # fmt: skip
    assert items(rig)[0].status == "error"


# --- Carpetas (RN-41, RN-42) -----------------------------------------------------------------


async def test_abre_una_carpeta_absoluta_relativa_o_la_actual(rig, module):
    (rig.home / "Docs" / "sub").mkdir(parents=True)
    absolute = await module.execute("abrir_carpeta", {"ruta": rig.home / "Docs"}, rig.ctx)
    assert absolute.speech == Phrase("apertura.abriendo", {"nombre": "Docs"})
    rig.workdir.change(rig.home / "Docs")
    await module.execute("abrir_carpeta", {"ruta": Path("sub")}, rig.ctx)
    await module.execute("abrir_carpeta", {}, rig.ctx)
    await settle()
    opened = [args[0] for name, args in rig.platform.calls if name == "open_folder"]
    assert opened == [rig.home / "Docs", rig.home / "Docs" / "sub", rig.home / "Docs"]
    assert [item.kind for item in items(rig)] == ["carpeta"] * 3
    assert rig.workdir.path == rig.home / "Docs"  # abrir no cambia el directorio de trabajo


async def test_carpeta_inexistente_o_que_no_es_carpeta(rig, module):
    (rig.home / "notas.txt").write_text("x")
    missing = await module.execute("abrir_carpeta", {"ruta": rig.home / "nada"}, rig.ctx)
    assert missing.speech == Phrase("ruta.no_existe", {"nombre": "nada"})
    a_file = await module.execute("abrir_carpeta", {"ruta": rig.home / "notas.txt"}, rig.ctx)
    assert a_file.speech == Phrase("ruta.no_es_carpeta", {"nombre": "notas.txt"})
    assert rig.platform.calls == [] and rig.events == []


async def test_fallo_del_gestor_de_archivos(rig, module):
    rig.platform.launch_error = OSError("sin gestor")
    result = await module.execute("abrir_carpeta", {}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("ruta.gestor_fallo"))


# --- Elementos abiertos y «traer al frente» --------------------------------------------------


async def test_la_ventana_localizada_activa_el_boton(rig, module):
    await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    assert not items(rig)[0].can_focus  # todavía se está buscando
    await settle()
    assert items(rig)[0].can_focus
    wait = next(args for name, args in rig.platform.calls if name == "wait_for_window")
    assert wait[1] == 10.0


async def test_si_no_se_localiza_la_ventana_la_tarjeta_queda_sin_boton(rig, module):
    rig.platform.window_appears = False
    result = await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    await settle()
    assert result.status == "completado"
    assert not items(rig)[0].can_focus


async def test_la_ventana_de_una_pagina_es_la_de_edge(rig, module):
    await module.execute("abrir", {"objetivo": "GitHub"}, rig.ctx)
    await settle()
    handle = next(args[0] for name, args in rig.platform.calls if name == "wait_for_window")
    assert handle.title_hint == "Edge"


async def test_traer_al_frente_con_una_orden_y_con_el_boton(rig, module):
    await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    await module.execute("abrir", {"objetivo": "GitHub"}, rig.ctx)
    await settle()
    assert module.catalogs()[OPENED][0]() == ["Calculadora", "GitHub"]
    assert resolve(module, "trae al frente github").params == {"objetivo": "GitHub"}
    by_name = await module.execute("traer_al_frente", {"objetivo": "GitHub"}, rig.ctx)
    assert (by_name.status, by_name.speech) == ("completado", None)
    action, params = module.user_actions()[events.FocusItemRequested](
        events.FocusItemRequested(1)
    )
    by_click = await module.execute(action, params, rig.ctx)
    assert by_click.status == "completado"
    assert [ref.title for ref in rig.platform.focused] == ["Edge", "Calculadora"]


async def test_traer_al_frente_una_ventana_cerrada_desactiva_el_boton(rig, module):
    await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    await settle()
    rig.platform.close_window(module._items[0].window)
    result = await module.execute("traer_al_frente", {"id": 1}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("apertura.ventana_cerrada"))
    assert not items(rig)[0].can_focus


async def test_traer_al_frente_sin_soporte_del_sistema(rig, module):
    await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    await settle()
    rig.platform.can_focus = False
    result = await module.execute("traer_al_frente", {"id": 1}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("general.no_disponible"))
    await module.execute("abrir", {"objetivo": "GitHub"}, rig.ctx)
    assert not rig.last(events.OpenedItemsChanged).can_focus_windows


async def test_la_lista_guarda_los_doce_ultimos(rig, module):
    for _ in range(MAX_ITEMS + 2):
        await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    assert [item.id for item in items(rig)] == list(range(3, MAX_ITEMS + 3))


async def test_al_cerrar_la_sesion_la_lista_se_vacia(rig, module):
    await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    await module.on_session_closed(rig.ctx)
    await settle()
    assert items(rig) == ()
    assert module.catalogs()[OPENED][0]() == []


async def test_al_abrir_la_sesion_usa_el_catalogo_vigente_y_descubre(rig):
    module = AppLauncher()
    await module.on_session_opened(rig.ctx)
    await module._discovery
    assert module.catalogs()[TARGETS][0]()[0] == "Visual Studio Code"
    assert module.catalogs()[TARGETS][2]() == ["Calculadora", "Notas"]
    assert items(rig) == ()


async def test_ninguna_accion_trae_al_frente_la_ventana_del_asistente(rig, module):
    (rig.home / "Docs").mkdir()
    await module.execute("abrir", {"objetivo": "Calculadora"}, rig.ctx)
    await module.execute("abrir", {"objetivo": "GitHub"}, rig.ctx)
    await module.execute("abrir_carpeta", {"ruta": rig.home / "Docs"}, rig.ctx)
    await settle()
    await module.execute("traer_al_frente", {"id": 1}, rig.ctx)
    assert "bring_own_window_to_front" not in [name for name, _ in rig.platform.calls]


def test_todas_las_acciones_activan_el_panel_de_aperturas():
    assert {spec.panel for spec in AppLauncher().intents()} == {"aperturas"}
