# Módulo de acción: Sesión

- **Código:** `action_modules/session_manager.py` (compartido con [Historial](historial.md)). Nombre de módulo: `sesion`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Gestionar la sesión de uso actual: su apertura y cierre, su nombre y su importancia, con prioridad sobre los cambios que propongan los [Protocolos](protocolos.md).

## Ciclo de vida de la sesión

El ciclo completo está en RN-43 y en [maquina-estados.md](../Infraestructura/maquina-estados.md). Este módulo ejecuta la parte de datos; lo llama el orquestador, no una intención del usuario.

| Operación | Cuándo | Qué hace |
|---|---|---|
| `open_session()` | `DORMIDO` → `LISTENING_COMMAND` | Crea la fila con el nombre por defecto (RN-02), `is_important = 0` y `opened_at` = ahora. Restablece el directorio de trabajo a la carpeta del usuario (RN-14). Publica `SessionChanged`. |
| `close_session(reason)` | Cierre con la frase de cierre o salida del proceso | Si la sesión está vacía (RN-69), la elimina y publica `SessionsDeleted`. Si no, marca `error` las actividades `pendiente` (RN-46), fija `closed_at` y `close_reason` (`voz`, el cierre con la frase de cierre, o `salida`) y, por último, elimina las sesiones marcadas por desbordamiento por esta sesión (RN-09), lo que renumera las demás. |
| `recover_interrupted()` | Arranque del proceso | Para cada sesión sin `closed_at`: aplica `close_session` con `close_reason = 'interrumpida'` y `closed_at` = momento de su última actividad, o `opened_at` si no tiene (RN-47). Una vacía se elimina. |
| `discard_empty()` | Arranque del proceso | Elimina las sesiones cerradas que quedaron vacías (RN-69) y publica `SessionsDeleted`. |

## Acciones

| Acción | Parámetros | Con una orden | En protocolos | Efecto |
|---|---|---|---|---|
| `nombrar` | `nombre: TEXT` | Sí | No | Fija el nombre y `name_set_by_module = 1`. |
| `marcar_importante` | — | Sí | No | `is_important = 1`, `importance_locked_by_module = 1`. Comprueba el desbordamiento. |
| `desmarcar_importante` | — | Sí | No | `is_important = 0`, `importance_locked_by_module = 0`. Restaura la sesión desplazada, si la hay. |
| `proponer_nombre` | `nombre: TEXT` | No | Solo desde Protocolos | Si `name_set_by_module = 1`, no hace nada. Si no, pregunta (`BOOLEAN`) y, con un sí, cambia el nombre sin tocar `name_set_by_module`. |
| `importante_por_protocolo` | — | No | Solo desde Protocolos | Si ya es importante, no hace nada. Si no, `is_important = 1` sin tocar `importance_locked_by_module`. Comprueba el desbordamiento. |

Las dos últimas no tienen patrones: solo las invoca el módulo Protocolos con `ctx.invoke`.

## Reglas

### Prioridad de estado (estricta)

- **Nombre:** fijado por el usuario (`name_set_by_module = 1`), ningún protocolo lo cambia (RN-03). Si no, un protocolo puede proponerlo, siempre con confirmación (RN-04).
- **Importancia:** si el usuario la marcó no importante y un protocolo la marca importante, prevalece importante (RN-05). Un protocolo nunca la degrada (RN-06): el módulo no ofrece ninguna acción de protocolo que quite la importancia.

### Desbordamiento de sesiones importantes (RN-07, RN-08)

Tras poner `is_important = 1` en la sesión actual, en la misma transacción:

1. Si el número de sesiones importantes no eliminadas es mayor que 10:
2. se toma la importante más antigua (menor `opened_at`) distinta de la actual;
3. se le pone `is_important = 0`, `pending_purge_on_close = 1` y `displaced_by = <id de la sesión actual>`;
4. se publica `SessionOverflowed` y se dice el aviso con el nombre de la sesión que sale.

**Restauración:** si la sesión actual deja de ser importante antes de cerrarse, las sesiones con `displaced_by` igual a su id recuperan `is_important = 1` y pierden la marca.

**Eliminación:** al cerrar la sesión actual, las sesiones con `displaced_by` igual a su id y `pending_purge_on_close = 1` se borran del todo con sus actividades, y las demás se renumeran (RN-12, RN-53).

### Otras

- Un nombre vacío no es válido: tarea en `error`.
- Se permiten nombres repetidos fijados por el usuario.

## Datos

Tabla `sessions` ([especificacion-base-datos.md](../../BaseDatos/especificacion-base-datos.md)), mediante `SessionRepository`.

## Eventos

`SessionChanged`, `SessionOverflowed`, y `DialogueOpened` a través de `ctx.ask`.

## Criterios de aceptación

- Nombre por defecto y sufijo `(2)` cuando ya existe.
- Cada combinación de RN-03 a RN-06.
- Con 10 importantes, marcar la actual desplaza la más antigua; desmarcarla la restaura; cerrarla la elimina y renumera las demás.
- `recover_interrupted` cierra las sesiones huérfanas y aplica las eliminaciones pendientes.
- `close_session` deja en `error` las actividades `pendiente`.
- Una sesión vacía no queda en la base de datos al cerrarla ni al recuperarla; una con actividades, importante o que desplazó a otra, sí.

## Prohibiciones

- Ningún protocolo sobrescribe un nombre fijado por el usuario ni degrada la importancia.
- No se borra ninguna sesión salvo por RN-09, RN-12 o RN-69.
- No se guardan sesiones fuera de la base de datos.
