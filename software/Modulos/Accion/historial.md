# Módulo de acción: Historial

- **Código:** `action_modules/session_manager.py` (compartido con [Sesión](sesion.md)). Nombre de módulo: `historial`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Permitir al usuario consultar las sesiones recientes y sus actividades, y eliminar una sesión por su identificador.

## Acciones

| Acción | Parámetros | Panel | Efecto |
|---|---|---|---|
| `mostrar` | — | Historial | Publica `HistoryShown` con las sesiones visibles (RN-10). Dice cuántas hay. |
| `actividades` | `id: INTEGER` (opcional) | Historial | Publica `SessionActivitiesShown` con las actividades de la sesión indicada, o de la actual si no se indica. Dice el nombre de la sesión y el número de actividades. |
| `eliminar` | `id: INTEGER` | Historial | Elimina la sesión tras confirmación (RN-11, RN-12). |

Las tres son invocables con una orden escrita. `mostrar` y `actividades` también desde protocolos; `eliminar`, no.

## Reglas

### Sesiones visibles (RN-10)

```sql
SELECT * FROM sessions WHERE is_deleted = 0
ORDER BY is_important DESC, opened_at DESC LIMIT 10;
```

Cada apertura con «Hey Jarvis» crea una entrada propia, aunque comparta fecha con otra. La sesión actual aparece en la lista, marcada como «actual». Cada fila muestra su identificador numérico, que es lo que el usuario escribe para referirse a ella (RN-53).

### Registro de actividades (RF-10)

El registro lo hace `run_task` del orquestador para todos los módulos ([arquitectura.md](../../arquitectura.md), sección 4): inserta la actividad en `pendiente` al empezar la tarea y la actualiza a `completado` o `error` al terminar. Este módulo solo las consulta. Cada actividad tiene módulo, descripción, estado y momento.

### Eliminación por identificador

1. Si el identificador no existe o la sesión ya está eliminada: tarea en `error`, «No existe la sesión {id}.».
2. Si es la sesión actual: tarea en `error`, «No se puede eliminar la sesión actual.».
3. Si existe: se publica `HistoryShown` con solo esa sesión y se pregunta (`BOOLEAN`), con la sesión como `subject` y su id en `metadata`.
4. Solo con un sí: `is_deleted = 1`. Con un no, una cancelación o el vencimiento del tiempo, no se elimina y la tarea queda en `error` con el motivo «cancelada».

Las actividades de una sesión eliminada dejan de ser consultables: `actividades` responde como si no existiera.

## Datos

Tablas `sessions` y `session_activities`, mediante `SessionRepository` y `ActivityRepository`.

## Criterios de aceptación

- Orden y límite de RN-10 con más de 10 sesiones y con mezcla de importantes.
- `actividades` sin id usa la sesión actual.
- `eliminar`: id inexistente, sesión actual, confirmación afirmativa, negativa y vencida.
- Tras eliminar, la fila sigue en la base de datos (RNF-12).

## Prohibiciones

- No se elimina ninguna sesión sin confirmación explícita.
- No se usa `DELETE` físico.
- No se guardan sesiones ni actividades fuera de la base de datos.
