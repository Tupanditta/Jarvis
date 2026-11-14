# Diseño: entrada por texto en lugar de voz

- **Fecha:** 2026-11-14
- **Estado:** pendiente de aprobación del propietario
- **Alcance:** código de `implementation/` y especificación de `software/`

## 1. Intención

Jarvis deja de escuchar. El propietario escribe sus órdenes en una caja de texto y Jarvis
responde como hasta ahora: hablando y mostrando el estado en pantalla.

**Por qué.** El reconocimiento de voz no interpreta bien las peticiones y se ha convertido en
el cuello de botella del proyecto. El propietario quiere seguir teniendo la aplicación como
entorno de trabajo, sin depender de que el asistente le entienda al hablar.

**Qué debe sentirse igual.** La experiencia es la de antes sin usar la voz: los mismos estados,
las mismas frases de control y las mismas respuestas habladas. Todo lo que hacía la voz del
propietario pasa a hacerse escribiendo.

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**

1. Al abrir la aplicación se ve una ventana de fondo oscuro con una caja de texto.
2. Escribir «Hey Jarvis» abre la sesión, con su frase hablada de apertura.
3. Las frases de control y las órdenes se escriben y llegan al mismo enrutador que antes recibía
   la transcripción.
4. La máquina de estados conserva sus estados y transiciones.
5. La salida por voz (Piper) no cambia.
6. No queda en el repositorio código, pruebas, modelos, dependencias ni configuración de la
   entrada por voz.
7. La especificación de `software/` describe el asistente tal como queda.

**No objetivos**

- Botones en la ventana. El propietario no quiere ninguno por ahora; se decidirán cuando existan
  módulos de acción.
- Módulos de acción (abrir aplicaciones, recordatorios, búsqueda). Siguen sin existir.
- La interfaz completa de la fase 2 (orbe, paneles, HUD). Aquí solo se adapta la ventana mínima.
- Un atajo de teclado global para llevar el foco a la caja.
- Cambiar el nombre del repositorio, de la carpeta o del paquete `asistente-voz-personal`.
- Una vía para volver a la voz por configuración.

**Anti-objetivos**

- Dejar código de captura o transcripción desconectado «por si acaso».
- Cambiar el comportamiento de los estados aprovechando el cambio de entrada.
- Renumerar los identificadores de requisitos, reglas o casos de uso de la especificación.

## 3. Restricciones

- **Git.** El propietario crea todos los commits. Casi todo el código de la fase 1 está sin
  confirmar: `orchestrator.py`, `state_machine.py`, `main.py`, `speaker/`, `ui/`,
  `audio_capture/`, `transcriber/` y la mayoría de las pruebas aparecen como archivos sin
  seguimiento. Lo que se borre de ahí no se puede recuperar. **Primer paso del plan: el
  propietario confirma el estado actual antes de que se borre nada.**
- **Entorno.** Las instalaciones y desinstalaciones se hacen con
  `.\implementation\.venv\Scripts\pip.exe`.
- **Datos.** Ningún dato personal ni credencial en archivos del repositorio.
- **Sin subagentes** salvo que el propietario los pida.
- La carpeta de datos del usuario no se toca, salvo la migración de la base de datos (sección 6.7).
  El archivo `wakeword_verifier.pkl` que pueda existir allí queda huérfano; el propietario puede
  borrarlo a mano.

## 4. Enfoques considerados

| Enfoque | Qué supone | Ventajas | Inconvenientes |
|---|---|---|---|
| **A. Quitar la entrada por voz del todo** | Se borran captura, transcriptor, sus pruebas, modelos, dependencias y configuración. La caja entrega el texto al orquestador. | Arranque rápido, menos código, código y especificación coinciden. | Volver a la voz es rehacerla. |
| B. Dos modos por configuración | `input.mode = text \| voice`; la voz queda apagada. | Vuelta atrás con una línea. | Dos caminos que probar y mantener en cada módulo futuro; modelos y dependencias siguen instalados. |
| C. Desconectar sin borrar | El orquestador deja de usar captura y transcriptor; los paquetes se quedan. | Cambio pequeño hoy. | Código muerto que se degrada y confunde. |

**Elegido por el propietario: A.** Pidió un cambio drástico que elimine el cuello de botella; B y
C lo conservan. Si en el futuro quiere voz, un reconocedor mejor se conecta en el mismo punto por
el que ahora entra el texto.

## 5. Comportamiento

### 5.1 Correspondencia entre voz y texto

Decidido por el propietario: mismos estados, mismas frases, todo por texto. La tabla es la
traducción propuesta, que el propietario vio sin objeciones.

| Antes, por voz | Ahora, por texto |
|---|---|
| «Hey Jarvis» en `DORMIDO` | Escribirlo abre la sesión: «Sesión iniciada. Le escucho.» |
| «Hey Jarvis» en `IDLE` | Escribirlo vuelve a `LISTENING_COMMAND`: «Le escucho.» |
| «Hey Jarvis» mientras el asistente habla | Escribirlo corta la locución, si es interrumpible |
| «Gracias Jarvis» | Escrito: pasa a `IDLE`, «A su disposición.» |
| «Buenas noches Jarvis» (en escucha o en reposo) | Escrito: cierra la sesión, «Buenas noches. Sesión cerrada.» |
| «Cancelar», «cancela», «olvídalo», «déjalo» | Escritos: cancelan el turno |
| Órdenes | Escritas; mismo enrutador y mismo catálogo de intenciones |
| Frase no reconocida | Se muestra el texto con la marca «no reconocido»; el asistente no dice nada |
| Silencio de N segundos en escucha lleva a reposo | N segundos sin enviar texto ni teclear llevan a reposo |
| En reposo solo se atienden «Hey Jarvis» y el cierre | Igual: cualquier otro texto se descarta sin efecto |
| En dormido solo se atiende «Hey Jarvis» | Igual |

El texto se envía con Enter. Un envío vacío o solo con espacios no hace nada. La comparación
sigue siendo aproximada (normalizador y `rapidfuzz`), así que «hey jarvis», «Hey Jarvis» y
«hey jarbis» valen lo mismo.

### 5.2 Ventana

```
┌──────────────────────────────────────────────┐
│ Jarvis                                 _ □ ✕ │
├──────────────────────────────────────────────┤
│                                              │
│             Sesión 12: Sesión 12             │
│                                              │
│                  Escuchando                  │
│                                              │
│          «abre chrome» (no reconocido)       │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Escriba una orden                      │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

- Fondo oscuro y texto claro, con los colores de `software/Interfaz/README.md`
  (`bg.base` `#05070B`, `text.primary` `#E6F1F8`, `text.secondary` `#8FA6B8`).
- Se muestra al arrancar y sigue visible en `DORMIDO` y al cerrar la sesión. Antes se ocultaba
  mientras el asistente dormía.
- La caja tiene el foco al mostrarse la ventana y lo recupera tras cada envío. Se vacía al enviar.
- El texto de ayuda de la caja depende del estado:

| Estado | Texto de ayuda |
|---|---|
| `DORMIDO` | Escriba «Hey Jarvis» para iniciar la sesión |
| `IDLE` | En reposo. Escriba «Hey Jarvis» |
| `LISTENING_COMMAND` y `AWAITING_*` | Escriba una orden |

- Cerrar la ventana con ✕ la oculta; el proceso sigue en la bandeja. «Mostrar pantalla» en el menú
  de la bandeja la devuelve al frente con el foco en la caja, y pasa a estar disponible también en
  `DORMIDO`. «Abrir sesión» en la bandeja sigue abriendo la sesión y además muestra la ventana.
- Ningún botón.

### 5.3 Texto escrito mientras el asistente habla

El orquestador atiende las entradas de una en una y espera a que termine cada frase del ciclo de
vida. El texto enviado durante una de esas frases se atiende al acabar. Las frases del ciclo de
vida siguen sin poder interrumpirse. Las locuciones interrumpibles llegarán con los módulos de
acción y se cortan escribiendo «Hey Jarvis», como antes con la voz.

## 6. Diseño técnico

### 6.1 Camino de la entrada

```
caja de texto (hilo de Qt)
   └─ bus.publish_threadsafe(TextSubmitted(text))
        └─ Orchestrator: router.route(text, estado) → entrada de la FSM → efectos
```

- Evento nuevo `TextSubmitted(text)` en `core/events.py`, en el bloque de acciones del usuario.
- Evento nuevo `UserTyping()`: la ventana lo publica al teclear, como mucho una vez por segundo.
  El orquestador reinicia con él la cuenta de inactividad si está en `LISTENING_COMMAND`.
- `TranscriptReady` pasa a llamarse `CommandReceived(text, recognized)`. Se publica igual que hoy:
  con las frases de control reconocidas y con las no reconocidas.
- El orquestador se suscribe a `TextSubmitted` y encola el texto. El antiguo `_on_utterance` se
  reduce a enrutar el texto y entregar el resultado a la FSM.

### 6.2 Enrutador

`IntentRouter.route` reconoce además la frase de activación:

- Frases de activación, ya normalizadas: `hey jarvis` y `jarvis`.
- En `DORMIDO` y en `IDLE`: si el texto alcanza el umbral, devuelve `fsm.WakeWord()`. En `IDLE`
  sigue reconociendo además la frase de cierre.
- En los estados de atención: la frase de activación compite con las frases de control por la
  mejor puntuación y, si gana y alcanza el umbral, devuelve `fsm.WakeWord()`.
- Umbral nuevo `router.wake_threshold`, predeterminado 80, entre 0 y 100.

### 6.3 Máquina de estados

Sin cambios de estados ni de transiciones. Cambios menores:

- Desaparece el efecto `LoadTranscriber`.
- `WakeWord` conserva su nombre; su descripción pasa a ser «frase de activación escrita».
- El motivo de cierre `"voz"` pasa a `"orden"` (sección 6.7).

### 6.4 Orquestador

Se eliminan: los protocolos `Capture` y `CaptureController`, el transcriptor, la época (`epoch`)
que descartaba órdenes de voz atrasadas, el indicador `_processing` y la comprobación de «hay voz
en curso» al vencer la cuenta de silencio. Se conserva la cuenta de inactividad con su
temporizador y su testigo. La actividad `PROCESANDO` sigue en la enumeración para los módulos de
acción, aunque de momento nada la publique.

`AudioLevel` solo admite los orígenes `assistant` y `none`: el nivel se publica mientras el
asistente habla.

### 6.5 Voz de salida

`Speaker` pierde el parámetro `capture_gate` y las llamadas a `speech_started` y
`speech_finished`. El resto no cambia.

### 6.6 Proceso, bandeja y configuración

- `main.py`: `Adapters` pierde `microphone`, `wakeword`, `vad` y `transcriber`; `App` pierde
  `capture`; `CoreThread` deja de arrancar y parar la captura. La ventana se muestra al arrancar.
- `paths.py`: `required_models` exige solo los dos archivos de Piper. Desaparecen
  `verifier_path` y `VERIFIER_FILE_NAME`.
- `process/tray.py`: desaparecen el estado «micrófono no disponible», su color y
  `MicStatusChanged`. «Mostrar pantalla» siempre visible.
- `config.py` y `settings.toml` predeterminado:
  - Se elimina la sección `[stt]`.
  - Se elimina la sección `[audio]`. Su única clave superviviente se traslada a una sección nueva:
    `[input] inactivity_to_idle_seconds = 30` (entre 5 y 600).
  - `closing_phrase_in_idle` desaparece: el cierre en reposo se reconoce siempre.
  - Se añade `router.wake_threshold`.
  - Se elimina `ui.wake_brings_screen_to_front`: quien escribe ya está en la ventana.
  - Un `settings.toml` antiguo del usuario con claves retiradas solo produce avisos de «clave
    desconocida»; el archivo se carga igualmente. Es el comportamiento actual del cargador.

### 6.7 Base de datos

La tabla `sessions` restringe `close_reason` a `'voz'`, `'salida'` o `'interrumpida'`. Migración
nueva `0002` que reconstruye la restricción con `'orden'` en lugar de `'voz'` y convierte las
filas existentes.

### 6.8 Qué se borra

- Código: `audio_capture/` y `transcriber/` enteros.
- Guiones: `calibrate_wakeword.py`, `diagnose_mic.py`, `make_fixture_audio.py`. `fetch_models.py`
  descarga solo la voz de Piper.
- Pruebas: `tests/unit/audio_capture/`, `tests/unit/transcriber/`, `tests/fakes/audio.py`, los
  audios de `tests/fixtures/audio/`, y las partes de micrófono, activación, VAD y Whisper de
  `tests/fakes/voice.py`, `tests/hardware/`, `tests/models/` y `tests/manual/`.
- Modelos locales: `models/openwakeword/` y `models/faster-whisper-small/`.
- Dependencias de `pyproject.toml`: `openwakeword`, `faster-whisper`, `scipy`, `scikit-learn`, y
  su desinstalación del entorno virtual. `sounddevice` se queda (reproducción). `onnxruntime` se
  queda si Piper lo necesita.

### 6.9 Pruebas

- Enrutador: frase de activación en cada estado, con erratas y con el umbral.
- Orquestador: `TextSubmitted` recorre el ciclo completo; `UserTyping` reinicia la cuenta; el
  texto en reposo y en dormido se descarta.
- Integración: `tests/integration/test_lifecycle.py` reescrito con texto en lugar de audio.
- Ventana (pytest-qt): visible al arrancar y en dormido, Enter publica `TextSubmitted` y vacía la
  caja, envío vacío sin efecto, texto de ayuda por estado, ✕ oculta sin terminar el proceso.
- Migración `0002`: una base con filas `'voz'` queda con `'orden'`.
- La batería completa y `ruff` pasan al terminar.

## 7. Especificación (`software/`)

Los identificadores no se renumeran. Un requisito, regla o restricción que deja de aplicarse se
conserva con su identificador y la marca «Retirado: entrada por texto».

| Documento | Cambio |
|---|---|
| `Modulos/Infraestructura/captura-audio.md`, `transcriptor.md` | Se retiran. Se anotan en «Documentos retirados» de `README.md`. |
| `Modulos/Infraestructura/entrada-texto.md` | Nuevo: la caja, los eventos `TextSubmitted` y `UserTyping`, la cuenta de inactividad. |
| `maquina-estados.md`, `bus-eventos.md`, `enrutador-intenciones.md`, `sintetizador.md`, `proceso.md`, `configuracion.md` | Se ajustan a la sección 6. |
| `hud.md`, `Interfaz/README.md` | Ventana visible en dormido; caja de texto en la pantalla de sesión y en el HUD; el orbe reacciona solo a la voz del asistente; desaparece el estado de micrófono no disponible. |
| `arquitectura.md`, `contexto.md`, `README.md`, `restricciones.md`, `reglas-negocio.md`, `Requisitos/*.md`, `catalogo-intenciones.md` | Se sustituye la entrada por voz por la escrita; hilos, dependencias y modelos actualizados. |
| `plan-implementacion.md` | La fase 1 pasa a ser «Ciclo de vida por texto»; se retiran las tareas y riesgos de captura y transcripción. |
| `CasosUso/` y `Modulos/Accion/` | Donde digan «el usuario dice», pasa a «el usuario escribe». |
| `BaseDatos/especificacion-base-datos.md` | Motivo de cierre `'orden'`. |

**Conflicto que resuelve este diseño.** `hud.md` dice que el HUD flotante «nunca toma el foco».
Con órdenes escritas, el HUD necesita una caja. Regla nueva: el HUD nunca roba el foco por su
cuenta; lo toma solo cuando el usuario hace clic en su caja.

## 8. Decisiones tomadas por quien escribe este diseño

El propietario no las ha decidido expresamente; puede cambiarlas al revisar.

1. Teclear reinicia la cuenta de inactividad, no solo enviar.
2. La ventana se muestra al arrancar, también cuando el proceso arranca con el inicio de sesión de
   Windows.
3. Cerrar con ✕ oculta la ventana y deja el proceso en la bandeja.
4. Se acepta «jarvis» a secas como frase de activación, además de «hey jarvis».
5. El motivo de cierre `'voz'` se renombra a `'orden'` con una migración.
6. La clave de inactividad se traslada a `[input] inactivity_to_idle_seconds`.
7. Para escribir una orden mientras se trabaja en otra aplicación hay que volver a la ventana de
   Jarvis (Alt+Tab, barra de tareas o bandeja). El atajo global queda fuera.
8. En el HUD futuro, la caja toma el foco solo con un clic.
9. Se borran también los audios de prueba y `make_fixture_audio.py`.

## 9. Lo que queda a quien lo construya

- El orden de los pasos, siempre que la batería de pruebas pase al final de cada uno.
- Los nombres internos no fijados aquí.
- Comprobar si `onnxruntime` y `numpy` siguen haciendo falta como dependencias directas.
- Qué partes de `tests/fakes/voice.py`, `tests/hardware/` y `tests/models/` sobreviven por
  pertenecer a la voz de salida.
- El detalle de la migración `0002` en SQLite.
- La redacción exacta de cada documento de `software/`.
