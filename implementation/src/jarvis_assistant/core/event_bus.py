"""Bus de eventos: publicación/suscripción por tipo (RES-24, RNF-20).

Los manejadores se ejecutan siempre en el hilo del núcleo, en orden de suscripción.
`publish` se llama desde ese hilo; `publish_threadsafe`, desde cualquier otro.
"""
import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

from jarvis_assistant.core.events import Event

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Event)
Unsubscribe = Callable[[], None]


class EventBus:
    """Bus síncrono y sin memoria. Enruta por la clase exacta del evento."""

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Callable[[Event], None]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Fija el bucle del núcleo, al que `publish_threadsafe` entrega los eventos."""
        self._loop = loop

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> Unsubscribe:
        """Suscribe `handler` a `event_type`. Devuelve la función que anula la suscripción."""
        entry = handler  # una entrada por suscripción, aunque el manejador se repita
        self._handlers.setdefault(event_type, []).append(entry)  # type: ignore[arg-type]

        def unsubscribe() -> None:
            handlers = self._handlers.get(event_type, [])
            for index, candidate in enumerate(handlers):
                if candidate is entry:
                    # Lista nueva: una entrega en curso sigue con la que tenía.
                    self._handlers[event_type] = handlers[:index] + handlers[index + 1 :]
                    return

        return unsubscribe

    def publish(self, event: Event) -> None:
        """Entrega `event` a sus suscriptores. Un manejador que falla se registra y se salta."""
        if not isinstance(event, Event):
            raise TypeError(f"Solo se publican eventos: {event!r}")
        for handler in tuple(self._handlers.get(type(event), ())):
            try:
                handler(event)
            except Exception:
                logger.exception("Un manejador de %s ha fallado", type(event).__name__)

    def publish_threadsafe(self, event: Event) -> None:
        """Publica desde cualquier hilo; la entrega ocurre en el hilo del núcleo."""
        if self._loop is None:
            raise RuntimeError("El bus no tiene bucle: falta llamar a bind_loop")
        try:
            self._loop.call_soon_threadsafe(self.publish, event)
        except RuntimeError:
            # El bucle ya está cerrado: el proceso está saliendo.
            logger.debug("%s descartado: el núcleo ya no está en marcha", type(event).__name__)
