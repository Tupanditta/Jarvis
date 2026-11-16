"""Planificador de trabajos a una fecha (recordatorio.md, «Programación»; RES-14).

Los trabajos tienen un identificador estable (`trigger:{id}`, `deadline:{id}`,
`autoconfirm:{id}`): añadir uno con un identificador que ya existe lo sustituye. El almacén es
la memoria: la base de datos es la única fuente de verdad y los trabajos se recalculan al abrir
cada sesión. Los trabajos se ejecutan en el hilo del núcleo.

- `ApsScheduler`: `APScheduler` (`AsyncIOScheduler`) en el bucle del núcleo. Es el del
  asistente real: sigue la hora del sistema aunque el equipo se suspenda.
- `ClockScheduler`: sobre `Clock.call_later`. Con el reloj falso, las pruebas controlan cuándo
  vence cada trabajo.
"""
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from jarvis_assistant.core.clock import Clock, TimerHandle

logger = logging.getLogger(__name__)

Job = Callable[[], None]


@runtime_checkable
class Scheduler(Protocol):
    def add(self, job_id: str, when: datetime, job: Job) -> None:
        """Programa `job` para `when` (con zona horaria). Una fecha pasada vence en seguida."""
        ...

    def remove(self, job_id: str) -> None:
        """Anula el trabajo, si existe."""
        ...

    def remove_all(self) -> None:
        ...

    def jobs(self) -> dict[str, datetime]:
        """Trabajos pendientes y su fecha."""
        ...


def _run(job_id: str, job: Job) -> None:
    try:
        job()
    except Exception:  # un trabajo que falla no detiene a los demás
        logger.exception("El trabajo %s ha fallado", job_id)


class ClockScheduler:
    """Planificador sobre el reloj inyectable."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._timers: dict[str, tuple[datetime, TimerHandle]] = {}

    def add(self, job_id: str, when: datetime, job: Job) -> None:
        self.remove(job_id)
        delay = max(0.0, (when - self._clock.now()).total_seconds())

        def fire() -> None:
            current = self._timers.get(job_id)
            if current is None or current[1] is not handle:
                return
            del self._timers[job_id]
            _run(job_id, job)

        handle = self._clock.call_later(delay, fire)
        self._timers[job_id] = (when, handle)

    def remove(self, job_id: str) -> None:
        entry = self._timers.pop(job_id, None)
        if entry is not None:
            entry[1].cancel()

    def remove_all(self) -> None:
        for job_id in list(self._timers):
            self.remove(job_id)

    def jobs(self) -> dict[str, datetime]:
        return {job_id: when for job_id, (when, _handle) in self._timers.items()}


class ApsScheduler:
    """`AsyncIOScheduler` de APScheduler. Arranca con el primer trabajo, ya en el bucle."""

    def __init__(self) -> None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self._scheduler = AsyncIOScheduler(timezone=UTC)
        self._started = False

    def add(self, job_id: str, when: datetime, job: Job) -> None:
        from apscheduler.triggers.date import DateTrigger

        if not self._started:
            self._scheduler.start()
            self._started = True

        async def run() -> None:  # una corrutina: se ejecuta en el bucle, no en un hilo
            _run(job_id, job)

        self._scheduler.add_job(
            run, DateTrigger(run_date=when.astimezone(UTC)), id=job_id,
            replace_existing=True, misfire_grace_time=None, coalesce=True,
        )  # fmt: skip

    def remove(self, job_id: str) -> None:
        if self._scheduler.get_job(job_id) is not None:
            self._scheduler.remove_job(job_id)

    def remove_all(self) -> None:
        self._scheduler.remove_all_jobs()

    def jobs(self) -> dict[str, datetime]:
        return {
            job.id: job.next_run_time for job in self._scheduler.get_jobs()
            if job.next_run_time is not None
        }  # fmt: skip

    def shutdown(self) -> None:
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
