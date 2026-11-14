"""Garantiza una sola instancia del proceso por usuario con un mutex con nombre (RF-75).

La API de Windows va detras del puerto `MutexApi`, sustituible por un doble en las
pruebas. `RealMutexApi` usa ctypes y se importa de forma perezosa: este modulo se
puede importar en cualquier sistema operativo.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)

MUTEX_NAME: str = r"Local\jarvis_assistant-{7c3e9a52-4b1d-4f86-9a0e-5d2c8b61f3a7}"

ERROR_ALREADY_EXISTS: int = 183


class MutexApi(Protocol):
    """Subconjunto de kernel32 que necesita la exclusion de instancia."""

    def create_mutex(self, name: str) -> tuple[object, bool]:
        """Crea u abre el mutex `name`. Devuelve (handle nativo, ya_existia)."""
        ...

    def close_handle(self, handle: object) -> None:
        """Cierra el handle nativo."""
        ...


class RealMutexApi:
    """Implementacion real sobre ctypes. Solo se puede crear en Windows."""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32 = self._kernel32
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

    def create_mutex(self, name: str) -> tuple[object, bool]:
        self._ctypes.set_last_error(0)
        handle = self._kernel32.CreateMutexW(None, False, name)
        last_error = self._ctypes.get_last_error()
        if not handle:
            raise OSError(last_error, "CreateMutexW fallo")
        return handle, last_error == ERROR_ALREADY_EXISTS

    def close_handle(self, handle: object) -> None:
        self._kernel32.CloseHandle(handle)


class SingleInstanceHandle:
    """Posesion del mutex. Se libera solo con `close()`, nunca por recoleccion."""

    def __init__(self, native: object, api: MutexApi) -> None:
        self._native: object | None = native
        self._api = api

    def close(self) -> None:
        """Libera el mutex. Idempotente."""
        if self._native is None:
            return
        native, self._native = self._native, None
        self._api.close_handle(native)


def acquire_single_instance(
    name: str, api: MutexApi | None = None
) -> SingleInstanceHandle | None:
    """Adquiere el mutex `name`; None si ya hay otra instancia.

    Si `api` es None se usa `RealMutexApi` (solo Windows). Quien reciba el handle
    debe conservarlo y llamar a `close()` al terminar.
    """
    mutex_api = api if api is not None else RealMutexApi()
    native, already_existed = mutex_api.create_mutex(name)
    if already_existed:
        mutex_api.close_handle(native)
        logger.info("Ya hay otra instancia en ejecucion")
        return None
    return SingleInstanceHandle(native, mutex_api)
