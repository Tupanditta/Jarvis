# Bus de eventos

- **Código:** `core/event_bus.py`, `core/events.py`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Desacoplar el backend (orquestador y módulos de acción) de la interfaz mediante publicación/suscripción, de modo que los módulos informen sin conocer las ventanas (RES-24, RNF-20).

## Comportamiento

- Los eventos son `dataclass` inmutables, tipados por clase. La suscripción es por tipo.
- Los manejadores se ejecutan siempre en el hilo del núcleo, en orden de suscripción. Un manejador que lanza una excepción se registra y no afecta a los demás.
- `publish` se llama desde el hilo del núcleo. `publish_threadsafe` se puede llamar desde cualquier hilo y entrega en el hilo del núcleo.
- La interfaz no se suscribe directamente: lo hace `UiBridge`, que convierte cada evento en una señal de Qt ([hud.md](hud.md)).
- El bus no guarda eventos. La interfaz reconstruye su estado solo con los eventos recibidos; por eso cada evento de contenido lleva la lista completa de su panel, no diferencias.

```python
class EventBus:
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> Unsubscribe: ...
    def publish(self, event: Event) -> None: ...
    def publish_threadsafe(self, event: Event) -> None: ...
```

## Catálogo de eventos

### Ciclo de vida y estado

| Evento | Campos | Publica | Efecto en la interfaz |
|---|---|---|---|
| `SessionOpened` | `session_id`, `name` | Orquestador | Abre la pantalla de sesión con la animación de despertar. |
| `ListeningResumed` | `silent: bool` | Orquestador | Animación de despertar. |
| `RestEntered` | — | Orquestador | Animación de dormirse; la interfaz sigue visible. |
| `SessionClosed` | — | Orquestador | Animación de dormirse; al terminar, oculta todo. |
| `AssistantActivityChanged` | `state`, `activity` | Orquestador | Etiqueta de estado, aspecto del orbe, icono de la bandeja. |
| `MicStatusChanged` | `available: bool` | Captura de audio | Icono de la bandeja. |
| `AudioLevel` | `level: float` (0–1), `source` (`mic` \| `assistant` \| `none`) | Orquestador, a 20 Hz | Reacción del núcleo del orbe (RF-83). |

### Voz y diálogo

| Evento | Campos | Publica |
|---|---|---|
| `TranscriptReady` | `text`, `recognized: bool` | Orquestador |
| `SpeechStarted` | `text`, `interruptible: bool` | Speaker |
| `SpeechFinished` | `interrupted: bool` | Speaker |
| `DialogueOpened` | `question: str`, `expected_type`, `hints: tuple[str, ...]`, `timeout_seconds`, `subject: Mapping \| None` | Orquestador |
| `DialogueClosed` | `outcome` (`answered` \| `cancelled`) | Orquestador |

`subject` es el elemento sobre el que se pregunta, para mostrarlo (p. ej. la sesión que se va a eliminar). `hints` son las respuestas admitidas que se muestran («Sí», «No», «Cancelar»).

### Tareas

| Evento | Campos | Publica |
|---|---|---|
| `TaskUpdated` | `task_id`, `parent_id \| None`, `module`, `description`, `status` (`pendiente` \| `error` \| `completado`), `detail: str \| None`, `at` | `run_task` |

Único evento de estado de tarea, para todos los módulos (RN-01, RF-71). Las tareas de un protocolo llevan como `parent_id` la tarea del protocolo.

### Contenido de los paneles

| Evento | Campos | Publica |
|---|---|---|
| `PanelActivated` | `panel` | Orquestador (según `IntentSpec.panel`) y módulos |
| `SessionChanged` | `session_id`, `name`, `is_important` | Sesión |
| `SessionOverflowed` | `displaced_id`, `displaced_name` | Sesión |
| `HistoryShown` | `sessions: tuple[SessionRow, ...]` | Historial |
| `SessionActivitiesShown` | `session: SessionRow`, `activities: tuple[ActivityRow, ...]` | Historial |
| `WorkdirChanged` | `path` | Comandos |
| `DirectoryListed` | `path`, `entries: tuple[Entry, ...]` | Comandos |
| `DirectoryTreeBuilt` | `root`, `nodes: tuple[TreeNode, ...]`, `dirs`, `files`, `truncated` | Comandos |
| `CommandOutputAppended` | `task_id`, `command`, `lines: tuple[str, ...]`, `stream` (`out` \| `err`) | Comandos |
| `CommandPanelCleared` | — | Comandos |
| `OpenedItemsChanged` | `items: tuple[OpenedItem, ...]` (`id`, `title`, `kind`, `status`, `can_focus`) | Apertura |
| `SearchResultsReady` | `query`, `kind`, `results: tuple[SearchResult, ...]`, `total`, `limited` | Búsqueda |
| `RemindersChanged` | `items: tuple[ReminderItem, ...]` (`index`, `id`, `content`, `status`, `next_trigger`, `deadline`, `highlighted`) | Recordatorio |
| `ProtocolStarted` | `task_id`, `name`, `steps: tuple[str, ...]` | Protocolos |
| `ProtocolFinished` | `task_id`, `completed`, `failed` | Protocolos |
| `ProtocolsListed` | `protocols: tuple[ProtocolRow, ...]` | Protocolos |
| `HelpShown` | `groups: tuple[HelpGroup, ...]` | Orquestador |
| `ConfigReloadFailed` | `file`, `reason` | Configuración |

### Acciones del usuario (interfaz → núcleo)

Se publican con `publish_threadsafe`.

| Evento | Origen | Lo atiende |
|---|---|---|
| `FocusItemRequested(item_id)` | Botón «traer al frente» | Apertura |
| `SilenceRequested` | Botón de silencio | Speaker |
| `OpenSessionRequested` | Bandeja | Orquestador |
| `ShowScreenRequested(visible)` | Bandeja | Interfaz (`window_controller`) |
| `QuitRequested` | Bandeja | Orquestador |

## Criterios de aceptación

- Publicar desde otro hilo entrega en el hilo del núcleo.
- Un manejador que falla no impide la entrega a los demás.
- Una prueba recorre `events.py` y comprueba que todos los eventos son inmutables.

## Prohibiciones

- Los módulos de acción no manipulan ventanas ni importan Qt.
- La interfaz no llama a módulos ni lee la base de datos: solo recibe eventos y publica acciones del usuario.
- No se publican estados de tarea distintos de `pendiente`, `error` y `completado`.
