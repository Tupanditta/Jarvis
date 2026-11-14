"""`FakePlatform` cumple el `Protocol` de plataforma y simula ventanas y resultados (T-0.4)."""
import inspect
from pathlib import Path

import pytest

from fakes.platform import FakePlatform
from jarvis_assistant.os_adapters.base import (
    AppTarget,
    DiscoveredApp,
    EdgeNotFound,
    PlatformAdapter,
    SearchKind,
    SearchOutcome,
)


def _members(cls) -> dict[str, object]:
    return {
        name: value
        for name, value in vars(cls).items()
        if not name.startswith("_") and (callable(value) or isinstance(value, property))
    }


PROTOCOL_MEMBERS = _members(PlatformAdapter)


def test_el_protocolo_declara_las_operaciones_de_la_especificacion():
    assert set(PROTOCOL_MEMBERS) == {
        "data_dir", "config_dir", "log_dir", "default_places",
        "launch_app", "open_url_in_edge", "open_folder", "open_terminal",
        "open_with_default", "discover_apps",
        "wait_for_window", "window_exists", "focus_window", "can_focus_windows",
        "bring_own_window_to_front", "make_non_activating",
        "indexed_search", "acquire_single_instance",
    }  # fmt: skip


def test_el_doble_es_una_instancia_del_protocolo(tmp_path):
    assert isinstance(FakePlatform(tmp_path), PlatformAdapter)


@pytest.mark.parametrize("name", sorted(PROTOCOL_MEMBERS))
def test_cada_miembro_del_doble_tiene_la_forma_del_protocolo(name):
    expected = PROTOCOL_MEMBERS[name]
    actual = vars(FakePlatform).get(name)
    assert actual is not None, f"FakePlatform no define {name}"
    if isinstance(expected, property):
        assert isinstance(actual, property)
        return
    assert inspect.iscoroutinefunction(actual) == inspect.iscoroutinefunction(expected)
    expected_params = [
        (p.name, p.kind, p.default) for p in inspect.signature(expected).parameters.values()
    ]
    actual_params = [
        (p.name, p.kind, p.default) for p in inspect.signature(actual).parameters.values()
    ]
    assert actual_params == expected_params


def test_las_carpetas_cuelgan_de_la_raiz_y_son_distintas(tmp_path):
    platform = FakePlatform(tmp_path)
    dirs = {platform.data_dir(), platform.config_dir(), platform.log_dir()}
    assert len(dirs) == 3
    assert all(tmp_path in d.parents for d in dirs)


def test_los_lugares_predeterminados_existen(tmp_path):
    places = FakePlatform(tmp_path).default_places()
    assert {"escritorio", "documentos", "descargas"} <= set(places)
    assert all(path.is_dir() for path in places.values())


async def test_lanzar_una_aplicacion_registra_la_llamada_y_crea_su_ventana(tmp_path):
    platform = FakePlatform(tmp_path)
    target = AppTarget(name="Bloc de notas", path="notepad.exe")
    handle = await platform.launch_app(target)
    window = await platform.wait_for_window(handle)
    assert platform.calls[0] == ("launch_app", (target,))
    assert window is not None and "Bloc de notas" in window.title
    assert platform.window_exists(window)


async def test_una_ventana_cerrada_deja_de_existir(tmp_path):
    platform = FakePlatform(tmp_path)
    window = await platform.wait_for_window(await platform.open_folder(tmp_path))
    platform.close_window(window)
    assert not platform.window_exists(window)
    assert not platform.focus_window(window)


async def test_sin_ventana_la_espera_devuelve_none(tmp_path):
    platform = FakePlatform(tmp_path)
    platform.window_appears = False
    assert await platform.wait_for_window(await platform.open_terminal(tmp_path)) is None


async def test_traer_al_frente_registra_la_ventana(tmp_path):
    platform = FakePlatform(tmp_path)
    window = await platform.wait_for_window(await platform.open_folder(tmp_path))
    assert platform.focus_window(window)
    assert platform.focused == [window]
    platform.focus_succeeds = False
    assert not platform.focus_window(window)


async def test_sin_edge_se_lanza_edge_not_found(tmp_path):
    platform = FakePlatform(tmp_path)
    platform.edge_available = False
    with pytest.raises(EdgeNotFound):
        await platform.open_url_in_edge("https://github.com")


async def test_un_fallo_de_lanzamiento_programado_se_propaga(tmp_path):
    platform = FakePlatform(tmp_path)
    platform.launch_error = FileNotFoundError("no existe")
    with pytest.raises(FileNotFoundError):
        await platform.launch_app(AppTarget(name="x", path="x.exe"))


async def test_la_busqueda_indexada_devuelve_lo_programado_o_none(tmp_path):
    platform = FakePlatform(tmp_path)
    assert await platform.indexed_search("informe", SearchKind.FILE, 10) is None
    outcome = SearchOutcome(paths=(Path("C:/a/informe.txt"),), total=1)
    platform.search_outcome = outcome
    assert await platform.indexed_search("informe", SearchKind.FILE, 10) == outcome


def test_descubre_las_aplicaciones_programadas(tmp_path):
    platform = FakePlatform(tmp_path)
    platform.discovered = [DiscoveredApp(name="Paint", path="C:/paint.lnk")]
    assert list(platform.discover_apps()) == platform.discovered


def test_la_instancia_unica_se_concede_una_sola_vez(tmp_path):
    platform = FakePlatform(tmp_path)
    assert platform.acquire_single_instance() is True
    assert platform.acquire_single_instance() is False


def test_las_ventanas_propias_quedan_registradas(tmp_path):
    platform = FakePlatform(tmp_path)
    platform.bring_own_window_to_front(11)
    platform.make_non_activating(22)
    assert platform.calls == [("bring_own_window_to_front", (11,)), ("make_non_activating", (22,))]
