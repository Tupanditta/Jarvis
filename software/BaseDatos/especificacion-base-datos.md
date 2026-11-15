# Especificación de la base de datos

Gestor: [persistencia.md](../Modulos/Infraestructura/persistencia.md). Reglas de dominio: [reglas-negocio.md](../reglas-negocio.md).

## 1. Motor y configuración

| Decisión | Valor |
|---|---|
| Motor | SQLite mediante `sqlite3` nativo de Python. |
| Archivo | `jarvis.db` en la carpeta de datos del usuario. |
| Diario | `PRAGMA journal_mode = WAL`. |
| Claves ajenas | `PRAGMA foreign_keys = ON` en cada conexión; todas con `ON DELETE RESTRICT`. |
| Otros | `PRAGMA synchronous = NORMAL`, `PRAGMA busy_timeout = 2000`. |
| Versión del esquema | `PRAGMA user_version`; migraciones numeradas. |
| Fechas | Texto ISO-8601 en UTC con desplazamiento explícito (`2026-11-14T17:32:05+00:00`). Nunca sin zona horaria. Así el orden alfabético coincide con el cronológico. |
| Borrado | Lógico. Sin `DELETE` físico. |
| Booleanos | `INTEGER` con `CHECK (x IN (0, 1))` y `NOT NULL`. |

## 2. Entidades

| Tabla | Descripción | Módulos |
|---|---|---|
| `sessions` | Sesiones de uso: nombre, importancia, marcas de prioridad y de ciclo de vida. | Sesión, Historial, Protocolos |
| `session_activities` | Tareas ejecutadas en cada sesión. | Historial y, a través de `run_task`, todos |
| `reminders` | Recordatorios con fecha límite opcional. | Recordatorio |
| `reminder_triggers` | Fechas de aviso de cada recordatorio (1 a N). | Recordatorio |

Relaciones: `sessions` 1—N `session_activities`; `reminders` 1—N `reminder_triggers`; `session_activities` 1—N `session_activities` (subtareas de un protocolo); `sessions` 1—N `sessions` (sesión desplazada por desbordamiento).

Los protocolos, el catálogo de aplicaciones y páginas y el resto de la configuración **no** se guardan en la base de datos: están en archivos TOML ([configuracion.md](../Modulos/Infraestructura/configuracion.md)).

## 3. Esquema

Migración `0001_initial.sql`:

```sql
CREATE TABLE sessions (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    name                        TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    opened_at                   TEXT    NOT NULL,
    closed_at                   TEXT,
    close_reason                TEXT    CHECK (close_reason IN ('voz', 'salida', 'interrumpida')),
    is_important                INTEGER NOT NULL DEFAULT 0 CHECK (is_important IN (0, 1)),
    name_set_by_module          INTEGER NOT NULL DEFAULT 0 CHECK (name_set_by_module IN (0, 1)),
    importance_locked_by_module INTEGER NOT NULL DEFAULT 0 CHECK (importance_locked_by_module IN (0, 1)),
    pending_purge_on_close      INTEGER NOT NULL DEFAULT 0 CHECK (pending_purge_on_close IN (0, 1)),
    displaced_by                INTEGER REFERENCES sessions(id) ON DELETE RESTRICT,
    is_deleted                  INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    CHECK ((closed_at IS NULL) = (close_reason IS NULL))
);
CREATE INDEX idx_sessions_history ON sessions (is_deleted, is_important DESC, opened_at DESC);

CREATE TABLE session_activities (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id) ON DELETE RESTRICT,
    parent_id        INTEGER REFERENCES session_activities(id) ON DELETE RESTRICT,
    module_name      TEXT    NOT NULL,
    task_description TEXT    NOT NULL,
    status           TEXT    NOT NULL CHECK (status IN ('pendiente', 'error', 'completado')),
    executed_at      TEXT    NOT NULL,
    finished_at      TEXT
);
CREATE INDEX idx_activities_session ON session_activities (session_id, id);

CREATE TABLE reminders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT    NOT NULL CHECK (length(trim(content)) > 0),
    created_at  TEXT    NOT NULL,
    deadline_at TEXT,
    status      TEXT    NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'vencido', 'eliminado'))
);
CREATE INDEX idx_reminders_status ON reminders (status);

CREATE TABLE reminder_triggers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_id INTEGER NOT NULL REFERENCES reminders(id) ON DELETE RESTRICT,
    trigger_at  TEXT    NOT NULL,
    is_fired    INTEGER NOT NULL DEFAULT 0 CHECK (is_fired IN (0, 1))
);
CREATE INDEX idx_triggers_pending ON reminder_triggers (is_fired, trigger_at);
```

## 4. Significado de las columnas

### `sessions`

| Columna | Significado |
|---|---|
| `id` | Identificador numérico que el usuario ve y dice (RN-53). |
| `name` | Nombre; por defecto, la fecha local de apertura (RN-02). |
| `opened_at` | Momento de apertura. |
| `closed_at`, `close_reason` | Momento y motivo del cierre: `voz` (el usuario escribió la frase de cierre; el valor conserva su nombre de cuando la frase se decía, para no reconstruir la tabla), `salida` (desde la bandeja o fin de sesión de Windows) o `interrumpida` (RN-47). Ambos `NULL` mientras la sesión está abierta. Como máximo hay una sesión abierta. |
| `is_important` | Importancia (RN-05 a RN-08). |
| `name_set_by_module` | 1 si el usuario fijó el nombre mediante el módulo Sesión (RN-03). |
| `importance_locked_by_module` | 1 si el usuario la marcó importante mediante el módulo Sesión (RN-06). |
| `pending_purge_on_close` | 1 si fue desplazada por desbordamiento y se eliminará al cerrar la sesión que la desplazó (RN-08). |
| `displaced_by` | Sesión que la desplazó. Permite restaurarla (RN-08) y saber cuándo eliminarla (RN-09). |
| `is_deleted` | Borrado lógico (RN-12). |

### `session_activities`

| Columna | Significado |
|---|---|
| `parent_id` | Actividad del protocolo al que pertenece la tarea; `NULL` si no pertenece a ninguno. |
| `module_name` | Nombre estable del módulo (`comandos`, `apertura`…). |
| `task_description` | Texto que se muestra en el panel de actividad y en el historial. |
| `status` | Estado de la tarea (RN-01). Se inserta `pendiente` y se actualiza una vez al terminar. |
| `executed_at`, `finished_at` | Inicio y fin de la tarea. |

### `reminders` y `reminder_triggers`

| Columna | Significado |
|---|---|
| `content` | Texto del recordatorio (RN-20). |
| `deadline_at` | Fecha límite opcional (RN-21). |
| `status` | `activo`, `vencido` (ya se avisó de su fecha límite, RN-31) o `eliminado` (RN-13). |
| `trigger_at` | Fecha de aviso. Posponer un aviso la actualiza y pone `is_fired = 0` (RN-27). |
| `is_fired` | 1 cuando el aviso ya se disparó. |

## 5. Reglas de integridad aplicadas por el código

- **Borrado lógico:** eliminar una sesión es `UPDATE sessions SET is_deleted = 1`; eliminar un recordatorio es `UPDATE reminders SET status = 'eliminado'`. Sus actividades y sus avisos no se modifican; se ignoran por el estado del padre.
- **Límite de importantes (RN-07):** lo aplica el módulo Sesión en la misma transacción que el cambio de importancia.
- **Una sola sesión abierta:** `open_session` solo se llama en `DORMIDO`, tras `recover_interrupted`.
- **Historial (RN-10):**

  ```sql
  SELECT * FROM sessions WHERE is_deleted = 0
  ORDER BY is_important DESC, opened_at DESC LIMIT 10;
  ```

- **Avisos pendientes al abrir sesión (RN-22):**

  ```sql
  SELECT t.* FROM reminder_triggers t JOIN reminders r ON r.id = t.reminder_id
  WHERE r.status = 'activo' AND t.is_fired = 0 AND t.trigger_at <= :now;
  ```

- **Fechas límite vencidas sin avisar (RN-31):** `status = 'activo' AND deadline_at IS NOT NULL AND deadline_at <= :now`.

## 6. Cambios respecto al esquema anterior

| Cambio | Motivo |
|---|---|
| `sessions.id` pasa de `TEXT` a `INTEGER` autoincremental. | Es breve y fácil de escribir en una orden (RN-53). |
| `created_at` de `sessions` pasa a llamarse `opened_at`; se añaden `closed_at` y `close_reason`. | Ciclo de vida y recuperación de sesiones interrumpidas (RN-47). |
| Se añaden `pending_purge_on_close` y `displaced_by`. | La marca de desbordamiento no existía y se perdía ante un cierre inesperado (RN-08, RN-09). |
| Se añaden `parent_id` y `finished_at` a `session_activities`. | Tareas de protocolo y duración. |
| `ON DELETE CASCADE` pasa a `ON DELETE RESTRICT`. | Con borrado lógico la cascada no tenía efecto; `RESTRICT` impide un borrado físico accidental. |
| Se añaden `NOT NULL`, `CHECK` e índices. | Integridad y rendimiento. |
| Las fechas se normalizan a UTC. | Orden correcto con cambios de hora (RES-35). |
