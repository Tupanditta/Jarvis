"""`protocols.toml`: secuencias de tareas con nombre (protocolos.md).

Al cargar se comprueba su estructura. Su validación contra el registro de intenciones
(`validate_protocols`) la hace el orquestador, que conoce el registro, cada vez que aplica la
configuración.
"""
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from jarvis_assistant.config.reader import REQUIRED, ConfigError, InvalidError, Reader


@dataclass(frozen=True)
class ProtocolTask:
    module: str
    action: str
    params: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))
    stop_on_error: bool = False
    description: str | None = None


@dataclass(frozen=True)
class ProtocolDef:
    id: str
    name: str
    tasks: tuple[ProtocolTask, ...]
    aliases: tuple[str, ...] = ()
    important: bool = False


def _parse_protocol(item: Reader) -> ProtocolDef:
    protocol_id = item.text("id", non_empty=True)
    name = item.text("name", non_empty=True)
    aliases = item.texts("aliases")
    important = item.boolean("important", False)
    tasks = []
    for task in item.tables("tasks", REQUIRED) or []:
        params = dict(task.table("params").items())
        for key, value in params.items():
            if not isinstance(value, str | int | float | bool):
                raise InvalidError(
                    task.key(f"params.{key}"), "debe ser un texto, un número o un booleano"
                )
        tasks.append(
            ProtocolTask(
                module=task.text("module", non_empty=True),
                action=task.text("action", non_empty=True),
                params=MappingProxyType(params),
                stop_on_error=task.boolean("stop_on_error", False),
                description=task.text("description", None),
            )
        )
        task.close()
    if not tasks:
        raise InvalidError(item.key("tasks"), "el protocolo no tiene tareas")
    item.close()
    return ProtocolDef(
        id=protocol_id, name=name, tasks=tuple(tasks), aliases=aliases, important=important
    )


def parse_protocols(reader: Reader) -> tuple[ProtocolDef, ...]:
    """Un protocolo no válido se descarta con un error; los demás se cargan."""
    protocols = []
    ids: set[str] = set()
    names: set[str] = set()
    for item in reader.tables("protocols") or []:
        try:
            protocol = _parse_protocol(item)
            if protocol.id in ids:
                raise InvalidError(item.key("id"), f"el id «{protocol.id}» está repetido")
            for field_name, spoken in [("name", protocol.name)] + [
                ("aliases", alias) for alias in protocol.aliases
            ]:
                if spoken.casefold() in names:
                    raise InvalidError(item.key(field_name), f"el nombre «{spoken}» está repetido")
        except InvalidError as invalid:
            reader.error(invalid.key, invalid.reason)
            continue
        ids.add(protocol.id)
        names.update(spoken.casefold() for spoken in (protocol.name, *protocol.aliases))
        protocols.append(protocol)
    return tuple(protocols)


def validate_protocols(
    protocols: Sequence[ProtocolDef], specs_of: Callable[[str, str], Sequence[Any]]
) -> tuple[tuple[ProtocolDef, ...], list[ConfigError]]:
    """Valida cada tarea contra el registro de intenciones (`specs_of(module, action)`, las
    `IntentSpec` registradas de la acción): la acción existe, admite protocolos y tiene sus
    parámetros obligatorios. Un protocolo no válido se descarta con un error; los demás se
    devuelven."""
    valid: list[ProtocolDef] = []
    errors: list[ConfigError] = []
    for position, protocol in enumerate(protocols):
        reason = None
        for number, task in enumerate(protocol.tasks):
            reason = _task_problem(task, specs_of(task.module, task.action))
            if reason is not None:
                key = f"protocols[{position}].tasks[{number}]"
                errors.append(ConfigError("protocols.toml", key, f"{protocol.id}: {reason}"))
                break
        if reason is None:
            valid.append(protocol)
    return tuple(valid), errors


def _task_problem(task: ProtocolTask, specs: Sequence[Any]) -> str | None:
    intent = f"{task.module}.{task.action}"
    if not specs:
        return f"la acción {intent} no existe"
    if not all(spec.in_protocols for spec in specs):
        return f"la acción {intent} no se puede usar en un protocolo"
    # Obligatorio: lo que todas sus formas piden y ninguna fija por sí misma.
    required = set.intersection(*(
        {slot.name for slot in spec.slots if not slot.optional and slot.name not in spec.fixed}
        for spec in specs
    ))  # fmt: skip
    missing = sorted(required - set(task.params))
    if missing:
        return f"a {intent} le falta el parámetro {', '.join(missing)}"
    return None
