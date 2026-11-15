"""Cola de órdenes y planificador de tareas.

Las órdenes entran en la cola en el orden en que se escriben y salen cuando pueden
ejecutarse. Cada una declara lo que ocupa (`Claim`): el módulo que la atiende y los recursos
compartidos que lee y que cambia. Una orden empieza cuando ninguna anterior sin terminar
choca con ella:

- las de un mismo módulo se ejecutan de una en una, en su orden;
- las de módulos distintos se ejecutan a la vez, salvo que una cambie un recurso que la otra
  usa (el directorio de trabajo, por ejemplo): entonces la posterior espera.

Es código puro: no ejecuta nada ni conoce `asyncio`. El orquestador pide las órdenes que
pueden empezar, las ejecuta y avisa cuando terminan.
"""
import itertools
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Claim:
    """Lo que una orden ocupa mientras no termina."""

    lanes: frozenset[str] = frozenset()  # módulos que pueden atenderla
    reads: frozenset[str] = frozenset()
    writes: frozenset[str] = frozenset()

    def blocks(self, later: "Claim") -> bool:
        """True si una orden posterior con `later` debe esperar a esta."""
        return bool(
            self.lanes & later.lanes
            or self.writes & (later.reads | later.writes)
            or self.reads & later.writes
        )

    def covers(self, other: "Claim") -> bool:
        return (
            other.lanes <= self.lanes and other.reads <= self.reads and other.writes <= self.writes
        )


@dataclass(eq=False)
class Job(Generic[T]):
    """Orden en la cola. `payload` es del orquestador: la cola no lo interpreta."""

    id: int
    claim: Claim
    payload: T
    running: bool = False


class TaskQueue(Generic[T]):
    def __init__(self) -> None:
        self._jobs: list[Job[T]] = []  # sin terminar, en orden de llegada
        self._ids = itertools.count(1)

    def __len__(self) -> int:
        return len(self._jobs)

    @property
    def waiting(self) -> list[Job[T]]:
        return [job for job in self._jobs if not job.running]

    @property
    def running(self) -> list[Job[T]]:
        return [job for job in self._jobs if job.running]

    def add(self, claim: Claim, payload: T) -> Job[T]:
        job = Job(next(self._ids), claim, payload)
        self._jobs.append(job)
        return job

    def take_ready(self) -> list[Job[T]]:
        """Las órdenes en espera que ya pueden empezar, en su orden. Quedan en ejecución."""
        ready: list[Job[T]] = []
        for position, job in enumerate(self._jobs):
            if job.running:
                continue
            if any(earlier.claim.blocks(job.claim) for earlier in self._jobs[:position]):
                continue
            job.running = True
            ready.append(job)
        return ready

    def narrow(self, job: Job[T], claim: Claim) -> None:
        """Reduce lo que ocupa una orden cuando ya se sabe qué acción es. Solo se puede
        reducir: ampliarlo podría chocar con órdenes que ya están en ejecución."""
        if not job.claim.covers(claim):
            raise ValueError("Una orden no puede ocupar más de lo que declaró al entrar")
        job.claim = claim

    def finish(self, job: Job[T]) -> None:
        """La orden ha terminado. No hace nada si ya no está en la cola."""
        if job in self._jobs:
            self._jobs.remove(job)

    def clear(self) -> list[Job[T]]:
        """Vacía la cola y devuelve las órdenes que quedaban, en espera o en ejecución."""
        jobs, self._jobs = self._jobs, []
        return jobs
