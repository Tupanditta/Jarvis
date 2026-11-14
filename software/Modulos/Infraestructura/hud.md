# Interfaz HUD

- **Código:** `ui/`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md) · diseño visual en [Interfaz/README.md](../../Interfaz/README.md).

## Propósito

Mostrar al usuario el estado del asistente y de sus tareas sin interrumpir su trabajo. Este documento define el comportamiento y la estructura técnica; el aspecto está en [Interfaz/README.md](../../Interfaz/README.md).

## 1. Superficies

| Superficie | Qué es | Foco |
|---|---|---|
| **Pantalla de sesión** | Ventana a pantalla completa en el monitor principal: el orbe en el centro, la actividad de la sesión a la izquierda y el panel activo a la derecha (RF-82). | Pasa al frente y pide el foco solo al abrir la sesión. No queda siempre encima. |
| **HUD flotante** | Ventana compacta en una esquina ⚙ del monitor principal: mini orbe, estado, subtítulos y el panel activo (RF-87). | Siempre encima, sin bordes, fondo translúcido, **nunca toma el foco** (RNF-13). Sus botones responden al clic sin activar la ventana. |
| **Icono de la bandeja** | Estado y menú ([proceso.md](proceso.md), RF-86). | — |

Las dos ventanas usan los mismos componentes QML de panel y los mismos modelos de datos: un panel se construye una vez y se muestra en ambas.

## 2. Qué se muestra y cuándo

Lógica pura en `ui/window_controller.py`, probada sin Qt. Entradas: los eventos del ciclo de vida, si la pantalla de sesión es la ventana activa, y las peticiones de mostrar u ocultar.

| Situación | Pantalla de sesión | HUD flotante |
|---|---|---|
| Dormido | Oculta | Oculto |
| `SessionOpened` | Se muestra a pantalla completa, pasa al frente, pide el foco; animación de despertar | Oculto |
| Sesión abierta y la pantalla es la ventana activa | Visible | Oculto |
| Sesión abierta y la pantalla no es la ventana activa (el usuario pasó a otra ventana, se abrió una aplicación, o la pantalla está minimizada) | Queda detrás, sin cambios | Visible |
| `ListeningResumed` con la pantalla activa | Animación de despertar | Oculto |
| `ListeningResumed` con la pantalla no activa | Sin cambios. Con ⚙ `ui.wake_brings_screen_to_front = true`: pasa al frente y pide el foco | Animación de despertar en el mini orbe |
| `RestEntered` | Animación de dormirse; sigue visible | Animación de dormirse en el mini orbe; después se contrae |
| «Muestra la pantalla» o menú de la bandeja | Pasa al frente y pide el foco | Se oculta |
| «Oculta la pantalla» | Se minimiza | Visible |
| `SessionClosed` | Animación de dormirse; al terminar (2 s) se oculta | Igual |
| `SessionOpened` durante la animación de cierre | No se oculta: la animación de dormirse se funde con la de despertar (RF-01) | — |

**Pasar al frente** (`os_adapters`): la ventana se marca como superior, se muestra y, pasado 1 s, se le quita la marca. Así queda delante aunque Windows no conceda el foco; el foco se pide con `requestActivate()` y no se fuerza.

**HUD contraído.** El HUD tiene dos alturas: contraído (cabecera con el mini orbe, el estado y los subtítulos) y expandido (cabecera y panel activo). Se expande con cualquier evento de tarea, diálogo, aviso o panel; se contrae tras 8 s ⚙ sin eventos, siempre que no haya un diálogo abierto ni una tarea `pendiente`. No se arrastra: su esquina se elige en la configuración.

**Cursor.** Sobre la pantalla de sesión, el cursor se oculta tras 2 s sin moverse y reaparece al moverlo.

## 3. Paneles

Cada panel es un componente QML en `ui/qml/panels/` alimentado por un modelo. El **panel activo** es el último que recibió `PanelActivated`; es el que se ve en el HUD y en la columna derecha de la pantalla de sesión.

| Panel | Contenido | Eventos |
|---|---|---|
| Actividad | Las tareas de la sesión, la más reciente arriba, con módulo, descripción, estado y hora. Siempre visible en la columna izquierda de la pantalla de sesión; en el HUD, es el panel por defecto. | `TaskUpdated` |
| Diálogo | La pregunta en curso, las respuestas admitidas, el elemento sobre el que se pregunta y una barra con el tiempo restante. Se superpone al panel activo mientras dura. | `DialogueOpened`, `DialogueClosed` |
| Comandos | Directorio de trabajo, y debajo el último resultado: listado de `ls`, árbol, o salida de un binario. `clear` lo vacía. | `WorkdirChanged`, `DirectoryListed`, `DirectoryTreeBuilt`, `CommandOutputAppended`, `CommandPanelCleared` |
| Aperturas | Una tarjeta por elemento abierto, con su estado y el botón «traer al frente». | `OpenedItemsChanged` |
| Búsqueda | Resultados numerados con nombre, tipo y ruta. | `SearchResultsReady` |
| Recordatorios | Lista numerada (1…n) con texto, estado, próximo aviso y fecha límite; el recordatorio notificado o leído aparece destacado. | `RemindersChanged` |
| Protocolo | Nombre del protocolo y sus tareas con estado, con una barra de progreso. | `ProtocolStarted`, `TaskUpdated` con `parent_id`, `ProtocolFinished` |
| Historial | Tabla de sesiones (identificador, nombre, fecha, importancia) o actividades de una sesión. | `HistoryShown`, `SessionActivitiesShown` |
| Ayuda | Órdenes disponibles agrupadas por módulo, con un ejemplo. | `HelpShown`, `ProtocolsListed` |

**Activar un panel** (p. ej. el de recordatorios, RF-44) es convertirlo en el panel activo y expandir el HUD. No implica foco del sistema.

**Interacción con el ratón.** Solo tres controles: «traer al frente» en cada tarjeta de apertura, el botón de silencio mientras el asistente habla, y el botón de expandir o contraer el HUD. Todo lo demás se maneja por voz.

## 4. Elementos comunes

- **Estado del asistente:** texto y color según la actividad (dormido, reposo, escuchando, procesando, hablando, esperando).
- **Subtítulos (RF-89):** última orden transcrita (atenuada y con la marca «no reconocido» cuando lo es) y última respuesta del asistente.
- **Sesión:** nombre, y un distintivo si es importante.
- **Micrófono no disponible:** distintivo visible en la cabecera.

## 5. Estructura técnica

```text
Bus (hilo del núcleo) ──► UiBridge (señales Qt en cola) ──► modelos de vista (hilo UI) ──► QML
QML (clic) ──► modelo de vista ──► bus.publish_threadsafe(acción del usuario)
```

- **`UiBridge`** (`ui/bridge.py`): se suscribe a los eventos del bus y emite una señal por tipo. Es el único punto de contacto con el backend. Para `AudioLevel`, solo conserva el último valor pendiente.
- **Modelos de vista** (`ui/view_models.py`): objetos `QObject` con propiedades y `QAbstractListModel` para las listas, registrados como propiedades de contexto de QML: `assistant` (estado, actividad, sesión, nivel y origen del audio, subtítulos, micrófono), `tasks`, `dialogue`, y uno por panel.
- **QML:** declarativo, sin lógica de negocio. Las animaciones usan los tipos de animación de Qt Quick; no hay código Python por frame.
- **Tema:** todos los colores, tamaños, tipografías y duraciones salen del singleton `Theme.qml` ([Interfaz/README.md](../../Interfaz/README.md)).
- **Ventanas:** se crean ocultas al arrancar el proceso, para que la apertura sea inmediata. El HUD usa los indicadores `Tool`, `FramelessWindowHint`, `WindowStaysOnTopHint` y `WindowDoesNotAcceptFocus`.
- **Consumo:** Qt Quick no dibuja una ventana oculta o tapada. En el HUD, en reposo, no hay ninguna animación continua.
- **Vista previa:** `python -m jarvis_assistant --preview` abre la interfaz con una secuencia de eventos simulados, sin audio ni modelos, para construir y revisar el aspecto. `--ui-debug` añade un contador de frames.

## Criterios de aceptación

- `window_controller`: cada fila de la tabla de la sección 2, con pruebas unitarias.
- Todo el QML se carga sin errores ni avisos en modo sin pantalla (prueba de integración).
- Cada modelo de vista refleja sus eventos (pruebas con `pytest-qt`).
- Manual: el HUD no toma el foco al aparecer, al actualizarse ni al hacer clic (RNF-13); la lista visual de [Interfaz/README.md](../../Interfaz/README.md).

## Prohibiciones

- Prohibido robar el foco a la aplicación que el usuario está usando o a las que abre el asistente. Única excepción: la pantalla de sesión al abrir la sesión.
- Prohibido mostrar ventanas en modo dormido.
- Prohibido usar estados de tarea distintos de `pendiente`, `error` y `completado`.
- Prohibido que la interfaz llame a módulos de acción, lea la base de datos o contenga reglas de negocio.
