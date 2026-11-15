"""Cola de avisos (arquitectura.md, sección 7; RN-39).

Un aviso es un mensaje que el asistente inicia por su cuenta: el fin de un binario en segundo
plano, un recordatorio que vence. El orquestador los entrega de uno en uno, cuando no hay
turno en curso ni locución. Al cerrar la sesión la cola se vacía.
"""
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from jarvis_assistant.core.action_api import Phrase


@dataclass(frozen=True)
class Notice:
    phrase: Phrase
    panel: str | None = None  # panel que se activa al entregarlo
    on_delivered: Callable[[], None] | None = None
    reminder: bool = False  # en reposo, pone al asistente en escucha


class NoticeQueue:
    def __init__(self) -> None:
        self._items: deque[Notice] = deque()

    def __len__(self) -> int:
        return len(self._items)

    def add(self, notice: Notice) -> None:
        self._items.append(notice)

    def pop(self) -> Notice | None:
        return self._items.popleft() if self._items else None

    def has_reminder(self) -> bool:
        return any(notice.reminder for notice in self._items)

    def pop_reminder(self) -> Notice | None:
        for notice in self._items:
            if notice.reminder:
                self._items.remove(notice)
                return notice
        return None

    def clear(self) -> None:
        self._items.clear()
