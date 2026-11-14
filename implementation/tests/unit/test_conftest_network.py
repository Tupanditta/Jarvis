"""El conftest bloquea la red: una prueba que abre un socket falla (RNF-01, T-0.2)."""
import asyncio
import os
import socket
from pathlib import Path

import pytest

CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"


def test_conectar_a_una_direccion_externa_lanza(network_guard):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock, pytest.raises(
        network_guard.error
    ):
        sock.connect(("192.0.2.1", 80))
    assert network_guard.attempts == ["connect ('192.0.2.1', 80)"]
    network_guard.attempts.clear()


def test_create_connection_lanza(network_guard):
    with pytest.raises(network_guard.error):
        socket.create_connection(("example.com", 443))
    network_guard.attempts.clear()


def test_resolver_un_nombre_lanza(network_guard):
    with pytest.raises(network_guard.error):
        socket.getaddrinfo("example.com", 443)
    network_guard.attempts.clear()


def test_enviar_un_datagrama_externo_lanza(network_guard):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock, pytest.raises(
        network_guard.error
    ):
        sock.sendto(b"x", ("192.0.2.1", 53))
    network_guard.attempts.clear()


def test_el_bucle_local_sigue_disponible(network_guard):
    # asyncio en Windows crea un par de sockets sobre 127.0.0.1.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect(server.getsockname())
    assert network_guard.attempts == []


async def test_asyncio_funciona_con_la_red_bloqueada():
    await asyncio.sleep(0)


def test_una_prueba_que_abre_un_socket_falla_aunque_capture_el_error(pytester):
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makepyfile(
        """
        import socket

        def test_traga_el_error():
            try:
                socket.create_connection(("example.com", 80))
            except Exception:
                pass

        def test_sin_red():
            assert True
        """
    )
    result = pytester.runpytest_inprocess(
        "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"
    )
    result.assert_outcomes(passed=2, errors=1)
    result.stdout.fnmatch_lines(["*intentó usar la red*"])


def test_qt_se_ejecuta_sin_pantalla():
    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"


@pytest.mark.parametrize("marker", ["models", "hardware"])
def test_los_marcadores_estan_registrados(pytestconfig, marker):
    assert any(line.startswith(f"{marker}:") for line in pytestconfig.getini("markers"))


def test_por_defecto_se_excluyen_modelos_y_hardware(pytestconfig):
    assert pytestconfig.getoption("-m") == "not models and not hardware"
