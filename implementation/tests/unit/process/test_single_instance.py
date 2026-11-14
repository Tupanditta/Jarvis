"""Pruebas de single_instance (T-37, D-16, RF-75; design.md 2.2 y 9.1).

Contrato fijado por estas pruebas, a implementar en
``jarvis_assistant/process/single_instance.py``:

- ``MUTEX_NAME: str``: ``Local\\jarvis_assistant-{GUID}`` con GUID fijo.
- Puerto sustituible ``MutexApi`` (Protocol) con dos metodos:
  ``create_mutex(name: str) -> tuple[object, bool]`` devuelve
  ``(handle_nativo, ya_existia)`` y ``close_handle(handle_nativo) -> None``.
  La implementacion real envuelve ``CreateMutexW`` / ``GetLastError`` /
  ``CloseHandle``.
- ``acquire_single_instance(name: str, api: MutexApi | None = None)
  -> SingleInstanceHandle | None``: ``api`` se inyecta como argumento
  opcional; con ``None`` usa la API real de Windows. Devuelve ``None`` si el
  mutex ya existe (y cierra el handle nativo obtenido).
- ``SingleInstanceHandle.close()``: libera el mutex; es idempotente.
  Nunca se cierra por recoleccion ni por perder la referencia.
"""

import gc
import re

NOMBRE = r"Local\jarvis_assistant-test"


class FakeMutexApi:
    """Doble de la API de mutex de Windows con nombres compartidos."""

    def __init__(self):
        self.vivos = set()
        self.creados = []
        self.cerrados = []
        self._propietarios = {}

    def create_mutex(self, name):
        self.creados.append(name)
        ya_existia = name in self.vivos
        native = (name, len(self.creados))
        if not ya_existia:
            self.vivos.add(name)
            self._propietarios[name] = native
        return native, ya_existia

    def close_handle(self, native):
        self.cerrados.append(native)
        nombre = native[0]
        # Solo cerrar el handle propietario elimina el mutex con nombre.
        if self._propietarios.get(nombre) == native:
            self.vivos.discard(nombre)
            del self._propietarios[nombre]


def _acquire(api, name=NOMBRE):
    from jarvis_assistant.process.single_instance import acquire_single_instance

    return acquire_single_instance(name, api)


def test_d16_nombre_del_mutex_en_local_con_guid_fijo():
    from jarvis_assistant.process.single_instance import MUTEX_NAME

    patron = (
        r"^Local\\jarvis_assistant-\{[0-9A-Fa-f]{8}(-[0-9A-Fa-f]{4}){3}"
        r"-[0-9A-Fa-f]{12}\}$"
    )
    assert re.match(patron, MUTEX_NAME)


def test_d16_primera_adquisicion_devuelve_handle():
    api = FakeMutexApi()

    handle = _acquire(api)

    assert handle is not None


def test_d16_segunda_adquisicion_devuelve_none():
    api = FakeMutexApi()
    primero = _acquire(api)

    segundo = _acquire(api)

    assert primero is not None
    assert segundo is None


def test_d16_segunda_adquisicion_cierra_su_propio_handle_nativo_y_no_el_del_propietario():
    api = FakeMutexApi()
    _acquire(api)

    _acquire(api)

    assert api.cerrados == [(NOMBRE, 2)]


def test_d16_adquisicion_usa_el_nombre_recibido():
    api = FakeMutexApi()

    _acquire(api, r"Local\otro-nombre")

    assert api.creados == [r"Local\otro-nombre"]


def test_d16_tras_liberar_el_primero_una_nueva_adquisicion_tiene_exito():
    api = FakeMutexApi()
    primero = _acquire(api)
    primero.close()

    nuevo = _acquire(api)

    assert nuevo is not None


def test_d16_el_handle_no_se_cierra_mientras_se_conserve():
    api = FakeMutexApi()

    handle = _acquire(api)
    gc.collect()

    assert handle is not None
    assert api.cerrados == []


def test_d16_perder_la_referencia_no_libera_el_mutex():
    api = FakeMutexApi()
    _acquire(api)
    gc.collect()

    segundo = _acquire(api)

    assert segundo is None


def test_d16_close_es_idempotente():
    api = FakeMutexApi()
    handle = _acquire(api)

    handle.close()
    handle.close()

    assert len(api.cerrados) == 1


def test_una_segunda_instancia_real_se_detecta():
    """Con el mutex real de Windows: la segunda adquisicion falla hasta liberar la primera."""
    import sys
    import uuid

    import pytest

    from jarvis_assistant.process.single_instance import acquire_single_instance

    if sys.platform != "win32":
        pytest.skip("mutex con nombre: solo Windows")
    name = rf"Local\jarvis_assistant-test-{uuid.uuid4()}"
    first = acquire_single_instance(name)
    assert first is not None
    try:
        assert acquire_single_instance(name) is None
    finally:
        first.close()
    third = acquire_single_instance(name)
    assert third is not None
    third.close()
