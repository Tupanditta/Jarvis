# Módulo de acción: Comandos

- **Código:** `action_modules/command_runner.py`. Nombre de módulo: `comandos`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Ofrecer una terminal manejada con órdenes escritas con directorio de trabajo persistente, generar el árbol de directorios de una carpeta (mapeo de entorno) y ejecutar binarios externos, informando del resultado.

## Acciones

| Acción | Parámetros | Efecto |
|---|---|---|
| `cd` | `ruta: DIR_PATH` | Cambia el directorio de trabajo (RN-14, RN-15). Publica `WorkdirChanged`. Dice el nombre de la carpeta resultante. |
| `ls` | — | Lee el directorio de trabajo con `os.scandir`. Publica `DirectoryListed` (carpetas primero, orden alfabético sin distinguir mayúsculas; máximo 500 entradas). Dice el recuento de carpetas y archivos. |
| `pwd` | — | Dice y muestra el directorio de trabajo (RF-98). |
| `arbol` | `ruta: DIR_PATH` (opcional) | Mapeo de entorno (RF-59, RF-73, RF-74). |
| `clear` | — | Publica `CommandPanelCleared` (RF-18). |
| `ejecutar` | `comando: COMMAND_LINE` | Ejecuta un binario permitido (RF-19, RF-20). |
| `abrir_consola` | — | Abre la terminal del sistema en el directorio de trabajo (RF-21). |

Todas se pueden invocar con una orden escrita y desde protocolos. Todas activan el panel de comandos, salvo `abrir_consola`.

## Reglas

### Directorio de trabajo

- Vive en `core/workdir.py` y se comparte por `ctx.workdir`; solo `cd` lo modifica. Otros módulos lo leen para resolver rutas relativas (RN-42).
- Empieza en la carpeta del usuario en cada sesión nueva; no se guarda en la base de datos (RN-14).
- La resolución de la ruta escrita (lugares con nombre, subcarpetas por coincidencia difusa, «atrás») es del enrutador ([enrutador-intenciones.md](../Infraestructura/enrutador-intenciones.md), sección 6). El módulo recibe una `Path` ya resuelta y comprueba de nuevo que existe y es carpeta.
- Ruta inválida: RN-41. El directorio de trabajo no cambia.

### Mapeo de entorno (RN-40)

- Recorrido en anchura con `os.scandir`, ejecutado con `asyncio.to_thread`.
- La raíz no cuenta como nivel ni como entrada; sus hijos son el nivel 1. Se baja hasta el nivel 3.
- Las entradas son carpetas y archivos; dentro de cada carpeta, carpetas primero y orden alfabético.
- Se detiene al llegar a 200 entradas; entonces `truncated = True`.
- No se siguen enlaces simbólicos. Una carpeta sin permiso de lectura aparece como entrada, sin hijos.
- Publica `DirectoryTreeBuilt`. El panel lo muestra con sangría por nivel y, si se recortó, una línea final «… (árbol recortado)».
- Voz: recuento de carpetas y archivos mostrados; si se recortó, añade «Se muestra solo una parte.».

### Binarios externos

- **Lista cerrada (RN-45):** solo los binarios de `commands.toml`. La primera palabra del comando, tras aplicar los alias, debe coincidir con el `name` de uno; el resto son argumentos.
- **Lanzamiento:** `asyncio.create_subprocess_exec(executable, *args, cwd=workdir, stdin=DEVNULL, stdout=PIPE, stderr=PIPE)`. Nunca con intérprete de órdenes.
- **Salida:** se lee línea a línea, se decodifica sin fallar ante bytes inválidos, y se publica en `CommandOutputAppended` en lotes cada 200 ms. El panel conserva las últimas 200 ⚙ líneas.
- **Resultado (RN-16):** código 0 → `completado`; otro código → `error`; ejecutable no encontrado → `error` con «No encuentro el programa {nombre}.».
- **Tiempo máximo:** 120 s ⚙, o el `timeout_seconds` del binario. Al vencer, se termina el árbol de procesos y la tarea queda en `error` con «El comando ha tardado demasiado.».
- **Con una orden del usuario:** la tarea se devuelve en segundo plano (`background=True`): el asistente dice «Ejecutando {comando}.» y sigue atendiendo órdenes. Al terminar, la tarea se actualiza y se encola un aviso con el resultado (RN-39). Solo puede haber un binario en ejecución lanzado con una orden; pedir otro produce `error` con «Ya hay un comando en ejecución.».
- **En un protocolo:** se espera en línea y devuelve su resultado directamente.
- **Cancelación y cierre de sesión:** se termina el árbol de procesos (con `psutil`) y la tarea queda en `error` (RN-46, RN-52).

### Abrir consola

`ctx.platform.open_terminal(workdir)`. Es una ventana externa del sistema, independiente del panel de comandos. Fallo al abrirla: tarea en `error`.

## Datos

Directorio de trabajo en memoria. Ningún dato propio en la base de datos.

## Eventos

`WorkdirChanged`, `DirectoryListed`, `DirectoryTreeBuilt`, `CommandOutputAppended`, `CommandPanelCleared`.

## Criterios de aceptación

Con un sistema de archivos temporal y un lanzador de procesos falso:

- `cd` a carpeta válida, inexistente y a un archivo.
- `ls` ordena y cuenta.
- `arbol`: profundidad máxima 3, corte en 200 entradas, raíz sin contar, recuentos correctos.
- `ejecutar`: binario no permitido, código 0, código distinto de 0, ejecutable inexistente, tiempo agotado, segundo binario simultáneo, cancelación.
- `ejecutar` real con `python --version` (prueba de integración).
- Ninguna llamada usa `shell=True` (prueba que inspecciona el código).

## Prohibiciones

- `cd`, `ls`, `clear` y el árbol no se ejecutan como subprocesos.
- No se ejecuta ningún binario fuera de la lista permitida ni mediante un intérprete de órdenes.
- La ejecución de binarios no bloquea la escucha.
