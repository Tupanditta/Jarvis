"""Reloj falso: el tiempo solo avanza cuando la prueba llama a `advance`."""
import asyncio
import heapq
import itertools
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

DEFAULT_START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FakeTimer:
    """Temporizador de `FakeClock`."""

    def __init__(self, due: float) -> None:
        self.due = due
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class FakeClock:
    """Doble de `Clock` con temporizadores controlables.

    `advance` dispara, en orden de vencimiento y de creación, los temporizadores que vencen
    en el intervalo. Durante cada disparo el reloj marca el instante de vencimiento.
    """

    def __init__(self, start: datetime = DEFAULT_START) -> None:
        if start.tzinfo is None:
            raise ValueError("El reloj necesita una fecha con zona horaria")
        self._start = start.astimezone(UTC)
        self._elapsed = 0.0
        self._queue: list[tuple[float, int, FakeTimer, Callable[[], None]]] = []
        self._order = itertools.count()

    def now(self) -> datetime:
        return self._start + timedelta(seconds=self._elapsed)

    def monotonic(self) -> float:
        return 1000.0 + self._elapsed

    def call_later(self, delay: float, callback: Callable[[], None]) -> FakeTimer:
        if delay < 0:
            raise ValueError("El retardo no puede ser negativo")
        timer = FakeTimer(self._elapsed + delay)
        heapq.heappush(self._queue, (timer.due, next(self._order), timer, callback))
        return timer

    async def sleep(self, seconds: float) -> None:
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        timer = self.call_later(
            seconds, lambda: None if future.done() else future.set_result(None)
        )
        try:
            await future
        finally:
            timer.cancel()

    def advance(self, seconds: float) -> None:
        """Avanza `seconds` segundos y dispara los temporizadores que venzan."""
        if seconds < 0:
            raise ValueError("El reloj no retrocede")
        target = self._elapsed + seconds
        # Tolerancia para que la suma de avances parciales alcance el vencimiento exacto.
        while self._queue and self._queue[0][0] <= target + 1e-9:
            due, _, timer, callback = heapq.heappop(self._queue)
            if timer.cancelled:
                continue
            self._elapsed = max(self._elapsed, due)
            callback()
        self._elapsed = max(self._elapsed, target)

    @property
    def pending(self) -> list[float]:
        """Segundos que faltan para cada temporizador vivo, ordenados."""
        return sorted(
            round(due - self._elapsed, 9) for due, _, timer, _ in self._queue if not timer.cancelled
        )
