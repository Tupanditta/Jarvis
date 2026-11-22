"""Adaptador de Windows (plataforma.md): lanzamiento, ventanas externas y búsqueda (T-3.4).

Las operaciones se prueban con dobles inyectados; las de solo lectura, además, contra el
sistema real cuando las pruebas corren en Windows.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from jarvis_assistant.os_adapters import windows
from jarvis_assistant.os_adapters.base import (
    AppTarget,
    EdgeNotFound,
    LaunchHandle,
    PlatformAdapter,
    SearchKind,
    WindowRef,
)
from jarvis_assistant.os_adapters.windows import WindowsAdapter

only_windows = pytest.mark.skipif(sys.platform != "win32", reason="solo en Windows")


class Recorder:
    """Dobles de `Popen`, `os.startfile` y `es.exe`."""

    def __init__(self) -> None:
        self.popen_calls: list[tuple[list[str], dict]] = []
        self.started: list[str] = []
        self.searches: list[list[str]] = []
        self.search_result = SimpleNamespace(returncode=0, stdout=b"")
        self.tools: dict[str, str] = {}
        self.windows: list[tuple[int, int, str]] = []
        self.slept = 0.0

    def popen(self, command, **kwargs):
        self.popen_calls.append((list(command), kwargs))
        return SimpleNamespace(pid=500 + len(self.popen_calls))

    def run_search(self, command):
        self.searches.append(list(command))
        return self.search_result

    async def sleep(self, seconds: float) -> None:
        self.slept += seconds


@pytest.fixture
def recorder():
    return Recorder()


@pytest.fixture
def make(tmp_path, recorder):
    def make(environ=None, **kwargs):
        options = {
            "user32": None,
            "popen": recorder.popen,
            "startfile": recorder.started.append,
            "which": recorder.tools.get,
            "known_folder": lambda _id: None,
            "edge_registry": lambda: None,
            "run_search": recorder.run_search,
            "sleep": recorder.sleep,
        }
        options.update(kwargs)
        adapter = WindowsAdapter(environ or {}, home=tmp_path, **options)
        adapter._windows = lambda: list(recorder.windows)  # type: ignore[method-assign]
        return adapter

    return make


def test_el_adaptador_cumple_el_protocolo(make):
    assert isinstance(make(), PlatformAdapter)


# --- Carpetas --------------------------------------------------------------------------------


def test_lugares_predeterminados_usan_las_carpetas_conocidas(make, tmp_path):
    redirected = tmp_path / "OneDrive" / "Documentos"
    adapter = make(
        known_folder=lambda folder_id: redirected
        if folder_id == windows.KNOWN_FOLDERS["documentos"][0]
        else None
    )
    places = adapter.default_places()
    assert set(places) == {"escritorio", "documentos", "descargas", "imagenes", "musica", "videos"}
    assert places["documentos"] == redirected  # respeta la redirección
    assert places["descargas"] == tmp_path / "Downloads"  # sin respuesta: la habitual


@only_windows
def test_lugares_predeterminados_reales():
    places = WindowsAdapter().default_places()
    assert places["documentos"].is_absolute()
    assert places["escritorio"].is_dir()


# --- Lanzamiento -----------------------------------------------------------------------------


async def test_lanza_un_ejecutable_con_popen_sin_esperar(make, recorder):
    recorder.windows = [(1, 10, "Otra")]
    handle = await make().launch_app(AppTarget("Editor", "code.exe", ("-n",)))
    assert recorder.popen_calls == [(["code.exe", "-n"], {})]
    assert handle == LaunchHandle(501, "Editor", frozenset({1}))
    assert "shell" not in recorder.popen_calls[0][1]


async def test_lanza_un_acceso_directo_con_startfile(make, recorder):
    handle = await make().launch_app(AppTarget("Calculadora", "C:/menu/Calculadora.lnk"))
    assert recorder.started == ["C:/menu/Calculadora.lnk"]
    assert recorder.popen_calls == []
    assert handle.pid is None and handle.title_hint == "Calculadora"


async def test_abre_una_url_solo_con_edge(make, recorder, tmp_path):
    edge = tmp_path / "pf" / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.write_text("")
    adapter = make({"ProgramFiles(x86)": str(tmp_path / "pf")})
    handle = await adapter.open_url_in_edge("https://github.com")
    assert recorder.popen_calls == [([str(edge), "https://github.com"], {})]
    assert handle.title_hint == "Edge" and handle.known_windows == frozenset()


async def test_edge_del_registro_tiene_prioridad(make, tmp_path):
    registry = tmp_path / "msedge.exe"
    registry.write_text("")
    assert make(edge_registry=lambda: registry).edge_path() == registry
    assert make(edge_registry=lambda: tmp_path / "no-existe.exe").edge_path() is None


async def test_sin_edge_no_se_abre_nada(make, recorder):
    with pytest.raises(EdgeNotFound):
        await make().open_url_in_edge("https://github.com")
    assert recorder.popen_calls == []


async def test_abre_una_carpeta_con_el_explorador(make, recorder, tmp_path):
    handle = await make().open_folder(tmp_path / "Docs")
    assert recorder.popen_calls == [(["explorer.exe", str(tmp_path / "Docs")], {})]
    assert handle.title_hint == "Docs"


async def test_abre_windows_terminal_o_cmd_en_el_directorio(make, recorder, tmp_path):
    await make().open_terminal(tmp_path)
    assert recorder.popen_calls[0] == (
        ["cmd.exe"], {"cwd": str(tmp_path), "creationflags": windows.CREATE_NEW_CONSOLE}
    )
    recorder.tools["wt.exe"] = "C:/apps/wt.exe"
    await make().open_terminal(tmp_path)
    assert recorder.popen_calls[1] == (["C:/apps/wt.exe", "-d", str(tmp_path)], {})


async def test_abre_ubuntu_en_el_directorio_si_hay_wsl(make, recorder, tmp_path):
    recorder.tools["wsl.exe"] = "C:/Windows/wsl.exe"
    await make().open_terminal(tmp_path)
    assert recorder.popen_calls[0] == (
        ["C:/Windows/wsl.exe", "--cd", str(tmp_path)],
        {"cwd": str(tmp_path), "creationflags": windows.CREATE_NEW_CONSOLE},
    )
    recorder.tools["wt.exe"] = "C:/apps/wt.exe"
    await make().open_terminal(tmp_path)
    assert recorder.popen_calls[1] == (
        ["C:/apps/wt.exe", "-d", str(tmp_path), "C:/Windows/wsl.exe", "--cd", str(tmp_path)], {}
    )


async def test_abre_un_archivo_con_su_aplicacion_predeterminada(make, recorder, tmp_path):
    await make().open_with_default(tmp_path / "informe.pdf")
    assert recorder.started == [str(tmp_path / "informe.pdf")]


def test_descubre_los_accesos_directos_del_menu_inicio(make, tmp_path):
    user = tmp_path / "roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    shared = tmp_path / "shared" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    for path in (user / "Zeta.lnk", user / "Grupo" / "Bloc de notas.lnk", user / "leeme.txt",
                 shared / "Calculadora.lnk", shared / "zeta.lnk"):  # fmt: skip
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    adapter = make({"APPDATA": str(tmp_path / "roaming"), "PROGRAMDATA": str(tmp_path / "shared")})
    apps = adapter.discover_apps()
    assert [app.name for app in apps] == ["Bloc de notas", "Calculadora", "Zeta"]
    assert apps[2].path == str(user / "Zeta.lnk")  # a igual nombre, el del usuario


def test_descubrir_sin_menu_inicio_no_falla(make):
    assert make({"APPDATA": "Z:/no/existe"}).discover_apps() == []


# --- Ventanas externas -----------------------------------------------------------------------


async def test_localiza_la_ventana_del_proceso_lanzado(make, recorder):
    recorder.windows = [(1, 10, "Vieja"), (2, 77, "Sin título"), (3, 99, "Editor - notas")]
    handle = LaunchHandle(77, "Editor", frozenset({1}))
    assert await make().wait_for_window(handle) == WindowRef(2, "Sin título")


async def test_si_no_es_la_del_proceso_vale_la_nueva_cuyo_titulo_contiene_el_nombre(make, recorder):
    recorder.windows = [(1, 10, "Docs antiguos"), (2, 20, "Otra cosa"), (3, 30, "DOCS")]
    handle = LaunchHandle(None, "Docs", frozenset({1}))
    assert await make().wait_for_window(handle) == WindowRef(3, "DOCS")


async def test_sondea_cada_250_ms_hasta_el_tiempo_maximo(make, recorder):
    recorder.windows = [(1, 10, "Vieja")]
    handle = LaunchHandle(77, "Editor", frozenset({1}))
    assert await make().wait_for_window(handle, timeout=10) is None
    assert recorder.slept == 10.0


class FocusUser32:
    def __init__(self, *, exists=True, minimized=False, granted=True) -> None:
        self.exists, self.minimized, self.granted = exists, minimized, granted
        self.calls: list[str] = []

    def IsWindow(self, hwnd):
        return self.exists

    def IsIconic(self, hwnd):
        return self.minimized

    def ShowWindow(self, hwnd, command):
        self.calls.append(f"ShowWindow:{command}")

    def SetForegroundWindow(self, hwnd):
        self.calls.append("SetForegroundWindow")
        return self.granted

    def FlashWindowEx(self, info):
        self.calls.append("FlashWindowEx")


def test_trae_una_ventana_al_frente_restaurandola_si_esta_minimizada(make):
    user32 = FocusUser32(minimized=True)
    adapter = make(user32=user32)
    assert adapter.focus_window(WindowRef(5, "Editor"))
    assert user32.calls == ["ShowWindow:9", "SetForegroundWindow"]
    assert adapter.window_exists(WindowRef(5, "Editor"))
    assert adapter.can_focus_windows


def test_si_windows_no_concede_el_foco_la_ventana_parpadea(make):
    user32 = FocusUser32(granted=False)
    assert not make(user32=user32).focus_window(WindowRef(5, "Editor"))
    assert user32.calls == ["SetForegroundWindow", "FlashWindowEx"]


def test_una_ventana_cerrada_no_se_trae_al_frente(make):
    user32 = FocusUser32(exists=False)
    adapter = make(user32=user32)
    assert not adapter.window_exists(WindowRef(5, "Editor"))
    assert not adapter.focus_window(WindowRef(5, "Editor"))
    assert user32.calls == []


@only_windows
def test_enumera_las_ventanas_reales():
    adapter = WindowsAdapter()
    listed = adapter._windows()
    assert all(isinstance(hwnd, int) and title for hwnd, _pid, title in listed)
    assert not adapter.window_exists(WindowRef(0, "ninguna"))


# --- Búsqueda indexada -----------------------------------------------------------------------


async def test_sin_everything_la_busqueda_indexada_no_esta_disponible(make, recorder):
    assert await make().indexed_search("informe", SearchKind.ANY, 50) is None
    assert recorder.searches == []


@pytest.mark.parametrize(
    ("kind", "filters"),
    [(SearchKind.ANY, []), (SearchKind.FILE, ["/a-d"]), (SearchKind.FOLDER, ["/ad"])],
)
async def test_busca_con_es_exe_con_filtro_y_limite(make, recorder, kind, filters):
    recorder.tools["es.exe"] = "C:/apps/es.exe"
    recorder.search_result.stdout = "C:\\Docs\\informe.txt\r\nC:\\Docs\\Año\\informes\r\n".encode()
    outcome = await make().indexed_search("informe", kind, 50)
    assert recorder.searches == [["C:/apps/es.exe", "-n", "50", *filters, "informe"]]
    assert outcome.paths == (Path("C:\\Docs\\informe.txt"), Path("C:\\Docs\\Año\\informes"))
    assert outcome.total == 2


async def test_es_exe_en_su_carpeta_de_instalacion(make, tmp_path):
    tool = tmp_path / "pf" / "Everything" / "es.exe"
    tool.parent.mkdir(parents=True)
    tool.write_text("")
    assert make({"ProgramFiles": str(tmp_path / "pf")}).search_tool() == str(tool)


async def test_si_everything_no_responde_no_hay_busqueda_indexada(make, recorder):
    recorder.tools["es.exe"] = "es.exe"
    recorder.search_result.returncode = 8  # la ventana de Everything no existe
    assert await make().indexed_search("informe", SearchKind.ANY, 50) is None

    def broken(_command):
        raise OSError("no se puede ejecutar")

    assert await make(run_search=broken).indexed_search("informe", SearchKind.ANY, 50) is None
