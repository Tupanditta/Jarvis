# Personalizar Jarvis

Esta guía explica cómo adaptar Jarvis a su equipo: aplicaciones, páginas web, carpetas, programas permitidos, protocolos y ajustes. Sirve para una persona que edita los archivos a mano y para un agente de IA que lo hace por encargo. La sección [Instrucciones para agentes](#instrucciones-para-agentes) recoge las reglas que un agente debe cumplir.

Para usar el asistente, consulte [MANUAL.md](MANUAL.md). Para instalarlo, [implementation/README.md](implementation/README.md).

## Índice

1. [Dónde está su configuración](#1-dónde-está-su-configuración)
2. [Cómo se aplican los cambios](#2-cómo-se-aplican-los-cambios)
3. [Aplicaciones y páginas web](#3-aplicaciones-y-páginas-web-catalogtoml)
4. [Lugares con nombre](#4-lugares-con-nombre-placestoml)
5. [Programas permitidos](#5-programas-permitidos-commandstoml)
6. [Estructuras de carpetas](#6-estructuras-de-carpetas-structurestoml)
7. [Protocolos](#7-protocolos-protocolstoml)
8. [Sustituciones de texto](#8-sustituciones-de-texto-aliasestoml)
9. [Ajustes generales](#9-ajustes-generales-settingstoml)
10. [Comprobar la configuración](#10-comprobar-la-configuración)
11. [Instrucciones para agentes](#instrucciones-para-agentes)

## 1. Dónde está su configuración

Su configuración personal está **fuera del repositorio**, en la carpeta de su usuario de Windows:

```text
%APPDATA%\Jarvis\config\
```

En el primer arranque, Jarvis copia ahí los archivos predeterminados del repositorio, que están en `implementation/src/jarvis_assistant/resources/config_defaults/`. Desde ese momento, Jarvis solo lee la copia de `%APPDATA%`. Para abrir esa carpeta, use «Abrir configuración» en el menú del icono de la bandeja.

| Carpeta | Qué contiene | ¿Se sube a Git? |
|---|---|---|
| `%APPDATA%\Jarvis\config\` | **Su** configuración: sus aplicaciones, páginas, rutas y protocolos. | No. Está fuera del repositorio. |
| `implementation/src/jarvis_assistant/resources/config_defaults/` | Plantillas genéricas para cualquier usuario nuevo. | Sí. No debe contener nada personal. |

**Regla principal:** escriba sus datos solo en `%APPDATA%\Jarvis\config\`. Nunca escriba URLs, rutas, nombres ni protocolos personales en `config_defaults/`, porque esa carpeta forma parte del repositorio.

Para guardar una copia de seguridad de su configuración, cópiela a una carpeta privada o a un repositorio privado distinto de este.

### Archivos

| Archivo | Para qué sirve |
|---|---|
| `catalog.toml` | Aplicaciones y páginas web para «abre {nombre}». |
| `places.toml` | Nombres cortos para sus carpetas («ve a proyectos»). |
| `commands.toml` | Programas que se pueden ejecutar con «ejecuta …». |
| `structures.toml` | Estructuras de carpetas para «crea la estructura …». |
| `protocols.toml` | Secuencias de tareas que se lanzan con una sola orden. |
| `aliases.toml` | Sustituciones de texto antes de interpretar cada orden. |
| `settings.toml` | Tiempos, umbrales, voz, interfaz y su nombre. |

Todos usan el formato [TOML](https://toml.io/es/). Cada archivo explica sus claves en comentarios.

## 2. Cómo se aplican los cambios

1. Edite el archivo en `%APPDATA%\Jarvis\config\` con cualquier editor de texto. Guárdelo en UTF-8.
2. Cierre la sesión con «Buenas noches Jarvis» y abra otra con «Hey Jarvis». Jarvis relee la configuración al abrir cada sesión y al arrancar.
3. Si un archivo tiene un error, Jarvis dice «Hay un error en la configuración de {archivo}. Uso la anterior.» y sigue con la versión anterior de ese archivo. El detalle del error está en el registro (ver la [sección 10](#10-comprobar-la-configuración)).

Otras reglas:

- Una clave que falta toma su valor predeterminado. Un archivo vacío es válido.
- Una clave desconocida solo produce un aviso en el registro.
- Jarvis nunca escribe en estos archivos: solo los lee.
- Para recuperar un archivo predeterminado, borre o renombre su copia en `%APPDATA%\Jarvis\config\` y arranque Jarvis de nuevo. Solo se copian los archivos que faltan; nunca se sobrescribe uno existente.

## 3. Aplicaciones y páginas web (`catalog.toml`)

Cuando escribe «abre {nombre}», Jarvis busca el nombre en este orden:

1. las aplicaciones de `[[apps]]`;
2. las páginas de `[[pages]]`;
3. las aplicaciones del menú Inicio, si `discover_installed_apps = true`.

Gana la primera fuente con una coincidencia suficiente. La tolerancia se ajusta con `router.catalog_threshold` en `settings.toml`.

### Aplicación

```toml
[[apps]]
name = "Visual Studio Code"                 # nombre que se escribe y que dice Jarvis
aliases = ["code", "vs code", "el editor"]  # otras formas de escribirlo (opcional)
path = "C:/Users/usuario/AppData/Local/Programs/Microsoft VS Code/Code.exe"
args = []                                   # argumentos (opcional)
```

- `path` puede ser un ejecutable (`.exe`), un acceso directo (`.lnk`) o un nombre que esté en el `PATH`, como `"notepad"`.
- Use barras `/` en las rutas, o barras invertidas dobles `\\`.
- Si la aplicación ya aparece en el menú Inicio, no hace falta añadirla. Añádala solo para darle alias o para lanzar un ejecutable concreto.

### Página web

```toml
[[pages]]
name = "Documentación"
aliases = ["docs", "la documentación"]
url = "https://example.com/docs"
```

- Las páginas se abren siempre en Microsoft Edge.
- Solo se abren las URLs de este archivo. No hay otra forma de añadir páginas.

### Sin descubrimiento automático

```toml
discover_installed_apps = false
```

Con este valor, solo se abren las aplicaciones de `[[apps]]`.

## 4. Lugares con nombre (`places.toml`)

Asocia un nombre corto a una carpeta. Sirve en cualquier orden que acepte una ruta: «ve a proyectos», «abre la carpeta universidad», «crea la carpeta apuntes en universidad».

```toml
[places]
proyectos = "D:/Proyectos"
universidad = "D:/Universidad"
```

Escritorio, Documentos, Descargas, Imágenes, Música y Vídeos ya vienen incluidos, con las carpetas reales del sistema. Un nombre suyo con el mismo nombre que uno de estos lo sustituye.

## 5. Programas permitidos (`commands.toml`)

«Ejecuta {comando}» solo lanza los programas de esta lista. Nunca se usa un intérprete de órdenes (`cmd`, PowerShell), así que no funcionan tuberías ni redirecciones.

```toml
[[binaries]]
name = "git"               # nombre que se escribe al principio de la orden
executable = "git"         # nombre en el PATH o ruta absoluta
aliases = ["guit"]         # otras formas de escribirlo (opcional)
timeout_seconds = 60       # tiempo máximo (opcional; por defecto, commands.default_timeout_seconds)
```

Vienen incluidos `git`, `gcc`, `g++`, `make`, `python`, `pip`, `node` y `npm`. Para quitar uno, borre su bloque. Para añadir otro, copie un bloque y cámbielo.

## 6. Estructuras de carpetas (`structures.toml`)

Define plantillas para «crea la estructura {estructura} llamada {nombre}». Jarvis crea una carpeta `{nombre}` y, dentro, las subcarpetas de la lista.

```toml
[[structures]]
name = "proyecto python"
folders = ["src", "tests", "docs", "scripts"]

[[structures]]
name = "proyecto web"
folders = ["public", "src/components", "src/styles"]
```

## 7. Protocolos (`protocols.toml`)

Un protocolo ejecuta varias tareas con una sola orden: «protocolo modo trabajo».

```toml
[[protocols]]
id = "modo-trabajo"          # identificador único, sin espacios
name = "modo trabajo"        # nombre que se escribe; se propone como nombre de la sesión
aliases = ["a trabajar"]     # opcional
important = true             # opcional: marca la sesión como importante

  [[protocols.tasks]]
  module = "comandos"
  action = "cd"
  params = { ruta = "proyectos barra web" }

  [[protocols.tasks]]
  module = "apertura"
  action = "abrir"
  params = { objetivo = "Visual Studio Code" }

  [[protocols.tasks]]
  module = "comandos"
  action = "ejecutar"
  params = { comando = "git status" }
  stop_on_error = true       # opcional: si falla, no se ejecutan las siguientes
```

- Las tareas se ejecutan en orden. Por defecto, un error no detiene el protocolo.
- Los parámetros se escriben **igual que en una orden escrita**: «barra» para separar carpetas, «punto» para la extensión, nombres del catálogo o de `places.toml`.
- Cada tarea admite también `description`: el texto que se muestra en el panel. Si falta, se genera.
- `id`, `name` y `aliases` no se pueden repetir entre protocolos.
- Un protocolo no puede ejecutar otro protocolo.

### Acciones que admiten los protocolos

| `module` | `action` | `params` obligatorios | `params` opcionales |
|---|---|---|---|
| `comandos` | `cd` | `ruta` | — |
| `comandos` | `ls` | — | — |
| `comandos` | `pwd` | — | — |
| `comandos` | `arbol` | — | `ruta` |
| `comandos` | `clear` | — | — |
| `comandos` | `ejecutar` | `comando` | — |
| `comandos` | `abrir_consola` | — | — |
| `apertura` | `abrir` | `objetivo` | — |
| `apertura` | `abrir_carpeta` | — | `ruta` |
| `apertura` | `traer_al_frente` | `objetivo` | — |
| `busqueda` | `buscar` | `consulta` | `tipo`: `"ambos"`, `"archivos"` o `"carpetas"` |
| `creacion` | `crear_archivo` | `nombre` | `ruta` |
| `creacion` | `crear_carpeta` | `nombre` | `ruta` |
| `creacion` | `crear_arbol` | `arbol` | `ruta` |
| `creacion` | `crear_estructura` | `estructura`, `nombre` | `ruta` |
| `recordatorio` | `crear` | `texto` | — |
| `recordatorio` | `mostrar` | — | — |
| `historial` | `mostrar` | — | — |
| `historial` | `actividades` | — | `id` |

Las demás acciones (sesión, eliminar, confirmar, posponer, abrir resultados de búsqueda y los propios protocolos) no se pueden usar en un protocolo. Un protocolo con una tarea no válida se descarta entero y el error queda en el registro; los demás protocolos se cargan.

## 8. Sustituciones de texto (`aliases.toml`)

Cada pareja sustituye un texto por otro antes de interpretar la orden. Sirve para abreviaturas y formas alternativas de escribir una palabra.

```toml
[aliases]
"ce de" = "cd"
"ele ese" = "ls"
"guit" = "git"
```

Use alias con cuidado: se aplican a todas las órdenes.

## 9. Ajustes generales (`settings.toml`)

Los ajustes más útiles:

| Clave | Predeterminado | Efecto |
|---|---|---|
| `user.name` | `""` | Su nombre, para «preséntate». Vacío: Jarvis no lo dice. |
| `input.inactivity_to_idle_seconds` | `120` | Segundos sin escribir antes de pasar a reposo (5–600). |
| `tts.volume` | `1.0` | Volumen de la voz (0–1). |
| `router.intent_threshold` | `80` | Similitud mínima (0–100) para reconocer una orden. Más bajo: más tolerante a erratas y más confusiones. |
| `router.catalog_threshold` | `75` | Similitud mínima de una aplicación, página o protocolo. |
| `router.default_hour` | `9` | Hora de una fecha escrita sin hora. |
| `dialogue.timeout_seconds` | `20` | Tiempo para responder a una pregunta. |
| `reminders.snooze_minutes` | `10` | Minutos de «posponer» sin duración. |
| `ui.hud_corner` | `"top-right"` | Esquina del HUD: `top-right`, `top-left`, `bottom-right` o `bottom-left`. |
| `ui.quality` | `"high"` | Calidad gráfica: `high`, `medium` o `low`. |
| `ui.reduce_motion` | `false` | Cambia las animaciones por fundidos. |
| `logging.level` | `"INFO"` | Nivel del registro. Con `DEBUG`, el texto de las órdenes aparece en el registro. |

Lista completa de claves: [configuracion.md](software/Modulos/Infraestructura/configuracion.md).

## 10. Comprobar la configuración

### Desde Jarvis

1. Cierre y abra la sesión.
2. Si Jarvis dice «Hay un error en la configuración de {archivo}», abra el registro: `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.
3. Busque las líneas que empiezan por `Configuración:`. Indican archivo, clave y motivo.
4. Pruebe las órdenes nuevas: «abre {nombre}», «qué protocolos hay», «ve a {lugar}».

### Desde la terminal

Desde la carpeta `implementation\`, en PowerShell. Comprueba la sintaxis, los tipos y los rangos de todos los archivos sin arrancar Jarvis:

```powershell
.\.venv\Scripts\python.exe -c "import os; from pathlib import Path; from jarvis_assistant import config; c, e = config.load(Path(os.environ['APPDATA']) / 'Jarvis' / 'config'); print('\n'.join(('AVISO ' if x.warning else 'ERROR ') + f'{x.file} {x.key}: {x.reason}' for x in e) or 'Sin errores')"
```

Las líneas `ERROR` hacen que Jarvis descarte ese archivo. Las líneas `AVISO`, como una clave desconocida de una versión anterior, no impiden cargarlo.

Esta comprobación no valida las tareas de los protocolos contra los módulos. Esa parte se hace al abrir sesión: revise el registro como en el apartado anterior.

## Instrucciones para agentes

Reglas para un agente de IA que configura Jarvis por encargo del usuario.

### Reglas obligatorias

1. **Edite solo `%APPDATA%\Jarvis\config\`.** Es la configuración del usuario y está fuera del repositorio.
2. **No escriba datos personales en el repositorio.** Nunca añada URLs, rutas, nombres de usuario, aplicaciones ni protocolos del usuario a `implementation/src/jarvis_assistant/resources/config_defaults/`, a la documentación ni a las pruebas. Los ejemplos del repositorio usan datos inventados (`https://example.com`, `D:/Proyectos`, `usuario`).
3. **No haga commits** de la configuración del usuario.
4. **Copie antes de editar.** Antes de cambiar un archivo, guarde una copia junto a él con la extensión `.bak` (por ejemplo, `catalog.toml.bak`).
5. **Edite, no sustituya.** Conserve las entradas y los comentarios existentes. Añada bloques nuevos al final de su sección.
6. **No invente rutas.** Compruebe que cada ejecutable y cada carpeta existen antes de escribirlos. Si no puede comprobarlo, pregunte al usuario.
7. **Valide después de editar** con el comando de la [sección 10](#desde-la-terminal). Si hay errores, corríjalos o restaure la copia `.bak`.
8. **Para protocolos**, use solo las acciones de la [tabla de la sección 7](#acciones-que-admiten-los-protocolos) y escriba los parámetros como frases escritas («proyectos barra web», no `proyectos/web`).

### Procedimiento

1. Lea el archivo actual de `%APPDATA%\Jarvis\config\`. Si la carpeta no existe, Jarvis no se ha arrancado nunca: arránquelo una vez o copie los archivos de `config_defaults/`.
2. Guarde la copia `.bak`.
3. Haga el cambio pedido, con el formato de las secciones 3 a 9.
4. Ejecute la validación de la sección 10.
5. Diga al usuario qué archivos ha cambiado y que los cambios se aplican al abrir la siguiente sesión.
