"""Datos que llevan los eventos de contenido de los paneles (bus-eventos.md).

Son valores inmutables: cada evento de contenido lleva la lista completa de su panel.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Entry:
    """Elemento de un listado de directorio."""

    name: str
    is_dir: bool


@dataclass(frozen=True)
class TreeNode:
    """Entrada del árbol de directorios, en orden de dibujo. `depth`: nivel, desde 1."""

    name: str
    depth: int
    is_dir: bool


OpenedKind = Literal["aplicacion", "pagina", "carpeta"]


@dataclass(frozen=True)
class OpenedItem:
    """Elemento abierto por el asistente en la sesión."""

    id: int
    title: str
    kind: OpenedKind
    status: str  # estado de la apertura (RN-01)
    can_focus: bool


@dataclass(frozen=True)
class LaunchTarget:
    """Elemento del catálogo que el asistente puede abrir: aplicación o página."""

    name: str
    kind: OpenedKind


@dataclass(frozen=True)
class SearchResult:
    """Resultado numerado de una búsqueda. `index`: lo que el usuario escribe (RN-50)."""

    index: int
    name: str
    is_dir: bool
    folder: str
    path: str


ReminderStatus = Literal["activo", "vencido"]


@dataclass(frozen=True)
class ReminderItem:
    """Recordatorio del panel. `index`: lo que el usuario escribe (RN-50). `highlighted`: el
    notificado o leído."""

    index: int
    id: int
    content: str
    status: ReminderStatus
    next_trigger: datetime | None
    deadline: datetime | None
    highlighted: bool = False


@dataclass(frozen=True)
class ProtocolRow:
    """Protocolo de la configuración, para el listado. `steps`: la descripción de sus tareas."""

    id: str
    name: str
    aliases: tuple[str, ...]
    important: bool
    steps: tuple[str, ...]


@dataclass(frozen=True)
class IntrusionItem:
    """Un aviso de intrusión, para la tarjeta crítica."""

    alert_id: int
    at: datetime  # UTC
    attempts: int
    origin: str  # 'inicio' o 'configuracion'
    profile_name: str = ""  # para el Acedor, que recibe los de todos los perfiles


@dataclass(frozen=True)
class NamedItem:
    """Algo con id y nombre: un perfil, un módulo."""

    id: str
    name: str


@dataclass(frozen=True)
class CredentialItem:
    """La contraseña de un perfil protegido, para la ventana Credenciales del Acedor. `None`:
    todavía no se puede ver (se custodia la próxima vez que su dueño entre)."""

    profile_id: str
    profile_name: str
    password: str | None = field(default=None, repr=False)
