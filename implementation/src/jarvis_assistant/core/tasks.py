"""Registro de tareas: actividades de la sesión, `TaskUpdated`, subtareas y trabajo en
segundo plano (arquitectura.md, sección 4; AD-13).

Cada tarea se registra como actividad en `pendiente` y se publica; al terminar se fija su
estado en la base de datos y se publica otra vez. Lo usa solo el orquestador: `run_task`, la
única función que ejecuta acciones, se apoya en este registro. Los módulos no registran
actividades ni publican `TaskUpdated` de su tarea principal.
"""
import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import CANCELLED_REASON, ActionResult, Phrase, Subtask
from jarvis_assistant.core.clock import Clock
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.notices import Notice
from jarvis_assistant.core.repositories import ActivityRepository

logger = logging.getLogger(__name__)


@dataclass
class TaskRecord:
    """Tarea registrada: lo que hace falta para publicar su estado."""

    id: int
    parent: int | None
    module: str
    description: str
    reason: str = CANCELLED_REASON  # motivo si se cancela mientras sigue en segundo plano


class TaskRegistry:
    """`notify`: entrega un aviso (la frase de un trabajo en segundo plano que termina).
    `render`: texto de una frase, para el motivo de una tarea en `error`."""

    def __init__(
        self,
        *,
        bus: EventBus,
        clock: Clock,
        activities: ActivityRepository,
        notify: Callable[[Notice], None],
        render: Callable[[Phrase], str],
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._activities = activities
        self._notify = notify
        self._render = render
        self._unrun: dict[int, TaskRecord] = {}  # subtareas creadas que aún no se han ejecutado
        self._background: dict[asyncio.Task, TaskRecord] = {}

    # --- Tareas ---

    def new(self, session_id: int, module: str, description: str, parent: int | None) -> TaskRecord:
        """Registra una tarea en `pendiente` como actividad de la sesión y la publica."""
        task = TaskRecord(
            self._activities.add(session_id, module, description, self._clock.now(), parent),
            parent, module, description,
        )  # fmt: skip
        self.publish(task, "pendiente")
        return task

    def publish(self, task: TaskRecord, status: str, detail: str | None = None) -> None:
        self._bus.publish(
            events.TaskUpdated(
                task.id, task.parent, task.module, task.description,
                status,  # type: ignore[arg-type]
                detail, self._clock.now().astimezone(),
            )
        )

    def finish(self, task: TaskRecord, status: str, detail: str | None = None) -> None:
        self._activities.finish(task.id, status, task.description, self._clock.now())
        self.publish(task, status, detail)

    def detail(self, result: ActionResult) -> str | None:
        """Motivo que se muestra bajo una tarea en `error`: el del módulo o, si no, su frase."""
        if result.status != "error":
            return None
        if result.detail is not None:
            return result.detail
        if result.speech is None:
            return None
        try:
            return self._render(result.speech)
        except Exception:
            return None

    # --- Subtareas ---

    def subtask(
        self, session_id: int, parent: TaskRecord | None, module: str, description: str
    ) -> Subtask:
        """`ctx.subtask`: una tarea hija en `pendiente`, que se ejecuta después con `invoke`."""
        if parent is None:
            raise RuntimeError("Solo una tarea puede tener subtareas")
        task = self.new(session_id, module, description, parent.id)
        self._unrun[task.id] = task

        def fail(reason: str) -> None:
            if self._unrun.pop(task.id, None) is not None:
                self.finish(task, "error", reason)

        return Subtask(task.id, fail)

    def take_unrun(self, subtask_id: int) -> TaskRecord:
        """La subtarea creada con `subtask` que se va a ejecutar ahora."""
        task = self._unrun.pop(subtask_id, None)
        if task is None:
            raise RuntimeError(f"La subtarea {subtask_id} ya no está pendiente")
        return task

    def fail_unrun(self, parent: TaskRecord, reason: str) -> None:
        """Las subtareas de `parent` que no han llegado a ejecutarse quedan en `error`."""
        for task_id, task in list(self._unrun.items()):
            if task.parent == parent.id:
                del self._unrun[task_id]
                self.finish(task, "error", reason)

    # --- Segundo plano ---

    @property
    def has_background(self) -> bool:
        return bool(self._background)

    def spawn_background(self, task: TaskRecord, work: Coroutine[Any, Any, ActionResult]) -> None:
        job = asyncio.ensure_future(work)
        self._background[job] = task
        job.add_done_callback(self._background_done)

    async def cancel_background(self, reason: str) -> None:
        jobs = list(self._background)
        for job in jobs:
            self._background[job].reason = reason
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        for job in jobs:
            self._background_done(job)

    def _background_done(self, job: asyncio.Task) -> None:
        """El trabajo en segundo plano ha terminado: su resultado fija el estado de la tarea
        y su frase se entrega como aviso cuando el asistente quede libre (RN-39)."""
        task = self._background.pop(job, None)
        if task is None:
            return
        if job.cancelled():
            self.finish(task, "error", task.reason)
            return
        if job.exception() is not None:
            logger.error("La tarea en segundo plano ha fallado", exc_info=job.exception())
            result = ActionResult("error", Phrase("general.error"))
        else:
            result = job.result()
        if result.description:
            task.description = result.description
        self.finish(task, result.status, self.detail(result))
        if result.speech is not None:
            self._notify(Notice(result.speech))
