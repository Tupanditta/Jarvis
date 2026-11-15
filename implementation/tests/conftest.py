"""Configuración global de las pruebas: Qt sin pantalla y red bloqueada (RNF-01)."""
import os

# Debe fijarse antes de que cualquier módulo importe Qt.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import socket

import pytest

pytest_plugins = ["pytester"]

_LOOPBACK_HOSTS = {"localhost", "::1", ""}


class NetworkBlockedError(RuntimeError):
    """Una prueba intentó usar la red."""


def _is_loopback(host: object) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    return isinstance(host, str) and (host in _LOOPBACK_HOSTS or host.startswith("127."))


def _host_of(address: object) -> object:
    return address[0] if isinstance(address, tuple) and address else address


class NetworkGuard:
    """Registra los intentos de red de la prueba en curso."""

    error = NetworkBlockedError

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def block(self, operation: str, target: object) -> None:
        self.attempts.append(f"{operation} {target!r}")
        raise NetworkBlockedError(f"Red bloqueada en las pruebas: {operation} {target!r}")


@pytest.fixture(autouse=True)
def network_guard(monkeypatch):
    """Bloquea toda conexión que no sea al propio equipo y hace fallar la prueba que lo intente.

    El bucle local se permite porque `asyncio` lo necesita en Windows. La prueba falla aunque
    el código capture la excepción: los intentos se comprueban al terminar.
    """
    guard = NetworkGuard()
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_sendto = socket.socket.sendto
    real_getaddrinfo = socket.getaddrinfo
    real_create_connection = socket.create_connection

    def connect(self, address):
        if not _is_loopback(_host_of(address)):
            guard.block("connect", address)
        return real_connect(self, address)

    def connect_ex(self, address):
        if not _is_loopback(_host_of(address)):
            guard.block("connect_ex", address)
        return real_connect_ex(self, address)

    def sendto(self, data, *args):
        if not _is_loopback(_host_of(args[-1])):
            guard.block("sendto", args[-1])
        return real_sendto(self, data, *args)

    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host):
            guard.block("getaddrinfo", host)
        return real_getaddrinfo(host, *args, **kwargs)

    def create_connection(address, *args, **kwargs):
        if not _is_loopback(_host_of(address)):
            guard.block("create_connection", address)
        return real_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", sendto)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    yield guard
    if guard.attempts:
        pytest.fail("La prueba intentó usar la red: " + "; ".join(guard.attempts), pytrace=False)


@pytest.fixture(autouse=True)
def _frases_desde_la_primera_variante():
    """Cada prueba empieza con todas las frases en su primera variante."""
    from jarvis_assistant.speaker.phrases import reset_rotation

    reset_rotation()
    yield
    reset_rotation()
