# Personalizar Jarvis

Cómo añadir sus aplicaciones, páginas web, carpetas, programas y protocolos. Sirve para una persona y para un agente de IA; el agente debe cumplir además las [Instrucciones para agentes](#instrucciones-para-agentes).

## Lo esencial

- **Su configuración está en `%APPDATA%\Jarvis\config\`**, fuera del repositorio. Se abre con «Abrir configuración» en el icono de la bandeja.
- **Nunca escriba datos personales en el repositorio.** La carpeta `implementation/src/jarvis_assistant/resources/config_defaults/` contiene plantillas genéricas que se suben a Git.
- **Los cambios se aplican al abrir sesión:** «Buenas noches Jarvis» y luego «Hey Jarvis».
- **Si se equivoca, no se rompe nada:** Jarvis avisa y sigue con la versión anterior del archivo.

## Índice

1. [Los archivos](#1-los-archivos)
2. [Aplicar y comprobar los cambios](#2-aplicar-y-comprobar-los-cambios)
3. [Aplicaciones y páginas web](#3-aplicaciones-y-páginas-web-catalogtoml)
4. [Lugares con nombre](#4-lugares-con-nombre-placestoml)
5. [Programas permitidos](#5-programas-permitidos-commandstoml)
6. [Estructuras de carpetas](#6-estructuras-de-carpetas-structurestoml)
7. [Protocolos](#7-protocolos-protocolstoml)
8. [Sustituciones de texto](#8-sustituciones-de-texto-aliasestoml)
9. [Ajustes generales](#9-ajustes-generales-settingstoml)
10. [Instrucciones para agentes](#instrucciones-para-agentes)

## 1. Los archivos

Todos están en `%APPDATA%\Jarvis\config\`, en formato [TOML](https://toml.io/es/), y explican sus claves en comentarios.

| Archivo | Para qué sirve | Orden que lo usa |
|---|---|---|
| `catalog.toml` | Aplicaciones y páginas web. | «abre {nombre}» |
| `places.toml` | Nombres cortos para sus carpetas. | «ve a {lugar}» |
| `commands.toml` | Programas que se pueden ejecutar. | «ejecuta {programa} …» |
| `structures.toml` | Plantillas de carpetas. | «crea la estructura {plantilla} llamada {nombre}» |
| `protocols.toml` | Varias tareas en una sola orden. | «protocolo {nombre}» |
| `aliases.toml` | Sustituciones de texto antes de interpretar la orden. | Todas |
| `settings.toml` | Tiempos, umbrales, volumen, interfaz y su nombre. | — |

Jarvis los crea en el primer arranque a partir de las plantillas del repositorio. Después solo lee los de `%APPDATA%`; nunca los modifica. Para recuperar una plantilla, borre o renombre su archivo y arranque Jarvis de nuevo: solo se copian los que faltan.

Para guardar una copia de su configuración, use una carpeta o un repositorio privados, distintos de este.

## 2. Aplicar y comprobar los cambios

1. Edite el archivo con cualquier editor de texto y guárdelo en UTF-8.
2. Cierre y abra la sesión: «Buenas noches Jarvis» y «Hey Jarvis».
3. Si Jarvis dice «Hay un error en la configuración de {archivo}. Uso la anterior.», busque las líneas `Configuración:` en el registro, `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`. Indican archivo, clave y motivo.
4. Pruebe las órdenes nuevas: «abre {nombre}», «qué protocolos hay», «ve a {lugar}».

Una clave que falta toma su valor predeterminado; una desconocida solo produce un aviso.

**Comprobar sin arrancar Jarvis.** Desde la carpeta `implementation\`, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "import os; from pathlib import Path; from jarvis_assistant import config; c, e = config.load(Path(os.environ['APPDATA']) / 'Jarvis' / 'config'); print('\n'.join(('AVISO ' if x.warning else 'ERROR ') + f'{x.file} {x.key}: {x.reason}' for x in e) or 'Sin errores')"
```

Un `ERROR` hace que Jarvis descarte ese archivo; un `AVISO` no. Esta comprobación no valida las tareas de los protocolos: eso se hace al abrir sesión y queda en el registro.

## 3. Aplicaciones y páginas web (`catalog.toml`)

Para «abre {nombre}», Jarvis busca en este orden: sus `[[apps]]`, sus `[[pages]]` y las aplicaciones del menú Inicio.

```toml
discover_installed_apps = true              # incluir las aplicaciones del menú Inicio

[[apps]]
name = "Visual Studio Code"                 # nombre que se escribe y que dice Jarvis
aliases = ["code", "vs code", "el editor"]  # otras formas de escribirlo (opcional)
path = "C:/Users/usuario/AppData/Local/Programs/Microsoft VS Code/Code.exe"
args = []                                   # argumentos (opcional)

[[pages]]
name = "Documentación"
aliases = ["docs", "la documentación"]
url = "https://example.com/docs"
```

- `path` acepta un `.exe`, un acceso directo `.lnk` o un nombre del `PATH` (`"notepad"`). Use `/` o `\\` en las rutas.
- Una aplicación del menú Inicio funciona sin añadirla. Añádala solo para darle alias o lanzar un ejecutable concreto.
- Las páginas se abren siempre en Microsoft Edge, y solo las de este archivo.

## 4. Lugares con nombre (`places.toml`)

Un nombre corto para una carpeta. Vale en cualquier orden con ruta: «ve a proyectos», «crea la carpeta apuntes en universidad».

```toml
[places]
proyectos = "D:/Proyectos"
universidad = "D:/Universidad"
```

Escritorio, Documentos, Descargas, Imágenes, Música y Vídeos ya vienen incluidos.

## 5. Programas permitidos (`commands.toml`)

«Ejecuta …» solo lanza los programas de esta lista. No pasa por `cmd` ni PowerShell, así que no funcionan tuberías (`|`) ni redirecciones (`>`).

```toml
[[binaries]]
name = "git"               # primera palabra de la orden
executable = "git"         # nombre en el PATH o ruta absoluta
aliases = ["guit"]         # opcional
timeout_seconds = 60       # opcional; por defecto, 120
```

Vienen incluidos `git`, `gcc`, `g++`, `make`, `python`, `pip`, `node` y `npm`.

## 6. Estructuras de carpetas (`structures.toml`)

```toml
[[structures]]
name = "proyecto web"
folders = ["public", "src/components", "src/styles"]
```

«Crea la estructura proyecto web llamada tienda» crea `tienda\` con esas subcarpetas dentro.

## 7. Protocolos (`protocols.toml`)

Varias tareas con una sola orden: «protocolo modo trabajo».

```toml
[[protocols]]
id = "modo-trabajo"          # único, sin espacios
name = "modo trabajo"        # nombre que se escribe
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
  stop_on_error = true       # opcional: si falla, se detiene el protocolo
```

- **Los parámetros se escriben como en una orden:** «proyectos barra web», no `proyectos/web`.
- Las tareas van en orden. Sin `stop_on_error`, un error no detiene el protocolo.
- `description` (opcional) es el texto que muestra el panel para esa tarea.
- `id`, `name` y `aliases` no se pueden repetir. Un protocolo no puede lanzar otro.
- Un protocolo con una tarea no válida se descarta entero; el motivo queda en el registro.

### Acciones disponibles

| `module` | `action` | Obligatorios | Opcionales |
|---|---|---|---|
| `apertura` | `abrir` · `traer_al_frente` | `objetivo` | — |
| `apertura` | `abrir_carpeta` | — | `ruta` |
| `comandos` | `cd` | `ruta` | — |
| `comandos` | `ejecutar` | `comando` | — |
| `comandos` | `arbol` | — | `ruta` |
| `comandos` | `ls` · `pwd` · `clear` · `abrir_consola` | — | — |
| `busqueda` | `buscar` | `consulta` | `tipo`: `"ambos"`, `"archivos"` o `"carpetas"` |
| `creacion` | `crear_archivo` · `crear_carpeta` | `nombre` | `ruta` |
| `creacion` | `crear_arbol` | `arbol` | `ruta` |
| `creacion` | `crear_estructura` | `estructura`, `nombre` | `ruta` |
| `recordatorio` | `crear` | `texto` | — |
| `recordatorio` | `mostrar` | — | — |
| `historial` | `mostrar` | — | — |
| `historial` | `actividades` | — | `id` |

## 8. Sustituciones de texto (`aliases.toml`)

Cambia un texto por otro en **todas** las órdenes antes de interpretarlas. Úselo con cuidado.

```toml
[aliases]
"ce de" = "cd"
"guit" = "git"
```

## 9. Ajustes generales (`settings.toml`)

| Clave | Predeterminado | Efecto |
|---|---|---|
| `user.name` | `""` | Su nombre, para «preséntate». |
| `input.inactivity_to_idle_seconds` | `120` | Segundos sin escribir antes del reposo (5–600). |
| `tts.volume` | `1.0` | Volumen de la voz (0–1). |
| `router.intent_threshold` | `80` | Exigencia al reconocer órdenes (0–100). Más bajo: más tolerante y más confusiones. |
| `router.catalog_threshold` | `75` | Lo mismo para nombres de aplicaciones, páginas y protocolos. |
| `router.default_hour` | `9` | Hora de una fecha sin hora. |
| `dialogue.timeout_seconds` | `20` | Tiempo para responder a una pregunta. |
| `reminders.snooze_minutes` | `10` | Minutos de «posponer». |
| `ui.hud_corner` | `"top-right"` | Esquina del HUD: `top-right`, `top-left`, `bottom-right`, `bottom-left`. |
| `ui.quality` | `"high"` | Calidad gráfica: `high`, `medium`, `low`. |
| `ui.reduce_motion` | `false` | Cambia las animaciones por fundidos. |
| `logging.level` | `"INFO"` | Con `"DEBUG"`, el registro guarda el texto de sus órdenes. |

Todas las claves: [configuracion.md](software/Modulos/Infraestructura/configuracion.md).

## Instrucciones para agentes

Un agente de IA que configura Jarvis por encargo debe:

1. **Editar solo `%APPDATA%\Jarvis\config\`.** Si no existe, Jarvis no se ha arrancado nunca: arránquelo una vez ([INSTALAR.md](INSTALAR.md)).
2. **No escribir datos del usuario en el repositorio** (plantillas, documentación ni pruebas), ni hacer commits con ellos. Los ejemplos del repositorio usan datos inventados.
3. **Copiar antes de editar:** guarde `{archivo}.bak` junto al original.
4. **Añadir, no sustituir:** conserve las entradas y los comentarios existentes.
5. **No inventar rutas:** compruebe que cada ejecutable y carpeta existen o pregunte al usuario.
6. **En protocolos**, usar solo las [acciones disponibles](#acciones-disponibles), con los parámetros escritos como frases.
7. **Validar** con el comando de la [sección 2](#2-aplicar-y-comprobar-los-cambios). Si hay un `ERROR`, corregirlo o restaurar el `.bak`.
8. **Informar** al usuario de qué archivos ha cambiado y de que los cambios se aplican al abrir la siguiente sesión.
