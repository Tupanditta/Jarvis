# Módulo de acción: Historial

- **Código:** `action_modules/session_manager.py` (compartido con [Sesión](sesion.md)). Nombre de módulo: `historial`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Permitir al usuario consultar las sesiones recientes y sus actividades, y eliminar una o varias sesiones.

## Acciones

| Acción | Parámetros | Panel | Efecto |
|---|---|---|---|
| `mostrar` | — | Historial | Publica `HistoryShown` con las sesiones visibles (RN-10). Dice cuántas hay. |
| `actividades` | `id: INTEGER` (opcional) | Historial | Publica `SessionActivitiesShown` con las actividades de la sesión indicada, o de la actual si no se indica. Dice el nombre de la sesión y el número de actividades. |
| `eliminar` | `id: INTEGER` (opcional) | Historial | Elimina una sesión, o varias elegidas en un diálogo si no se indica id, tras confirmación (RN-11, RN-12). |

Las tres son invocables con una orden escrita. `mostrar` y `actividades` también desde protocolos; `eliminar`, no.

## Reglas

### Sesiones visibles (RN-10)

```sql
SELECT * FROM sessions WHERE is_deleted = 0
ORDER BY is_important DESC, opened_at DESC, id DESC LIMIT 10;
```

Cada apertura con «Hey Jarvis» crea una entrada propia, aunque comparta fecha con otra; una sesión que se cierra vacía no se guarda (RN-69). La sesión actual aparece en la lista, marcada como «actual». Cada fila muestra su identificador numérico, que es lo que el usuario escribe para referirse a ella (RN-53). Los ids van de 1 a N sin huecos.

### Registro de actividades (RF-10)

El registro lo hace `run_task` del orquestador para todos los módulos ([arquitectura.md](../../arquitectura.md), sección 4): inserta la actividad en `pendiente` al empezar la tarea y la actualiza a `completado` o `error` al terminar. Este módulo solo las consulta. Cada actividad tiene módulo, descripción, estado y momento.

### Eliminación

**Con id** («Elimina la sesión doce»): la sesión elegida es esa.

**Sin id** («Elimina sesiones»):

1. Si en el historial solo está la sesión actual: tarea en `error`, «No hay sesiones que eliminar. Solo está la actual.».
2. Se publica `HistoryShown` con todas las sesiones visibles, sin límite, y se pregunta «¿Qué sesiones elimino? Puede decirme, por ejemplo, 1, 3, 5 o 1-5.» (`SESSION_IDS`). Una cancelación o el vencimiento del tiempo terminan la tarea en `error` con el motivo «cancelada».

**Después, para las sesiones elegidas:**

1. Si un id no existe: tarea en `error`, «No existe la sesión {id}.». Si es la sesión actual: tarea en `error`, «No se puede eliminar la sesión actual.». No se elimina ninguna.
2. Se publica `HistoryShown` con solo las elegidas. Si alguna es importante, se dice «Atención: hay importancia marcada en {sesiones}.».
3. Se pregunta (`BOOLEAN`): «¿Elimino la sesión {id}, {nombre}?» o «¿Elimino las sesiones {sesiones}?», con las sesiones como `subject` y sus ids en `metadata`.
4. Solo con un sí se borran (RN-12): `SessionRepository.delete` borra en una transacción las sesiones y sus actividades, quita la marca de desbordamiento a las que desplazaron, renumera las demás por orden de creación (ids 1..N, también en `session_activities.session_id` y `sessions.displaced_by`) y ajusta la secuencia para que la siguiente sesión sea la N+1. Se publica `SessionsDeleted` (ids borrados y cambios de id) y `HistoryShown` con el historial nuevo. Se dice «Sesión {id} eliminada.» o «Sesiones {sesiones} eliminadas.».
5. Con un no, una cancelación o el vencimiento del tiempo, no se elimina nada y la tarea queda en `error` con el motivo «cancelada».

Si la sesión actual cambia de id al renumerar, la sesión en curso sigue con su id nuevo.

## Datos

Tablas `sessions` y `session_activities`, mediante `SessionRepository` y `ActivityRepository` ([especificacion-base-datos.md](../../BaseDatos/especificacion-base-datos.md)).

## Eventos

`HistoryShown`, `SessionActivitiesShown`, `SessionsDeleted`; `DialogueOpened` a través de `ctx.ask`.

## Criterios de aceptación

- Orden y límite de RN-10 con más de 10 sesiones y con mezcla de importantes.
- `actividades` sin id usa la sesión actual.
- `eliminar` con id: inexistente, sesión actual, confirmación afirmativa, negativa y vencida.
- `eliminar` sin id: solo la actual; lista («1, 3, 5») e intervalo («1-5»); un id inexistente o el de la actual entre los elegidos; aviso de importancia; cancelación en cada pregunta.
- Tras eliminar, ni las sesiones ni sus actividades están en la base de datos; las demás conservan sus actividades y sus marcas de desbordamiento con el id nuevo; los ids son 1..N y la siguiente sesión es la N+1 (RNF-12).
- Una subtarea de protocolo de una sesión borrada no impide borrarla (`parent_id` es `ON DELETE RESTRICT`).

## Prohibiciones

- No se elimina ninguna sesión sin confirmación explícita.
- No se elimina la sesión actual.
- No se guardan sesiones ni actividades fuera de la base de datos.
