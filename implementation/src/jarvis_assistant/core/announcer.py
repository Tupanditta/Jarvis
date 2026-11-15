"""Cola de voz: las respuestas se dicen de una en una, en el orden en que terminan sus tareas.

Cada tarea entrega su respuesta completa (`Announcement`) al terminar. Las frases de una
misma respuesta se dicen seguidas: nunca se intercalan con las de otra tarea ni se solapan.
Un único consumidor recorre la cola; mientras no hay nada que decir, no existe.
"""
import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from jarvis_assistant.core.action_api import Phrase

logger = logging.getLogger(__name__)

# Dice una frase y devuelve True si se ha cortado antes de terminar.
Say = Callable[[Phrase], Awaitable[bool]]


@dataclass(frozen=True)
class Announcement:
    """Lo que el asistente dice de una vez: la respuesta de una tarea o un aviso."""

    phrases: tuple[Phrase, ...]
    on_start: Callable[[], None] | None = None  # justo antes de la primera frase
    on_delivered: Callable[[], None] | None = None  # al terminar, también si se ha cortado


class Announcer:
    def __init__(
        self,
        say: Say,
        stop: Callable[[], None],
        on_idle: Callable[[], None] = lambda: None,
    ) -> None:
        self._say = say
        self._stop = stop
        self._on_idle = on_idle
        self._pending: deque[Announcement] = deque()
        self._worker: asyncio.Task | None = None

    @property
    def active(self) -> bool:
        """Hay una respuesta sonando o esperando su turno."""
        return self._worker is not None or bool(self._pending)

    def __len__(self) -> int:
        return len(self._pending)

    def submit(self, announcement: Announcement) -> None:
        """Pone la respuesta al final de la cola."""
        self._pending.append(announcement)
        if self._worker is None:
            self._worker = asyncio.ensure_future(self._drain())

    def clear(self) -> bool:
        """Calla la respuesta en curso y descarta las que esperaban. True si había alguna."""
        was_active = self.active
        self._pending.clear()
        self._stop()
        return was_active

    async def _drain(self) -> None:
        try:
            while self._pending:
                await self._deliver(self._pending.popleft())
        finally:
            self._worker = None
            self._on_idle()

    async def _deliver(self, announcement: Announcement) -> None:
        try:
            if announcement.on_start is not None:
                announcement.on_start()
            for phrase in announcement.phrases:
                if await self._say(phrase):
                    break  # cortada: el resto de esta respuesta no se dice
            if announcement.on_delivered is not None:
                announcement.on_delivered()
        except asyncio.CancelledError:
            raise
        except Exception:  # una respuesta que falla no detiene las siguientes
            logger.exception("No se ha podido decir una respuesta")
