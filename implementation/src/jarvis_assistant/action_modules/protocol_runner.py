"""Módulo Protocolos (protocolos.md; CU-13).

Ejecuta con una sola orden una secuencia de tareas de varios módulos, definida en
`protocols.toml` (RN-33, RES-36). Cada tarea se ejecuta con `ctx.invoke`: la misma interfaz y
el mismo `run_task` que una orden del usuario, como subtarea de la del protocolo. Sus
parámetros se resuelven al llegarle el turno, no al cargar: una ruta relativa usa el directorio
de trabajo que dejó la tarea anterior. Un protocolo con tareas de Comandos trabaja en su propia
consola (`ctx.open_console`): la reutiliza si ya la tenía abierta de otra vez. Si cambia de
carpeta (`comandos.cd`) después de haber trabajado en la anterior, abre otra ventana de
Comandos para la carpeta nueva (`_windows`): un protocolo que prepara dos asignaturas deja una
ventana en cada una.

El orquestador valida los protocolos contra el registro de intenciones al aplicar la
configuración (`config.validate_protocols`): aquí solo llegan los válidos.
"""
import asyncio
import logging
from collections.abc import Callable, Mapping, Sequence

from jarvis_assistant.config import ProtocolDef, ProtocolTask
from jarvis_assistant.core.action_api import (
    CANCELLED_REASON,
    ActionContext,
    ActionResult,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import ProtocolRow
from jarvis_assistant.core.events import ProtocolFinished, ProtocolsListed, ProtocolStarted
from jarvis_assistant.speaker.phrases import count

logger = logging.getLogger(__name__)

PANEL = "protocolo"
COMMANDS = "comandos"  # el módulo cuyas tareas piden una consola propia
CATALOG = "protocolos"
STOPPED_REASON = "protocolo detenido"  # RN-34


class ProtocolRunner:
    name = "protocolos"
    title = "Protocolos"

    def __init__(self) -> None:
        self._protocols: tuple[ProtocolDef, ...] = ()

    def intents(self) -> Sequence[IntentSpec]:
        # Solo con una orden del usuario: un protocolo no invoca a otro protocolo.
        return (
            IntentSpec(
                "ejecutar", ("protocolo {protocolo}", "ejecuta el protocolo {protocolo}",
                             "inicia el protocolo {protocolo}",
                             "activa el protocolo {protocolo}"),
                (Slot("protocolo", SlotType.CATALOG, catalog=CATALOG),),
                "Ejecutar un protocolo", "Protocolo modo trabajo", PANEL,
                in_protocols=False, exclusive=True,  # ocupa el turno (RN-55)
            ),
            IntentSpec(
                "listar", ("muestra los protocolos", "qué protocolos hay"), (),
                "Mostrar los protocolos", "Qué protocolos hay", PANEL, in_protocols=False,
                record=False,
            ),
        )  # fmt: skip

    def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]:
        return {CATALOG: (self._spellings,)}

    def _spellings(self) -> list[str]:
        return [spoken for protocol in self._protocols for spoken in _names(protocol)]

    async def on_session_opened(self, ctx: ActionContext) -> None:
        self._protocols = ctx.config.protocols  # la configuración vigente (RF-96)

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        self._protocols = ctx.config.protocols
        match action:
            case "ejecutar":
                wanted = str(params["protocolo"])
                protocol = self._find(wanted)
                if protocol is None:
                    return ActionResult(
                        "error", Phrase("entidad.no_encontrado", {"nombre": wanted})
                    )
                return await self._run(protocol, ctx)
            case "listar":
                return self._list(ctx)
        raise ValueError(f"Acción desconocida: {action}")

    def _find(self, spoken: str) -> ProtocolDef | None:
        """El protocolo con ese nombre o alias (el catálogo devuelve uno de ellos)."""
        wanted = spoken.casefold()
        for protocol in self._protocols:
            if wanted in (name.casefold() for name in _names(protocol)):
                return protocol
        return None

    # --- Ejecutar ------------------------------------------------------------------------------

    async def _run(self, protocol: ProtocolDef, ctx: ActionContext) -> ActionResult:
        """RF-52 a RF-57: panel con las tareas en `pendiente`, propuesta de nombre,
        importancia y las tareas en orden. Las respuestas de cada tarea no se dicen, salvo los
        errores y las preguntas; al final, el resumen."""
        name = protocol.name
        windows = _windows(protocol)
        if windows[0] is not None:
            # Su propia ventana de Comandos: dos protocolos no comparten carpeta ni salida.
            ctx.open_console(*windows[0], False)
        steps = [_describe(task) for task in protocol.tasks]
        subtasks = [
            ctx.subtask(task.module, step)
            for task, step in zip(protocol.tasks, steps, strict=True)
        ]
        assert ctx.task_id is not None
        ctx.publish(
            ProtocolStarted(ctx.task_id, name, tuple(steps), tuple(s.id for s in subtasks))
        )
        await ctx.say(Phrase("protocolos.inicio", {"nombre": name}))
        logger.info("Protocolo %s: %d tareas", protocol.id, len(subtasks))
        completed = failed = 0
        try:
            # Un no o el tiempo agotado no detienen el protocolo (RN-04); «cancelar», sí: no
            # se ejecuta ninguna tarea.
            proposal = await ctx.invoke(
                "sesion", "proponer_nombre", {"nombre": name},
                description=f"proponer el nombre {name}",
            )  # fmt: skip
            if proposal.detail == CANCELLED_REASON:
                for subtask in subtasks:
                    subtask.fail(CANCELLED_REASON)
                logger.info("Protocolo %s cancelado antes de empezar", protocol.id)
                ctx.publish(ProtocolFinished(ctx.task_id, 0, len(subtasks)))
                return ActionResult.cancelled(description=f"protocolo {name}")
            if protocol.important:  # RN-36; nunca degrada (RN-06)
                await ctx.invoke(
                    "sesion", "importante_por_protocolo", {}, quiet=False,
                    description="marcar la sesión como importante",
                )  # fmt: skip
            for position, (task, subtask) in enumerate(zip(protocol.tasks, subtasks, strict=True)):
                # Lo que dejó en marcha la tarea anterior (localizar la ventana de lo que se
                # ha abierto, por ejemplo) avanza antes de la siguiente, como entre dos órdenes.
                await asyncio.sleep(0)
                if position and windows[position] is not None:
                    # Otra carpeta de trabajo: otra ventana, que parte de la de la anterior
                    # (así una ruta relativa se resuelve como sin ventanas).
                    ctx.open_console(*windows[position], True)
                result = await ctx.invoke(
                    task.module, task.action, task.params, subtask=subtask, resolve=True
                )
                if result.status == "completado":
                    completed += 1
                    continue
                failed += 1
                if task.stop_on_error:  # RN-34
                    for rest in subtasks[position + 1:]:
                        rest.fail(STOPPED_REASON)
                        failed += 1
                    logger.info("Protocolo %s detenido en la tarea %d", protocol.id, position + 1)
                    break
        except asyncio.CancelledError:
            # «Cancelar» o el cierre de la sesión: la tarea en curso se cancela y el
            # orquestador deja las restantes en `error` (RN-46, RN-52).
            ctx.publish(ProtocolFinished(ctx.task_id, completed, len(subtasks) - completed))
            raise
        ctx.publish(ProtocolFinished(ctx.task_id, completed, failed))
        description = f"protocolo {name}"
        if failed:
            errors = count(failed, "error", "errores")
            speech = Phrase("protocolos.con_errores", {"nombre": name, "n": errors})
            return ActionResult("error", speech, description, detail=f"{errors}")
        return ActionResult("completado", Phrase("protocolos.completado", {"nombre": name}),
                            description)  # fmt: skip

    # --- Listar --------------------------------------------------------------------------------

    def _list(self, ctx: ActionContext) -> ActionResult:
        rows = tuple(
            ProtocolRow(p.id, p.name, p.aliases, p.important,
                        tuple(_describe(task) for task in p.tasks))
            for p in self._protocols
        )  # fmt: skip
        ctx.publish(ProtocolsListed(rows))
        description = "listar los protocolos"
        if not rows:
            return ActionResult("completado", Phrase("protocolos.ninguno"), description)
        n = count(len(rows), "protocolo", "protocolos")
        return ActionResult("completado", Phrase("protocolos.lista", {"n": n}), description)


def _windows(protocol: ProtocolDef) -> list[tuple[str, str] | None]:
    """Para cada tarea, la ventana de Comandos (clave y título) que se abre justo antes de
    ella, o None si sigue en la que hay.

    La primera se abre al empezar, si el protocolo tiene alguna tarea de Comandos. Después,
    un `cd` abre otra si en la ventana actual ya se ha hecho algo más que cambiar de carpeta;
    dos `cd` seguidos («proyectos», luego «jarvis») navegan en la misma. El título es la
    carpeta del primer `cd` de la ventana, o el nombre del protocolo si no empieza con uno.
    """
    windows: list[tuple[str, str] | None] = [None] * len(protocol.tasks)
    if not any(task.module == COMMANDS for task in protocol.tasks):
        return windows
    count, used = 1, False
    first = _destination(protocol.tasks[0]) if protocol.tasks else None
    windows[0] = (f"protocolo-{protocol.id}", f"Comandos · {first or protocol.name}")
    for position, task in enumerate(protocol.tasks):
        destination = _destination(task)
        if destination is None:
            used = True
            continue
        if used:
            count += 1
            windows[position] = (f"protocolo-{protocol.id}-{count}", f"Comandos · {destination}")
            used = False
    return windows


def _destination(task: ProtocolTask) -> str | None:
    """La carpeta, tal como se escribió, si la tarea es un `cd`."""
    if task.module != COMMANDS or task.action != "cd":
        return None
    return str(task.params.get("ruta", "")) or "carpeta"


def _names(protocol: ProtocolDef) -> tuple[str, ...]:
    return (protocol.name, *protocol.aliases)


def _describe(task: ProtocolTask) -> str:
    """La descripción de la tarea en `protocols.toml` o, si falta, su acción y sus
    parámetros tal como se escribieron: «cd proyectos barra jarvis»."""
    if task.description:
        return task.description
    values = " ".join(str(value) for value in task.params.values())
    return f"{task.action.replace('_', ' ')} {values}".strip()
