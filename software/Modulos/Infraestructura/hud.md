# Interfaz HUD

- **Código:** `ui/`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md) · diseño visual en [Interfaz/README.md](../../Interfaz/README.md).

## Propósito

Mostrar al usuario el estado del asistente y de sus tareas sin interrumpir su trabajo, y recibir las órdenes que escribe. Este documento define el comportamiento y la estructura técnica; el aspecto está en [Interfaz/README.md](../../Interfaz/README.md).

## 1. Superficies

| Superficie | Qué es | Foco |
|---|---|---|
| **Pantalla de sesión** | Ventana a pantalla completa en el monitor principal: el orbe en el centro, las ventanas flotantes de los módulos, el selector de ventanas y la caja de texto ([entrada-texto.md](entrada-texto.md)). Dónde va cada cosa lo dice la plantilla del perfil (sección 2.1). Dormida, encima de la caja, el selector de perfiles. | Pasa al frente y pide el foco al arrancar, al abrir la sesión y con «Mostrar pantalla». El foco queda en la caja. No queda siempre encima. |
| **HUD flotante** | Ventana compacta en una esquina ⚙ del monitor principal: mini orbe, estado, subtítulos, el panel activo (RF-87) y una caja de texto. | Siempre encima, sin bordes, fondo translúcido, **nunca toma el foco por su cuenta** (RNF-13): solo lo toma cuando el usuario hace clic en su caja de texto. Sus botones responden al clic sin activar la ventana. |
| **Icono de la bandeja** | Estado y menú ([proceso.md](proceso.md), RF-86). | — |

Las dos ventanas usan los mismos componentes QML de panel y los mismos modelos de datos: un panel se construye una vez y se muestra en ambas.

## 2. Qué se muestra y cuándo

Lógica pura en `ui/window_controller.py`, probada sin Qt. Entradas: los eventos del ciclo de vida, si la pantalla de sesión es la ventana activa, y las peticiones de mostrar u ocultar.

| Situación | Pantalla de sesión | HUD flotante |
|---|---|---|
| Arranque y dormido | Visible en su aspecto de dormido: fondo oscuro, orbe apagado y la caja de texto con el foco | Oculto |
| `SessionOpened` | Pasa al frente y pide el foco para la caja; animación de despertar | Oculto |
| Sesión abierta y la pantalla es la ventana activa | Visible | Oculto |
| Sesión abierta y la pantalla no es la ventana activa (el usuario pasó a otra ventana, se abrió una aplicación, o la pantalla está minimizada) | Queda detrás, sin cambios | Visible |
| `ListeningResumed` con la pantalla activa | Animación de despertar | Oculto |
| `ListeningResumed` con la pantalla no activa | Sin cambios | Animación de despertar en el mini orbe |
| `RestEntered` | Animación de dormirse; sigue visible | Animación de dormirse en el mini orbe; después se contrae |
| «Muestra la pantalla» o menú de la bandeja | Pasa al frente y pide el foco para la caja | Se oculta |
| «Oculta la pantalla» | Se minimiza | Visible |
| El usuario cierra la ventana (✕) | Se oculta; el proceso sigue en la bandeja | Visible si hay sesión |
| `SessionClosed` | Animación de dormirse; al terminar (2 s) queda en su aspecto de dormido, visible | Animación de dormirse; al terminar se oculta |
| `SessionOpened` durante la animación de cierre | La animación de dormirse se funde con la de despertar (RF-01) | — |

**Pasar al frente** (`os_adapters`): la ventana se marca como superior, se muestra y, pasado 1 s, se le quita la marca. Así queda delante aunque Windows no conceda el foco; el foco se pide con `requestActivate()` y no se fuerza.

**HUD contraído.** El HUD tiene dos alturas: contraído (cabecera con el mini orbe, el estado y los subtítulos) y expandido (cabecera y panel activo). Se expande con cualquier evento de tarea, diálogo, aviso o panel; se contrae tras 8 s ⚙ sin eventos, siempre que no haya un diálogo abierto ni una tarea `pendiente`. No se arrastra: su esquina se elige en la configuración.

**Cursor.** Sobre la pantalla de sesión, el cursor se oculta tras 2 s sin moverse y reaparece al moverlo.

### 2.1 Plantillas y perfiles

- **Plantilla** (`config.ScreenLayout`, `layouts.toml`): qué ventanas flotantes están abiertas al abrir sesión, su posición y tamaño, el centro del selector de ventanas y el centro y el ancho de la caja de texto. Todo en fracciones de la pantalla. Una ventana que la plantilla no nombra toma su disposición de fábrica (`WINDOWS`, `ui/workspace.py`). La plantilla de fábrica es la disposición de `WINDOWS` con el selector arriba y la caja abajo, centrados.
- **Al abrir sesión**, `WorkspaceModel` toma la plantilla del perfil con el que se abrió (`SessionOpened.profile_id`). Solo cambia los datos de las filas (`dataChanged`), sin reiniciar el modelo: QML conserva las ventanas en lugar de recrearlas. Los paneles se cargan de forma asíncrona (`Loader.asynchronous`) para no frenar la animación de despertar. Durante la sesión las ventanas se mueven libremente; eso no cambia la plantilla. El botón «Restablecer disposición» del selector vuelve a la plantilla. La disposición no se recuerda entre sesiones: cada sesión empieza en la plantilla.
- **Dormida**, la pantalla toma la plantilla del perfil elegido, así la caja de texto ya está donde estará en la sesión.
- **Pantalla dormida:** en el centro, bajo el orbe, el selector de perfiles. Encima de la caja de texto (debajo si la caja está en la mitad de arriba), el botón «Configuración», que abre la ventana de configuración ([configurador.md](configurador.md)). Es el único sitio desde el que se configura. Con la ventana abierta, el botón dice «Configuración abierta» y la caja de texto está desactivada: no se puede iniciar sesión.
- **Selector de perfiles** (`ProfilePicker.qml`, `ui/profiles.py`): solo en `DORMIDO` y solo con dos perfiles o más. Una fila de botones en el centro de la pantalla, bajo el orbe, con el elegido resaltado. Se cambia con el ratón o con ←/→ con la caja vacía. Cada cambio publica `ProfileSelected`; el núcleo abre la siguiente sesión con ese perfil. Viene elegido el perfil con el que se abrió la última sesión (`perfil.json` en la carpeta de datos); si ya no existe, el primero.
- **Subtítulos**: siguen a la caja de texto, encima o debajo según su altura.

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

**Interacción con el ratón.** Solo tres controles: «traer al frente» en cada tarjeta de apertura, el botón de silencio mientras el asistente habla, el botón de expandir o contraer el HUD, el de abrir la pantalla de sesión (la trae al frente y oculta el HUD) y el de ocultar el HUD. Todo lo demás se maneja escribiendo en la caja de texto; no hay botones de órdenes.

## 4. Elementos comunes

- **Estado del asistente:** texto y color según la actividad (dormido, reposo, escuchando, procesando, hablando, esperando).
- **Subtítulos (RF-89):** última orden escrita (atenuada y con la marca «no reconocido» cuando lo es) y última respuesta del asistente. Las frases que solo cambian el estado (activación, «Jarvis» en reposo, reposo y cierre) no se muestran, ni tampoco las frases del ciclo de vida con las que responde el asistente: al sonar una, los subtítulos anteriores se retiran.
- **Sesión:** nombre, y un distintivo si es importante.
- **Caja de texto:** una línea, con el texto de ayuda que corresponde al estado ([entrada-texto.md](entrada-texto.md)).

## 5. Estructura técnica

```text
Bus (hilo del núcleo) ──► UiBridge (señales Qt en cola) ──► modelos de vista (hilo UI) ──► QML
QML (clic, texto enviado) ──► modelo de vista ──► bus.publish_threadsafe(acción del usuario)
```

- **`UiBridge`** (`ui/bridge.py`): se suscribe a los eventos del bus y emite una señal por tipo. Es el único punto de contacto con el backend. Para `AudioLevel`, solo conserva el último valor pendiente.
- **Modelos de vista** (`ui/view_models.py`): objetos `QObject` con propiedades y `QAbstractListModel` para las listas, registrados como propiedades de contexto de QML: `assistant` (estado, actividad, sesión, nivel de la voz del asistente, subtítulos), `tasks`, `dialogue`, `workspace` (ventanas flotantes y barras), `profiles` (selector de perfiles), `ui` (opciones y sonido) y uno por panel.
- **Configuración aplicada:** el núcleo publica `ConfigApplied` al arrancar, al abrir sesión y al guardar desde la ventana de configuración con la sesión cerrada. De ahí toma la interfaz los perfiles, las plantillas y si suena el aviso de las ventanas (`sound.enabled`).
- **QML:** declarativo, sin lógica de negocio. Las animaciones usan los tipos de animación de Qt Quick; no hay código Python por frame.
- **Tema:** todos los colores, tamaños, tipografías y duraciones salen del singleton `Theme.qml` ([Interfaz/README.md](../../Interfaz/README.md)).
- **Ventanas:** se crean al arrancar el proceso; la pantalla de sesión se muestra y el HUD queda oculto. El HUD usa los indicadores `Tool`, `FramelessWindowHint` y `WindowStaysOnTopHint`, y no se activa al mostrarse ni al actualizarse; solo acepta el foco con un clic en su caja de texto.
- **Consumo:** Qt Quick no dibuja una ventana oculta o tapada. En el HUD, en reposo, no hay ninguna animación continua.
- **Vista previa:** `python -m jarvis_assistant --preview` abre la interfaz con una secuencia de eventos simulados, sin voz ni modelos, para construir y revisar el aspecto. `--ui-debug` añade un contador de frames.

## Criterios de aceptación

- `window_controller`: cada fila de la tabla de la sección 2, con pruebas unitarias.
- Todo el QML se carga sin errores ni avisos en modo sin pantalla (prueba de integración).
- Cada modelo de vista refleja sus eventos (pruebas con `pytest-qt`).
- Manual: el HUD no toma el foco al aparecer, al actualizarse ni al hacer clic en sus botones; sí al hacer clic en su caja de texto (RNF-13); la lista visual de [Interfaz/README.md](../../Interfaz/README.md).

## Prohibiciones

- Prohibido robar el foco a la aplicación que el usuario está usando o a las que abre el asistente. Excepciones: la pantalla de sesión al arrancar, al abrir la sesión y con «Mostrar pantalla»; y el HUD cuando el usuario hace clic en su caja de texto.
- Prohibido mostrar el HUD flotante en modo dormido.
- Prohibido usar estados de tarea distintos de `pendiente`, `error` y `completado`.
- Prohibido que la interfaz llame a módulos de acción, lea la base de datos o contenga reglas de negocio.
