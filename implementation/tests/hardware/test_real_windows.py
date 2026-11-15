r"""Escritorio real de Windows (marcador `hardware`; a demanda). Abre y cierra ventanas.

    .\.venv\Scripts\python.exe -m pytest -m hardware tests\hardware
"""
import subprocess
import sys
import time

import pytest

from jarvis_assistant.os_adapters.base import AppTarget, SearchKind
from jarvis_assistant.os_adapters.windows import WindowsAdapter

pytestmark = [
    pytest.mark.hardware,
    pytest.mark.skipif(sys.platform != "win32", reason="solo en Windows"),
]


async def test_abre_el_bloc_de_notas_localiza_su_ventana_y_la_trae_al_frente():
    """Criterio de aceptación de Plataforma."""
    import psutil

    if any(p.info["name"] == "notepad.exe" for p in psutil.process_iter(["name"])):
        pytest.skip("Hay un Bloc de notas abierto: la prueba lo cerraría")
    adapter = WindowsAdapter()
    handle = await adapter.launch_app(AppTarget("Bloc de notas", "notepad.exe"))
    window = None
    try:
        # El Bloc de notas de Windows 11 delega en otro proceso: vale el título.
        window = await adapter.wait_for_window(handle, timeout=10) or await adapter.wait_for_window(
            type(handle)(None, "notas", handle.known_windows), timeout=5
        )
        assert window is not None
        assert adapter.window_exists(window)
        adapter.focus_window(window)  # puede parpadear si Windows no concede el foco
    finally:
        subprocess.run(["taskkill", "/IM", "notepad.exe", "/F"], capture_output=True, check=False)
    time.sleep(1)
    assert not adapter.window_exists(window)


async def test_busqueda_real_con_everything_en_menos_de_dos_segundos():
    """RNF-09. Se salta si *Everything* no está instalado."""
    adapter = WindowsAdapter()
    if adapter.search_tool() is None:
        pytest.skip("Everything (es.exe) no está instalado")
    started = time.monotonic()
    outcome = await adapter.indexed_search("notepad", SearchKind.FILE, 50)
    assert outcome is not None, "Everything no responde: ¿está en marcha?"
    assert time.monotonic() - started <= 2
    assert all(path.is_absolute() for path in outcome.paths)
