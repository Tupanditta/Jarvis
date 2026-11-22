# Ventana de configuración — diseño

Estado: implementado, con un cambio posterior en el acceso: la ventana solo se abre desde el
botón «Configuración» de la pantalla dormida (no desde la bandeja), bloquea el inicio de sesión
mientras está abierta y se destruye al cerrarla. Documento del módulo: [configurador.md](../../../software/Modulos/Infraestructura/configurador.md).

## Intención

Que cualquier usuario cambie el funcionamiento del asistente desde una ventana, con el ratón,
sin editar archivos ni tocar el código. La ventana no habla con el asistente: no se le dan
órdenes ni responde; solo edita la configuración, y el asistente la lee como hasta ahora.

Primera versión: plantillas de pantalla, sonido, perfiles y alta manual de aplicaciones y
páginas web, con un único botón **Guardar** y la posibilidad de salir sin guardar. La estructura
debe admitir más apartados sin rehacer lo existente.

## Objetivos

1. **Plantillas de pantalla.** Crear, editar, renombrar, duplicar y eliminar disposiciones de la
   pantalla de sesión: qué ventanas flotantes se muestran al abrir sesión, su posición y tamaño,
   y la posición de la barra superior (selector de ventanas) y la inferior (caja de texto).
2. **Sonido.** Activar o desactivar el sonido del asistente.
3. **Perfiles.** Cada perfil dice el nombre del usuario (el que usa «preséntate») y qué
   plantilla usa por defecto. El perfil se elige en la pantalla dormida, justo encima de la caja donde se escribe
   «Hey Jarvis».
4. **Aplicaciones y páginas.** Añadir, editar y eliminar a mano entradas del catálogo, eligiendo
   primero si es una aplicación o una página web.
5. **Guardar y cancelar.** Nada queda registrado hasta pulsar **Guardar**. Salir sin guardar
   descarta todo lo cambiado desde el último guardado.

## No objetivos

- Editar desde la ventana el resto de ajustes (umbrales, lugares, binarios, protocolos,
  estructuras, alias). Quedan en sus archivos TOML; ver «Ideas para más adelante».
- Cambiar de perfil con la sesión abierta.
- Aplicar los cambios a la sesión en curso. Se aplican al abrir la siguiente sesión.
- Cambiar las frases del asistente: siguen diciendo «señor» en todos los perfiles.

## Antiobjetivos

- Que guardar destruya los comentarios que explican cada clave en los archivos TOML.
- Que la ventana de configuración dependa del núcleo, o el núcleo de ella.
- Que añadir un apartado nuevo obligue a tocar los apartados existentes.
- Que una plantilla guardada deje la pantalla de sesión sin barra superior o sin caja de texto.

## Restricciones

- Se mantiene el formato TOML en `%APPDATA%\Jarvis\config\` ([configuracion.md](../../../software/Modulos/Infraestructura/configuracion.md)).
- **Cambia la regla de solo lectura (RES-33, RES-36).** Nueva redacción: «El asistente solo lee
  la configuración. El único que la escribe es la ventana de configuración, y solo al pulsar
  Guardar.» Actualizar `restricciones.md`, `configuracion.md` y su sección «Prohibiciones».
- La escritura conserva comentarios, orden y formato: se usa `tomlkit` (dependencia nueva,
  instalada en `implementation/.venv`). La lectura sigue con `tomllib`.
- Datos de ejemplo inventados («Jane Doe»), nunca datos reales.
- Mismo sistema de diseño ([Interfaz/README.md](../../../software/Interfaz/README.md)): tokens de
  `Theme.qml`, sin colores ni tamaños propios.

## Enfoques

**Cómo se editan las plantillas** (elegido por el autor):

- **Elegido: lienzo inerte a pantalla completa.** El botón «+» abre una pantalla con el mismo
  aspecto que la de sesión, pero que no hace nada: no hay asistente, no se pueden escribir
  órdenes y las ventanas no tienen datos. Solo se mueven y se redimensionan las ventanas y las
  dos barras. Lo que se ve es exactamente lo que quedará.
- Descartado: miniatura dentro de la ventana de configuración. Es menos fiel al tamaño real y
  obliga a dibujar otra versión reducida de cada componente.
- Descartado: formulario de coordenadas. Es incómodo y no se ve el resultado.

**Dónde vive la ventana** (decisión del diseño, se puede corregir):

- **Elegido: una ventana más del mismo proceso, en un paquete propio (`configurator/`).**
  Reutiliza Qt, `Theme.qml` y los componentes QML existentes. Al guardar, la pantalla dormida ve
  enseguida los perfiles nuevos. El paquete depende de `config` y de los componentes de `ui`;
  nadie depende de él.
- Descartado: un programa aparte. Duplicaría el arranque de Qt y la instancia única, y haría
  falta un aviso entre procesos para refrescar el selector de perfiles.
- Descartado: meterla dentro de `ui/`. Mezclaría la interfaz del asistente con la de edición, y
  `ui/` crecería con cada apartado.

## Diseño

### 1. Acceso

- Entrada **«Configuración…»** en el menú de la bandeja, visible solo en `DORMIDO` (como «Abrir
  sesión»). Así no se editan plantillas o perfiles mientras están en uso. La entrada que abría la
  carpeta pasa a llamarse «Abrir carpeta de configuración».
- Si se abre la sesión con la configuración abierta, la ventana sigue abierta y lo que se guarde
  se aplica en la sesión siguiente.
- Solo hay una ventana de configuración: si ya está abierta, la entrada del menú la trae al
  frente.

### 2. La ventana

Ventana normal con bordes, de unos 900 × 600 px lógicos. Tiene una columna de apartados a la
izquierda y el contenido del apartado a la derecha. Abajo a la derecha, **Cancelar** y
**Guardar**.

```
┌ Configuración ● ───────────────────────────────────────────────┐
│ Plantillas    │  Plantillas de pantalla                   [ + ] │
│ Perfiles      │  ┌──────────────────────────────────────────┐   │
│ Sonido        │  │ Fábrica          (predeterminada)         │   │
│ Aplicaciones  │  │ Estudio          ✎  ⧉  🗑                 │   │
│               │  │ Programar        ✎  ⧉  🗑                 │   │
│               │  └──────────────────────────────────────────┘   │
│               │                          [Cancelar] [Guardar]   │
└────────────────────────────────────────────────────────────────┘
```

- El punto ● del título y el botón **Guardar** activo indican que hay cambios sin guardar.
- Cerrar la ventana (✕, Esc o **Cancelar**) con cambios pendientes muestra, dentro de la propia
  ventana, «Hay cambios sin guardar» con **Salir sin guardar** y **Seguir editando**. Sin
  cambios pendientes, se cierra directamente.

### 3. Borrador, validación y guardado

- Al abrirse, la ventana carga la configuración en un **borrador**: una copia en memoria de los
  documentos editables. Todo lo que hace el usuario cambia solo el borrador.
- **Guardar:**
  1. Valida el borrador completo con las mismas reglas que el cargador. Si hay errores, no
     escribe nada: marca el apartado y el campo erróneos y muestra el motivo.
  2. Escribe solo los archivos que han cambiado. Cada uno se escribe en un temporal del mismo
     directorio y luego se sustituye (`os.replace`). Si falla alguno, se informa de cuál; los
     archivos ya sustituidos quedan bien formados.
  3. Publica `ConfigSaved`. El núcleo recarga la configuración, igual que al abrir sesión
     (RF-96), y la pantalla dormida refresca el selector de perfiles.
  4. El borrador pasa a ser el nuevo estado guardado: desaparece el ●.
- **Cancelar o salir sin guardar** descarta el borrador. No se toca ningún archivo.

### 4. Plantillas de pantalla

**Qué es una plantilla.** Un nombre y la disposición inicial de la pantalla de sesión:

- para **cada** ventana flotante del registro `WINDOWS` (`ui/workspace.py`): si se muestra al
  abrir sesión, su posición, su tamaño y su orden de apilado;
- la posición de la **barra superior** (`Dock`, el selector de ventanas): solo se mueve, porque
  su tamaño lo dan sus botones;
- la posición y el ancho de la **barra inferior** (`CommandInput`, la caja de texto). Los
  subtítulos van pegados encima de ella, como hoy.

Todo en fracciones del área de la pantalla, como ya hace `workspace.py`, para que valga en
cualquier resolución. El orbe no forma parte de la plantilla: sigue en el centro.

**Plantilla de fábrica.** Es la disposición actual de `WINDOWS`, con las barras donde están
hoy. Siempre existe, no se puede editar ni eliminar y es la que usa un perfil sin plantilla.
Sí se puede duplicar, como punto de partida.

**Apartado Plantillas.** Una lista con un botón **+** y, en cada plantilla, editar (✎),
duplicar (⧉) y eliminar (🗑). Al eliminar una plantilla que usa algún perfil, se pide
confirmación dentro de la ventana y esos perfiles pasan a la de fábrica.

**Editor (lienzo inerte).** Se abre con **+** (parte de la plantilla de fábrica) o con ✎:

- Ocupa toda la pantalla del monitor principal, con el fondo y el orbe de la pantalla de sesión
  quietos: sin animación continua, con el aspecto de dormido.
- Muestra las ventanas marcadas como visibles, con su marco (`FloatingWindow`), su título y su
  icono, y con el contenido vacío (`EmptyState`). Se arrastran y se redimensionan como en la
  sesión, con los mismos tamaños mínimos.
- Las dos barras siempre están. Se arrastran; la caja de texto además cambia de ancho (mínimo
  300 px). No responden a nada más: la caja no admite texto y los botones del selector no
  abren ventanas.
- Una paleta flotante y arrastrable reúne los controles de edición:
  - el **nombre** de la plantilla (obligatorio y único);
  - una casilla por ventana: **mostrar al abrir sesión** sí o no. Una ventana desmarcada
    desaparece del lienzo pero conserva su posición; si en la sesión su módulo la abre, sale
    ahí;
  - **Restablecer** (vuelve a la disposición de fábrica), **Aceptar** y **Cancelar** (o Esc).
- **Aceptar** cierra el editor y deja la plantilla en el borrador. Solo queda registrada al
  pulsar **Guardar** en la ventana de configuración.
- Ninguna barra puede quedar fuera de la pantalla, y las barras no pueden taparse entre sí. Al
  soltar una barra en una posición inválida, vuelve a la última válida.

**Uso en la sesión.**

- Al abrir sesión, la pantalla toma la plantilla del perfil elegido. Durante la sesión, el
  usuario sigue moviendo las ventanas libremente; eso no cambia la plantilla.
- El botón del selector que hoy «devuelve todas a su disposición inicial» vuelve a la plantilla
  del perfil.
- **Decisión del diseño:** la disposición deja de recordarse entre sesiones. Cada sesión empieza
  en la plantilla, y `LayoutStore` (`ventanas.json`) se retira. Mantener las dos cosas daría dos
  puntos de partida distintos y confusos.
- `SessionScreen.qml` deja de anclar el `Workspace` a la caja de texto (hoy `height` depende de
  `input.y`). El área de trabajo pasa a ser toda la pantalla menos el margen, y las pestañas de
  ventanas apartadas reservan el hueco de las dos barras donde estén.

**Compatibilidad hacia delante.** Una ventana que la plantilla no nombra (un módulo nuevo) toma
su disposición de fábrica. Un nombre de ventana que ya no existe se ignora con un aviso en el
registro.

### 5. Perfiles

**Qué es un perfil:**

| Campo | Significado |
|---|---|
| `name` | Nombre del perfil en el selector («Trabajo», «Casa»). Obligatorio y único. |
| `user_name` | Nombre del usuario para «preséntate». Vacío: no lo dice. Sustituye a `user.name`. |
| `layout` | Plantilla predeterminada. Vacío: la de fábrica. |

**Apartado Perfiles.** Una lista con **+**, editar, duplicar y eliminar. Un formulario con los
tres campos; la plantilla se elige de una lista desplegable con las plantillas del borrador.
Siempre queda al menos un perfil: el último no se puede eliminar.

**Frases.** No cambian: el asistente sigue diciendo «señor» en todos los perfiles. El perfil solo
aporta el nombre de «preséntate».

**Selector en la pantalla dormida:**

- Solo en `DORMIDO`, justo encima de la caja de texto. Desaparece con la animación de despertar
  y vuelve con la de dormirse.
- Es una fila de chips (`Chip.qml`), uno por perfil, con el elegido resaltado en `primary`. Se
  cambia con el ratón o con ←/→ con la caja vacía; el foco no sale de la caja.
- Solo aparece si hay dos perfiles o más. Con uno, no se ve nada nuevo.
- Viene elegido el **último perfil usado**. Si ya no existe, se elige el primero de la lista. El
  último usado no es configuración: se guarda en la carpeta de datos (`perfil.json`).
- «Hey Jarvis» y «Abrir sesión» en la bandeja abren la sesión con el perfil elegido. Nada más
  cambia en la activación.
- `SessionOpened` lleva el id del perfil. El orquestador y la pantalla de sesión leen de ahí el
  nombre y la plantilla.

**Migración.** Si no existe `profiles.toml`, se crea en memoria un perfil «Predeterminado» con
`user_name = user.name`. El archivo solo se escribe la primera vez que se
guarda desde la ventana. `user.name` queda obsoleto: se sigue leyendo y se documenta así.

### 6. Sonido

- Una casilla: **Sonido del asistente**, activada por defecto. Clave `sound.enabled` en
  `settings.toml`.
- Desactivada, el asistente no reproduce la voz ni el aviso de las ventanas al aparecer. Los
  subtítulos siguen mostrándose igual.
- La secuencia de estados no cambia: el altavoz da cada locución por terminada al momento, así
  que la FSM y la cola de tareas no saben si sonó o no.
- Es un ajuste global, no de cada perfil (ver «Ideas»).

### 7. Aplicaciones y páginas

**Apartado Aplicaciones.** Lista de las entradas manuales de `catalog.toml`, con un icono que
indica si es aplicación o página. Las descubiertas en el menú Inicio no aparecen ni se editan.
Botón **+**: primero se elige **Aplicación** o **Página web**, y luego aparece su formulario.

| Aplicación | Página web |
|---|---|
| Nombre (obligatorio) | Nombre (obligatorio) |
| Ruta: ejecutable, acceso directo o nombre en el PATH, con botón **Examinar…** (`.exe`, `.lnk`) | URL (obligatoria, `http://` o `https://`) |
| Argumentos (opcional, uno por línea) | — |
| Alias (opcional, uno por línea) | Alias (opcional, uno por línea) |

- El nombre y los alias no pueden repetir los de otra entrada manual, sin distinguir mayúsculas
  ni tildes. Una coincidencia con una aplicación descubierta solo produce un aviso, porque la
  manual tiene prioridad.
- Una ruta que no existe en disco solo produce un aviso, no un error: puede ser un nombre del
  PATH.
- Editar y eliminar desde la lista.

### 8. Estructura de módulos

```
jarvis_assistant/
├── config/                    # antes config.py: un módulo por archivo de configuración
│   ├── __init__.py            # Config, load() — misma interfaz pública que hoy
│   ├── settings.py            # settings.toml (+ SoundSettings)
│   ├── catalog.py             # catalog.toml
│   ├── profiles.py            # profiles.toml  (nuevo)
│   ├── layouts.py             # layouts.toml   (nuevo)
│   ├── …                      # places, commands, aliases, protocols, structures
│   └── writer.py              # escritura atómica con tomlkit (solo la usa configurator)
├── configurator/              # nuevo: la ventana de configuración
│   ├── window.py              # ConfigWindow: ventana, borrador, Guardar/Cancelar
│   ├── draft.py               # Draft: documentos tomlkit en memoria, ¿hay cambios?, validar
│   ├── sections.py            # registro SECTIONS
│   ├── sections/              # un archivo por apartado: modelo de vista + validación
│   │   ├── layouts.py
│   │   ├── profiles.py
│   │   ├── sound.py
│   │   └── catalog.py
│   └── qml/
│       ├── ConfigWindow.qml
│       ├── LayoutEditor.qml   # lienzo inerte
│       └── sections/          # una página QML por apartado
└── ui/
    ├── workspace.py           # WINDOWS sigue siendo el registro de ventanas
    └── qml/components/ProfilePicker.qml   # nuevo, en la pantalla dormida
```

- **Registro de apartados.** Igual que `WINDOWS` declara las ventanas, `SECTIONS` declara los
  apartados: `SectionSpec(id, title, icon, page_qml, model_factory)`. Cada modelo implementa un
  protocolo común:
  - `load(draft)`: lee su parte del borrador;
  - `validate() -> list[FieldError]`;
  - `apply(draft)`: escribe su parte en el borrador;
  - `dirty`: si tiene cambios.

  **Añadir un apartado** es añadir su `SectionSpec`, su modelo y su página QML.
- **Un esquema por archivo.** Cada módulo de `config/` define sus `dataclass`, cómo se leen
  (`parse`) y cómo se vuelcan sobre un documento `tomlkit` (`dump`). El cargador del asistente y
  el validador del borrador usan el mismo `parse`: una sola fuente de reglas.
- **Dependencias en un solo sentido:** `configurator → config, ui/qml/components`;
  `core, ui → config`. Ni `core` ni `ui` importan `configurator`, y `configurator` solo importa
  de `core` los tipos de eventos. `ConfigWindow` recibe una función `on_saved`. Quien monta la aplicación (`process/`)
  le pasa una que publica `ConfigSaved` en el bus.
- **Componentes compartidos.** `FloatingWindow`, `Dock` y `CommandInput` admiten una propiedad
  `inert: bool`. En modo inerte se pueden mover y redimensionar, pero no ejecutan nada. El
  editor y la pantalla de sesión dibujan con el mismo código.

### 9. Archivos nuevos

`profiles.toml`:

```toml
[[profiles]]
id = "trabajo"            # generado por la ventana, estable al renombrar
name = "Trabajo"
user_name = "Jane Doe"
layout = "programar"      # id de plantilla; vacío = fábrica
```

`layouts.toml`:

```toml
[[layouts]]
id = "programar"
name = "Programar"

[layouts.dock]            # barra superior
x = 0.40
y = 0.01

[layouts.input]           # barra inferior
x = 0.33
y = 0.92
width = 0.34

[layouts.windows.actividad]
open = true
x = 0.015
y = 0.03
width = 0.21
height = 0.55
order = 0
```

`settings.toml`, sección nueva:

```toml
[sound]
enabled = true
```

## Criterios de aceptación

- Unitarias (sin Qt): `parse` y `dump` de `profiles.toml` y `layouts.toml` en ambos sentidos;
  conservación de comentarios al guardar; borrador con y sin cambios; Guardar no escribe nada
  si hay errores; escritura atómica; migración desde `user.name`; plantilla con ventanas
  desconocidas o ausentes; eliminar una plantilla en uso; «preséntate» con el nombre del perfil.
- Unitarias: con `sound.enabled = false` el altavoz no reproduce y la FSM recorre los mismos
  estados.
- Manual: crear una plantilla, guardarla, asignarla a un perfil, elegir el perfil en la
  pantalla dormida, abrir sesión y comprobar la disposición y el nombre de «preséntate». Salir sin guardar no
  cambia ningún archivo. El selector de perfiles no aparece con un solo perfil ni fuera de
  `DORMIDO`.

## Documentación a actualizar

`software/restricciones.md` (RES-33, RES-36), `Modulos/Infraestructura/configuracion.md`,
`hud.md` (selector de perfiles, plantilla al abrir sesión, fin de `LayoutStore`), `proceso.md`
(entrada del menú), `entrada-texto.md` (←/→ en dormido) y un módulo nuevo
`Modulos/Infraestructura/configurador.md`. Los `.md` de la raíz solo se actualizan cuando lo
pida el autor.

## Lo que decide quien lo construya

- Cómo se parte `config.py` en el paquete `config/`, manteniendo su interfaz pública.
- Cómo se generan los `id` de perfiles y plantillas.
- El dibujo exacto de la ventana y de la paleta del editor, dentro de los tokens de `Theme.qml`.
- Cómo se evita que las barras se tapen en el editor: ajuste o vuelta atrás.
- Nombres y organización de las pruebas.

## Decisiones del diseño que conviene revisar

1. Una sola ventana en el mismo proceso, abierta solo en `DORMIDO` desde la bandeja.
2. Cada sesión empieza en la plantilla y se retira `LayoutStore`.
3. Selector de perfiles con chips, oculto si hay un solo perfil, con el último usado ya elegido.
4. Sin `profiles.toml`, un perfil «Predeterminado» con el `user.name` de siempre.
5. Sonido global, que silencia la voz y los avisos de ventana.
6. La ventana solo edita las entradas manuales del catálogo.

## Ideas para más adelante

- **Apartado General:** calidad gráfica, reducir movimiento, esquina del HUD, segundos de
  inactividad y volumen de la voz, con un botón **Probar voz**.
- **Por perfil:** voz y volumen propios, forma de dirigirse al usuario, lugares con nombre y aplicaciones
  favoritas.
- **Lugares, estructuras de carpetas y binarios permitidos** como apartados con lista y
  formulario. Encajan en el mismo registro.
- **Editor de protocolos** con validación contra el registro de intenciones.
- **Exportar e importar** la configuración en un `.zip`, para llevarla a otro equipo.
- **Restaurar valores de fábrica** de un apartado o de todo.
- **Activar o desactivar módulos** (y su ventana flotante) sin tocar el código.
- **Contraseña o código de activación propio** por perfil, en lugar de «Hey Jarvis».
