# Máquina de estados y contexto de diálogo

- **Código:** `core/state_machine.py` (FSM pura y `DialogueContext`), `core/orchestrator.py` (ejecución de efectos y bucle de turnos).
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Coordinar las fases del asistente (entrada escrita, intenciones, ejecución y respuesta) con una máquina de estados finitos (`AssistantState`) y un contexto de diálogo (`DialogueContext`) que permite diálogos de varios turnos sin bloquear la entrada (RES-21, RES-22).

## Estados

| Estado | Situación (RN-43) | Sesión | Qué se atiende de lo que escribe el usuario |
|---|---|---|---|
| `DORMIDO` | Dormido. Estado inicial del proceso. | No | Solo «Hey Jarvis». |
| `IDLE` | Reposo. | Sí | «Hey Jarvis» y «Buenas noches Jarvis». El resto se descarta. |
| `LISTENING_COMMAND` | Escucha. | Sí | Órdenes. |
| `AWAITING_CONFIRMATION` | Espera de una respuesta de sí o no. | Sí | La respuesta y las frases de control. |
| `AWAITING_PARAMETER` | Espera de un dato (nombre, fecha, acción de recordatorio). | Sí | La respuesta y las frases de control. |

Además del estado, el orquestador publica la **actividad** que ve el usuario: `dormido`, `reposo`, `escuchando`, `procesando` (ejecutando una acción), `hablando`, `esperando`. La actividad es informativa; no es un estado de la FSM.

## Entradas

| Entrada | Origen |
|---|---|
| `WakeWord` | Enrutador: el usuario ha escrito la frase de activación «Hey Jarvis» ([entrada-texto.md](entrada-texto.md)). |
| `Control(kind)` con `kind` ∈ `reposo`, `cerrar`, `cancelar` | [enrutador-intenciones.md](enrutador-intenciones.md). |
| `IntentMatched(intent)` / `NoMatch(text)` | Enrutador, en `LISTENING_COMMAND`. |
| `Answer(text)` | Enrutador, en `AWAITING_*`. |
| `ClosingPhraseInIdle` | Enrutador, en `IDLE`. |
| `SilenceTimeout` | Temporizador de 30 s ⚙ sin escribir (RF-78). |
| `DialogueRequested(ctx)` | Un módulo llama a `ctx.ask(…)`. |
| `DialogueTimeout` | Temporizador de 20 s ⚙ (RN-38). |
| `NoticeReady(notice)` | Cola de avisos. |
| `OpenSessionRequested` | Menú de la bandeja o arranque con ⚙ `startup.open_session_on_start`. Equivale a `WakeWord` en `DORMIDO`; sin efecto en los demás estados. |
| `ShutdownRequested` | Salir desde la bandeja o fin de la sesión de Windows. |

## Transiciones

| Estado | Entrada | Estado nuevo | Efectos, en orden |
|---|---|---|---|
| `DORMIDO` | `WakeWord` | `LISTENING_COMMAND` | Abrir sesión (RF-01). Publicar `SessionOpened`. Decir «Sesión iniciada. Le escucho.». Al terminar la frase: entregar los avisos pendientes (RF-41) e iniciar la cuenta de inactividad. |
| `DORMIDO` | cualquier otra | — | Ninguno. |
| `IDLE` | `WakeWord` | `LISTENING_COMMAND` | Publicar `ListeningResumed`. Decir «Le escucho.». Iniciar la cuenta de inactividad al terminar. |
| `IDLE` | `ClosingPhraseInIdle` | `DORMIDO` | Cierre de sesión (ver abajo). |
| `IDLE` | `NoticeReady` de recordatorio | `LISTENING_COMMAND` | Publicar `ListeningResumed(silent=True)`. Entregar el aviso. Iniciar la cuenta de inactividad. |
| `LISTENING_COMMAND` | `IntentMatched` | `LISTENING_COMMAND` | Ejecutar el turno con `run_task`. La cuenta de inactividad se detiene durante el turno y se reinicia al terminar la respuesta. |
| `LISTENING_COMMAND` | `NoMatch` | `LISTENING_COMMAND` | Publicar `CommandReceived(recognized=False)`. Reiniciar la cuenta de inactividad (RN-51). |
| `LISTENING_COMMAND` | `WakeWord` | `LISTENING_COMMAND` | Si hay una locución interrumpible, detenerla (RN-48). Reiniciar la cuenta de inactividad. Sin voz ni animación. |
| `LISTENING_COMMAND` | `Control(cancelar)` | `LISTENING_COMMAND` | Si hay un turno en curso: cancelarlo y decir «Cancelado.». Si no: nada. |
| `LISTENING_COMMAND` | `Control(reposo)` o `SilenceTimeout` | `IDLE` | Cancelar el turno en curso, si lo hay. Publicar `RestEntered`. Decir «A su disposición.». |
| `LISTENING_COMMAND` | `DialogueRequested` | `AWAITING_CONFIRMATION` si el tipo es `BOOLEAN`; si no, `AWAITING_PARAMETER` | Publicar `DialogueOpened`. Decir la pregunta. Iniciar el tiempo de espera al terminarla. |
| `AWAITING_*` | `Answer` válida | `LISTENING_COMMAND` | Resolver el diálogo con la respuesta. Publicar `DialogueClosed(answered)`. El módulo continúa su turno. |
| `AWAITING_*` | `Answer` no válida, primera vez | — | Decir «No le he entendido.» y repetir la pregunta. Reiniciar el tiempo de espera. |
| `AWAITING_*` | `Answer` no válida, segunda vez; `DialogueTimeout`; `Control(cancelar)` | `LISTENING_COMMAND` | Resolver el diálogo como cancelado. Publicar `DialogueClosed(cancelled)`. Decir «Operación cancelada.». |
| `AWAITING_*` | `WakeWord` | — | Reiniciar el tiempo de espera. Sin voz ni animación. |
| `AWAITING_*` | `Control(reposo)` | `IDLE` | Cancelar el diálogo y el turno. Publicar `RestEntered`. Decir «A su disposición.». |
| Con sesión | `Control(cerrar)` | `DORMIDO` | Cierre de sesión. |
| Con sesión | `NoticeReady` (resto de casos) | — | El aviso espera en la cola (RN-39). |
| Con sesión | `ShutdownRequested` | `DORMIDO` | Cierre de sesión sin frase ni animación; después termina el proceso. |
| `DORMIDO` | `ShutdownRequested` | — | Termina el proceso. |

**Cierre de sesión** (efectos, en orden): cancelar diálogo y turno, detener protocolo y binarios (RN-46); eliminar las sesiones marcadas por desbordamiento (RN-09); marcar la sesión como cerrada; llamar a `on_session_closed` de cada módulo; vaciar la cola de avisos y el planificador; publicar `SessionClosed`; decir «Buenas noches. Sesión cerrada.». El estado pasa a `DORMIDO` de inmediato, sin esperar a la frase ni a la animación: «Hey Jarvis» se atiende en cuanto termina la frase.

**Durante una locución.** El orquestador atiende las entradas de una en una y espera a que termine cada frase del ciclo de vida: lo que el usuario envía mientras suena una de ellas se atiende al acabar. Las demás locuciones no retienen la entrada, y «Hey Jarvis» las interrumpe (RN-48).

## Contexto de diálogo

```python
class ExpectedType(Enum):
    BOOLEAN            # sí / no                         → AWAITING_CONFIRMATION
    NEW_FILENAME       # un nombre de archivo o carpeta  → AWAITING_PARAMETER
    DATETIME           # una fecha y hora                → AWAITING_PARAMETER
    REMINDER_ACTION    # "otro aviso …" / "fecha límite …" / "no"  → AWAITING_PARAMETER

@dataclass
class DialogueContext:
    question: Phrase
    expected_type: ExpectedType
    metadata: Mapping[str, object]      # datos de la operación en pausa (ruta destino, id de sesión…)
    timeout_seconds: float              # predeterminado 20 ⚙
    continuation: asyncio.Future        # equivale al pending_callback: se resuelve con la respuesta
    attempts: int = 0

@dataclass(frozen=True)
class DialogueAnswer:
    cancelled: bool
    value: object | None                # bool, str, datetime o ReminderAction, ya validado
```

1. El módulo llama a `await ctx.ask(question, expected_type, metadata=…)`. No bloquea ningún hilo: su corrutina queda suspendida.
2. Solo puede haber un `DialogueContext`. Como los turnos son secuenciales (RN-44), nunca se piden dos a la vez.
3. La validación de la respuesta según `expected_type` la hace el enrutador con los analizadores de entidades:

| Tipo | Respuesta válida |
|---|---|
| `BOOLEAN` | Afirmación («sí», «vale», «de acuerdo», «confirmo», «adelante», «correcto», «hazlo») o negación («no», «negativo», «mejor no», «no lo hagas»). Una negación devuelve `value=False`; no es una cancelación. |
| `NEW_FILENAME` | Cualquier texto no vacío que forme un nombre válido en el sistema de archivos. |
| `DATETIME` | Una expresión de fecha y hora futura. |
| `REMINDER_ACTION` | «otro aviso {fecha}», «fecha límite {fecha}» o una negación («no», «nada más», «listo»). |

4. La autoconfirmación de recordatorios a 300 s (RN-29) no es un diálogo: la gestiona el planificador.

## Interfaz

```python
class StateMachine:
    state: AssistantState
    def handle(self, entry: Input) -> list[Effect]: ...     # pura: sin E/S, sin reloj

class Orchestrator:
    async def run(self) -> None: ...                         # consume entradas y ejecuta efectos
    def submit(self, entry: Input) -> None: ...              # segura desde cualquier hilo
    # Se suscribe a `TextSubmitted` y `UserTyping` del bus (entrada-texto.md).
    async def run_task(self, module: str, action: str, params, *, origin, parent=None) -> ActionResult: ...
```

## Criterios de aceptación

- Cada fila de la tabla de transiciones tiene una prueba unitaria de `StateMachine.handle`.
- Con dobles: los casos de uso CU-03, CU-04 y CU-05 completos, incluidas sus alternativas.
- Un turno que lanza una excepción deja la FSM en `LISTENING_COMMAND` y la tarea en `error` (RNF-23).
- Lo escrito durante una frase del ciclo de vida se atiende al terminar la frase.
- Teclear sin enviar reinicia la cuenta de inactividad.

## Prohibiciones

- Prohibido un pipeline lineal sin estado.
- Prohibido que un módulo espere la respuesta del usuario de forma síncrona.
- Prohibido que la FSM haga E/S o lea el reloj: solo devuelve efectos.
- Prohibido clasificar como intención nueva el texto recibido en `AWAITING_*`, salvo las frases de control.
