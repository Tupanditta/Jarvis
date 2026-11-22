"""Permisos por perfil: qué módulos y paneles puede usar una sesión.

Funciones puras sobre el registro de módulos. El orquestador calcula el alcance al abrir
sesión, lo pasa al enrutador y a la interfaz, y `run_task` lo consulta antes de ejecutar.

- Los módulos `always_allowed` (y el núcleo) se permiten siempre.
- Los módulos `admin` solo los usa el Acedor, que no usa ningún otro.
- El resto se permite salvo que el Acedor lo haya restringido para el perfil.
- Los medidores de la pantalla de sesión no son módulos: restringidos, solo se ocultan.
"""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from jarvis_assistant.config import ADMIN_PROFILE_ID, METERS
from jarvis_assistant.core.action_api import ActionModule

# Clave de una acción registrada (`módulo`, `acción`) → panel que activa, o None.
Panels = Mapping[tuple[str, str], str | None]


@dataclass(frozen=True)
class Scope:
    """Alcance de una sesión: los módulos que puede usar y los paneles que se ocultan."""

    allowed: frozenset[str]
    hidden_panels: frozenset[str]


def is_admin(module: ActionModule) -> bool:
    return bool(getattr(module, "admin", False))


def is_always_allowed(module: ActionModule) -> bool:
    return bool(getattr(module, "always_allowed", False))


def restrictable(modules: Mapping[str, ActionModule]) -> tuple[tuple[str, str], ...]:
    """Lo que el Acedor puede conceder o restringir, como (id, título): los módulos de acción
    normales, menos los que el asistente necesita siempre, y los medidores."""
    names = tuple(
        (name, module.title) for name, module in modules.items()
        if not is_admin(module) and not is_always_allowed(module)
    )  # fmt: skip
    return names + tuple((meter.id, meter.title) for meter in METERS)


def session_scope(
    modules: Mapping[str, ActionModule],
    panels: Panels,
    profile_id: str,
    restricted: Iterable[str],
    *,
    core_module: str,
) -> Scope:
    """El alcance del perfil `profile_id`. `restricted`: lo que el Acedor le ha quitado (se
    ignora para el propio Acedor). `core_module`: el nombre del núcleo, siempre permitido."""
    admin = {name for name, module in modules.items() if is_admin(module)}
    always = {core_module} | {name for name, module in modules.items() if is_always_allowed(module)}
    if profile_id == ADMIN_PROFILE_ID:
        blocked: frozenset[str] = frozenset()
        allowed = frozenset(always | admin)
    else:
        blocked = frozenset(restricted)
        allowed = frozenset(
            name for name in (*modules, core_module)
            if name in always or (name not in admin and name not in blocked)
        )  # fmt: skip
    shown = {panel for (module, _action), panel in panels.items() if module in allowed}
    hidden = {
        panel for (module, _action), panel in panels.items()
        if module not in allowed and panel is not None and panel not in shown
    }  # fmt: skip
    hidden |= {meter.id for meter in METERS if meter.id in blocked}
    return Scope(allowed, frozenset(hidden))
