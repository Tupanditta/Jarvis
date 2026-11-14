"""Reloj inyectable (RES-47).

El núcleo no consulta la hora ni programa temporizadores por su cuenta: recibe un `Clock`.
Las pruebas usan `tests/fakes/clock.py`, que solo avanza cuando la prueba lo pide.
"""
import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class TimerHandle(Protocol):
    """Temporizador programado con `Clock.call_later`."""

    def cancel(self) -> None:
        """Anula el temporizador. Idempotente."""
        ...


@runtime_checkable
class Clock(Protocol):
    """Fuente única de tiempo del núcleo."""

    def now(self) -> datetime:
        """Fecha y hora actuales, en UTC y con zona horaria (RES-35)."""
        ...

    def monotonic(self) -> float:
        """Segundos desde un origen arbitrario; nunca retrocede. Para medir duraciones."""
        ...

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:
        """Ejecuta `callback` en el hilo del núcleo cuando pasen `delay` segundos."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Suspende la corrutina durante `seconds` segundos."""
        ...


class SystemClock:
    """Reloj real. `call_later` y `sleep` usan el bucle `asyncio` en ejecución."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:
        return asyncio.get_running_loop().call_later(delay, callback)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
