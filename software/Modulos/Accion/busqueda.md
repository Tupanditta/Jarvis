# Módulo de acción: Búsqueda de Archivos/Carpetas

- **Código:** `action_modules/file_manager.py` (compartido con [Creación](creacion-archivos.md)). Nombre de módulo: `busqueda`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Localizar archivos, carpetas o ambos en disco de forma rápida mediante herramientas indexadas, y permitir abrir lo encontrado.

## Acciones

| Acción | Parámetros | Efecto |
|---|---|---|
| `buscar` | `consulta: TEXT`, `tipo` ∈ `archivos`, `carpetas`, `ambos` (lo fija el patrón) | Busca y muestra los resultados (RF-26, RF-27, RF-28). |
| `abrir_resultado` | `n: INTEGER` | Abre el resultado *n* con su aplicación predeterminada; si es una carpeta, en el gestor de archivos (RF-90). |
| `abrir_ubicacion` | `n: INTEGER` | Abre en el gestor de archivos la carpeta que contiene el resultado *n*. |

Todas se pueden invocar con una orden escrita; `buscar`, también desde protocolos. Todas activan el panel de búsqueda.

## Reglas

### Búsqueda indexada

- `ctx.platform.indexed_search(query, kind, limit)`: en Windows, `es.exe` de *Everything*, con el filtro de archivos, carpetas o ambos y un límite de 50 resultados. Los parámetros exactos de `es.exe` se comprueban con su ayuda al implementar el adaptador.
- La consulta es el texto escrito; *Everything* busca por nombre.

### Búsqueda limitada (sin herramienta indexada)

Si `indexed_search` devuelve `None` (*Everything* no está instalado o no responde):

- Se recorren, con `os.scandir` en un hilo, solo la carpeta del usuario y los lugares con nombre, hasta 6 niveles de profundidad, omitiendo carpetas ocultas y de sistema y las habituales de dependencias (`node_modules`, `.git`, `.venv`, `__pycache__`).
- Coincide un nombre que, normalizado, contiene la consulta normalizada.
- Se corta a los 5 s ⚙ o a los 50 resultados.
- El resultado se marca `limited = True`; el panel lo indica y la voz añade «Búsqueda limitada a sus carpetas.». La primera vez en cada sesión, añade «Instale Everything para buscar en todo el disco.».

Nunca se recorre el disco completo (RES-31).

### Presentación

- **Orden:** nombre igual a la consulta; después, nombre que empieza por ella; después, el resto; a igualdad, ruta más corta.
- **Panel:** los 10 ⚙ primeros, numerados, con nombre, tipo y carpeta. Si hay más, se indica el total.
- **Voz:** sin resultados, «No he encontrado nada para {consulta}.» (tarea `completado`); con uno, su nombre y carpeta; con varios, el número y el nombre y la carpeta del primero.
- El módulo guarda la última lista de resultados en memoria; los índices de `abrir_resultado` y `abrir_ubicacion` se refieren a ella (RN-50). Se vacía al cerrar la sesión.

### Un solo resultado: ofrecer abrirlo

- Si la búsqueda da exactamente una coincidencia, tras decir el resumen (y los avisos de búsqueda limitada) pregunta «¿Quiere que lo abra?» (`BOOLEAN`, ofrecimiento `OFFER`).
- Con un sí, lo abre como `abrir_resultado 1`; la tarea conserva la descripción «buscar {consulta}» y responde «Abriendo {nombre}.» (o el error de apertura).
- Con un no, «cancelar» o tiempo agotado, la búsqueda queda `completado` sin decir nada más: no se dice «Operación cancelada.».
- No se pregunta en un protocolo (`origin = "protocolo"`) ni con varios resultados.

### Abrir un resultado

- `abrir_resultado`: `ctx.platform.open_with_default(path)`; para una carpeta, `open_folder`.
- Si el archivo ya no existe: `error`, «Ese archivo ya no existe.».
- Sin búsqueda previa o índice fuera de rango: `error` (RN-50).

## Datos

Índices de la herramienta de búsqueda del sistema. Última lista de resultados en memoria.

## Eventos

`SearchResultsReady`.

## Criterios de aceptación

Con `FakePlatform` y un sistema de archivos temporal:

- Filtro por tipo; orden de presentación; límite de 10 mostrados con total.
- Búsqueda limitada: profundidad, carpetas omitidas, corte por tiempo con reloj falso, marca `limited`.
- `abrir_resultado` y `abrir_ubicacion`: índice válido, fuera de rango, sin búsqueda previa, archivo desaparecido.
- Un solo resultado: se ofrece abrirlo; sí abre (archivo o carpeta), no y cancelar dejan la búsqueda `completado`; sin pregunta en protocolos ni con varios resultados.
- Con marcador `hardware`: búsqueda real con `es.exe`, dentro de RNF-09.

## Prohibiciones

- No se recorre todo el disco con bucles lentos cuando la raíz es amplia.
- La búsqueda no modifica ni borra nada.
