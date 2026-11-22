"""Eventos del bus (bus-eventos.md).

Todos son `dataclass` inmutables y la suscripción es por clase. El bus no guarda eventos:
la interfaz reconstruye su estado solo con los que recibe.

Este módulo contiene los eventos del ciclo de vida, de estado, de órdenes, de voz, de diálogo,
de tareas, el panel activo, las acciones del usuario y los de contenido de los paneles de los
módulos ya construidos; los demás se añaden con los módulos que los publican.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal

from jarvis_assistant.config import Config
from jarvis_assistant.core.action_api import HelpGroup
from jarvis_assistant.core.content import (
    CatalogItem,
    CredentialItem,
    Entry,
    IntrusionItem,
    LaunchTarget,
    NamedItem,
    OpenedItem,
    ProtocolRow,
    ReminderItem,
    SearchResult,
    TreeNode,
)
from jarvis_assistant.core.repositories import ActivityRow, SessionRow


@dataclass(frozen=True)
class Event:
    """Base de todos los eventos del bus."""


class Activity(StrEnum):
    """Lo que el usuario ve que hace el asistente. Informativa: no es un estado de la FSM."""

    DORMIDO = "dormido"
    REPOSO = "reposo"
    ESCUCHANDO = "escuchando"  # atiende las órdenes escritas
    PROCESANDO = "procesando"
    HABLANDO = "hablando"
    ESPERANDO = "esperando"


AudioSource = Literal["assistant", "none"]
_AUDIO_SOURCES = ("assistant", "none")


# --- Ciclo de vida y estado ------------------------------------------------------------------


@dataclass(frozen=True)
class SessionOpened(Event):
    """Se ha abierto una sesión: la interfaz muestra la pantalla con la animación de despertar.
    `profile_id`: el perfil con el que se ha abierto; la pantalla toma su plantilla."""

    session_id: int
    name: str
    profile_id: str = ""


@dataclass(frozen=True)
class ListeningResumed(Event):
    """El asistente vuelve de reposo a escucha. `silent`: sin la frase «Le escucho»."""

    silent: bool = False


@dataclass(frozen=True)
class RestEntered(Event):
    """El asistente pasa a reposo; la interfaz sigue visible."""


@dataclass(frozen=True)
class SessionClosed(Event):
    """La sesión se ha cerrado; al terminar la animación, la interfaz se oculta."""


@dataclass(frozen=True)
class AssistantActivityChanged(Event):
    """Nuevo estado de la FSM (por su nombre) y actividad visible."""

    state: str
    activity: Activity


@dataclass(frozen=True)
class AudioLevel(Event):
    """Nivel de audio (0-1) de la voz del asistente, a 20 Hz."""

    level: float
    source: AudioSource

    def __post_init__(self) -> None:
        if not 0.0 <= self.level <= 1.0:
            raise ValueError(f"El nivel de audio debe estar entre 0 y 1: {self.level}")
        if self.source not in _AUDIO_SOURCES:
            raise ValueError(f"Origen de audio desconocido: {self.source!r}")


# --- Sesión ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionChanged(Event):
    """Datos de la sesión actual: al abrirla y cada vez que cambian."""

    session_id: int
    name: str
    is_important: bool


@dataclass(frozen=True)
class SessionsDeleted(Event):
    """Se han borrado sesiones del historial y las demás se han renumerado (ids 1..N).
    `deleted`: los ids borrados. `renumbered`: {id anterior: id nuevo} de las que cambian; la
    sesión actual puede estar entre ellas."""

    deleted: tuple[int, ...]
    renumbered: Mapping[int, int]


@dataclass(frozen=True)
class SessionOverflowed(Event):
    """Ya había 10 sesiones importantes: la más antigua deja de serlo y se eliminará al cerrar
    la actual (RN-07, RN-08)."""

    displaced_id: int
    displaced_name: str


# --- Órdenes y voz ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandReceived(Event):
    """Texto de una orden escrita. `recognized=False`: frase no reconocida (RN-51)."""

    text: str
    recognized: bool


@dataclass(frozen=True)
class SpeechStarted(Event):
    """El asistente empieza a decir `text`. `interruptible`: no es del ciclo de vida."""

    text: str
    interruptible: bool


@dataclass(frozen=True)
class SpeechFinished(Event):
    interrupted: bool


# --- Diálogo, tareas y paneles ---------------------------------------------------------------

TaskStatus = Literal["pendiente", "error", "completado"]
TASK_STATUSES = ("pendiente", "error", "completado")
DialogueOutcome = Literal["answered", "cancelled"]


@dataclass(frozen=True)
class DialogueOpened(Event):
    """El asistente ha hecho una pregunta. `hints`: respuestas admitidas que se muestran."""

    question: str
    expected_type: str
    hints: tuple[str, ...]
    timeout_seconds: float
    subject: Mapping[str, object] | None = None


@dataclass(frozen=True)
class DialogueClosed(Event):
    outcome: DialogueOutcome


@dataclass(frozen=True)
class TaskUpdated(Event):
    """Único evento de estado de tarea (RN-01). `parent_id`: la tarea del protocolo, si la hay."""

    task_id: int
    parent_id: int | None
    module: str
    description: str
    status: TaskStatus
    detail: str | None
    at: datetime

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError(f"Estado de tarea desconocido: {self.status!r}")


@dataclass(frozen=True)
class OrderQueueChanged(Event):
    """Órdenes que esperan su turno en la cola, en su orden. Las que ya se ejecutan son
    tareas `pendiente` y no están aquí."""

    waiting: tuple[str, ...]


@dataclass(frozen=True)
class PanelActivated(Event):
    """`panel` pasa a ser el panel activo de la interfaz."""

    panel: str


@dataclass(frozen=True)
class WindowAsideRequested(Event):
    """«Aparta …»: la ventana flotante `window` (su título) se aparta a un borde si está
    abierta. Sin ventana, se apartan todas las abiertas. Con `aside` falso es «desaparta …»:
    vuelven a su sitio las apartadas."""

    window: str | None = None
    aside: bool = True


# --- Contenido de los paneles ----------------------------------------------------------------


@dataclass(frozen=True)
class WorkdirChanged(Event):
    """Directorio de trabajo que muestra el panel de comandos de `console`."""

    path: str
    console: str = "comandos"


@dataclass(frozen=True)
class DirectoryListed(Event):
    """Listado de `ls`: carpetas primero, en orden alfabético. `total`: entradas reales."""

    path: str
    entries: tuple[Entry, ...]
    total: int
    console: str = "comandos"


@dataclass(frozen=True)
class DirectoryTreeBuilt(Event):
    """Árbol del mapeo de entorno (RN-40), en orden de dibujo."""

    root: str
    nodes: tuple[TreeNode, ...]
    dirs: int
    files: int
    truncated: bool
    console: str = "comandos"


@dataclass(frozen=True)
class CommandOutputAppended(Event):
    """Líneas nuevas de la salida de un binario. `stream`: `out` o `err`."""

    task_id: int
    command: str
    lines: tuple[str, ...]
    stream: Literal["out", "err"]
    console: str = "comandos"


@dataclass(frozen=True)
class CommandPanelCleared(Event):
    """`clear`: el panel de comandos de `console` se vacía."""

    console: str = "comandos"


@dataclass(frozen=True)
class ConsoleOpened(Event):
    """Hay una consola de Comandos extra (`core/workdir.py`): su ventana se abre, o se trae al
    frente si ya estaba. La abre un protocolo o el botón de una ventana de Comandos."""

    console: str
    title: str


@dataclass(frozen=True)
class ConsoleRequested(Event):
    """Botón de una ventana de Comandos: una consola nueva en la carpeta de `source`."""

    source: str


@dataclass(frozen=True)
class ConsoleClosed(Event):
    """El usuario ha cerrado la ventana de una consola extra: desaparece con lo que tenía en
    marcha."""

    console: str


@dataclass(frozen=True)
class ConsoleFocused(Event):
    """La ventana de Comandos que está delante ha cambiado: las órdenes sin consola van a la
    suya."""

    console: str


@dataclass(frozen=True)
class OpenedItemsChanged(Event):
    """Lista completa de elementos abiertos. `can_focus_windows`: el sistema permite traer
    ventanas al frente; si no, el botón no se muestra."""

    items: tuple[OpenedItem, ...]
    can_focus_windows: bool = True


@dataclass(frozen=True)
class LaunchTargetsChanged(Event):
    """Aplicaciones y páginas del catálogo, para abrirlas desde la ventana de aperturas."""

    targets: tuple[LaunchTarget, ...]


@dataclass(frozen=True)
class CatalogShown(Event):
    """Ventana Catálogo: lista completa de aplicaciones, páginas y comandos, tras cada cambio.
    `problem`: por qué no se ha podido añadir o eliminar lo último que se pidió; vacío si se
    ha hecho (el formulario de la ventana se vacía)."""

    items: tuple[CatalogItem, ...]
    problem: str = ""


@dataclass(frozen=True)
class SearchResultsReady(Event):
    """Resultados numerados que muestra el panel. `total`: los encontrados."""

    query: str
    kind: str  # 'archivos', 'carpetas' o 'ambos'
    results: tuple[SearchResult, ...]
    total: int
    limited: bool


@dataclass(frozen=True)
class RemindersChanged(Event):
    """Lista completa del panel de recordatorios, numerada (RN-50), tras cada cambio."""

    items: tuple[ReminderItem, ...]


@dataclass(frozen=True)
class ProtocolStarted(Event):
    """Empieza un protocolo: `task_id` es su tarea; `steps` y `step_ids`, la descripción y la
    subtarea de cada una de sus tareas, en orden, todas en `pendiente` (RF-53)."""

    task_id: int
    name: str
    steps: tuple[str, ...]
    step_ids: tuple[int, ...]


@dataclass(frozen=True)
class ProtocolFinished(Event):
    """El protocolo ha terminado (o se ha detenido): tareas completadas y fallidas."""

    task_id: int
    completed: int
    failed: int


@dataclass(frozen=True)
class ProtocolsListed(Event):
    """Protocolos de la configuración (RF-99)."""

    protocols: tuple[ProtocolRow, ...]


@dataclass(frozen=True)
class HistoryShown(Event):
    """Sesiones visibles del historial (RN-10). `current_id`: la sesión actual."""

    sessions: tuple[SessionRow, ...]
    current_id: int | None = None


@dataclass(frozen=True)
class SessionActivitiesShown(Event):
    session: SessionRow
    activities: tuple[ActivityRow, ...]


@dataclass(frozen=True)
class HelpShown(Event):
    """Órdenes disponibles, agrupadas por módulo (RF-92)."""

    groups: tuple[HelpGroup, ...]


@dataclass(frozen=True)
class ConfigApplied(Event):
    """El núcleo aplica una configuración: al arrancar, al abrir sesión y al guardar desde la
    ventana de configuración con la sesión cerrada. La interfaz toma de aquí los perfiles,
    las plantillas y el sonido."""

    config: Config


@dataclass(frozen=True)
class ConfigReloadFailed(Event):
    """Un archivo de configuración es inválido al recargar: se conserva el anterior (RF-96)."""

    file: str
    reason: str


# --- Acciones del usuario (interfaz → núcleo, con `publish_threadsafe`) ----------------------


@dataclass(frozen=True)
class FocusItemRequested(Event):
    """Botón «traer al frente» de un elemento abierto."""

    item_id: int


@dataclass(frozen=True)
class ActionRequested(Event):
    """Un control de una ventana pide una acción de un módulo. Entra en la cola de órdenes
    como una orden escrita y se responde igual, también con voz. `params`: las entidades ya con
    su tipo (una ruta es un `Path`)."""

    module: str
    action: str
    params: Mapping[str, object] = field(default_factory=dict)
    console: str | None = None  # la ventana de Comandos que la pide; None: la activa


@dataclass(frozen=True)
class TextSubmitted(Event):
    """El usuario ha enviado `text` desde la caja de texto."""

    text: str


@dataclass(frozen=True)
class UserTyping(Event):
    """El usuario está tecleando en la caja de texto; como mucho, una vez por segundo."""


@dataclass(frozen=True)
class WindowPressed(Event):
    """El usuario ha pulsado una ventana flotante: moverla, cambiar su tamaño o un control.
    En reposo despierta en silencio; en escucha cuenta como actividad."""


@dataclass(frozen=True)
class SilenceRequested(Event):
    """Botón de silencio: calla la locución en curso."""


@dataclass(frozen=True)
class ProfileSelected(Event):
    """El usuario elige perfil en la pantalla dormida; la próxima sesión se abre con él."""

    profile_id: str


@dataclass(frozen=True)
class ConfigSaved(Event):
    """La ventana de configuración ha guardado cambios. Con la sesión cerrada, el núcleo
    vuelve a cargar la configuración; con ella abierta, se aplican al abrir la siguiente."""


@dataclass(frozen=True)
class OpenSessionRequested(Event):
    """«Abrir sesión» en el menú de la bandeja."""


@dataclass(frozen=True)
class ShowScreenRequested(Event):
    """«Mostrar pantalla» en el menú de la bandeja."""

    visible: bool = True


@dataclass(frozen=True)
class ShowHudRequested(Event):
    """«Mostrar HUD» en el menú de la bandeja: vuelve a mostrar el HUD si se había ocultado."""


@dataclass(frozen=True)
class QuitRequested(Event):
    """«Salir» en el menú de la bandeja o fin de la sesión del sistema operativo."""


# --- Perfiles protegidos ---------------------------------------------------------------------
# La contraseña solo viaja en `AccessAttempted`, de la interfaz al núcleo: no pasa por el
# enrutador, no se publica como orden recibida y su `repr` no la muestra (RES-48).


@dataclass(frozen=True)
class ProtectedProfilesChanged(Event):
    """Qué perfiles piden contraseña. Se publica al arrancar y al volver a cargar la
    configuración; el selector de perfiles muestra un candado en ellos. `admin_active`: el
    Acedor está activado y el selector lo ofrece."""

    profile_ids: frozenset[str]
    admin_active: bool = False


@dataclass(frozen=True)
class AccessChallenged(Event):
    """«Hey Jarvis» (o «Abrir sesión») en un perfil protegido: la interfaz muestra la caja de
    la contraseña en el centro de la pantalla."""

    profile_id: str
    profile_name: str


@dataclass(frozen=True)
class AccessDenied(Event):
    """Contraseña incorrecta: la caja se sacude y se queda abierta."""


@dataclass(frozen=True)
class AccessClosed(Event):
    """La caja de la contraseña se cierra: acceso concedido, cancelado o tercer fallo. Quien
    la ve no sabe si se ha registrado un aviso de intrusión."""

    granted: bool = False


@dataclass(frozen=True)
class AccessAttempted(Event):
    """La interfaz envía la contraseña escrita en la caja."""

    password: str = field(repr=False)


@dataclass(frozen=True)
class AccessCancelled(Event):
    """El usuario cierra la caja de la contraseña (Esc)."""


@dataclass(frozen=True)
class IntrusionAlertsShown(Event):
    """Al entrar en un perfil protegido con avisos sin confirmar: la tarjeta crítica."""

    profile_id: str
    alerts: tuple[IntrusionItem, ...]


@dataclass(frozen=True)
class IntrusionAcknowledged(Event):
    """El usuario pulsa «Entendido» en la tarjeta crítica."""

    alert_ids: tuple[int, ...]


# --- Permisos y Acedor -----------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionsApplied(Event):
    """Al abrir sesión: las ventanas de los módulos que el perfil no puede usar no se muestran
    ni se pueden abrir."""

    hidden_panels: frozenset[str]


@dataclass(frozen=True)
class PermissionsShown(Event):
    """Ventana Permisos del Acedor: perfiles, módulos y lo que cada perfil tiene restringido
    (pares perfil, módulo)."""

    profiles: tuple[NamedItem, ...]
    modules: tuple[NamedItem, ...]
    restricted: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class PermissionChangeRequested(Event):
    """El Acedor pulsa un interruptor de la ventana Permisos."""

    profile_id: str
    module: str
    allowed: bool


@dataclass(frozen=True)
class CredentialsShown(Event):
    """Ventana Credenciales del Acedor. Las contraseñas no salen en el `repr`."""

    items: tuple[CredentialItem, ...]


@dataclass(frozen=True)
class ProfilesListed(Event):
    """Ventana Perfiles del Acedor: los perfiles que puede eliminar."""

    profiles: tuple[NamedItem, ...]


@dataclass(frozen=True)
class ProfileRemovalRequested(Event):
    """El Acedor pulsa «Eliminar» en la ventana Perfiles."""

    profile_id: str
