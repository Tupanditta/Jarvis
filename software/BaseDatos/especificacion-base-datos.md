# Especificación de la base de datos

Gestor: [persistencia.md](../Modulos/Infraestructura/persistencia.md). Reglas de dominio: [reglas-negocio.md](../reglas-negocio.md). Migraciones: `core/migrations/`.

## 1. Motor y configuración

| Decisión | Valor |
|---|---|
| Motor | SQLite mediante `sqlite3` nativo de Python. |
| Archivo | `jarvis.db` en la carpeta de datos del usuario. |
| Diario | `PRAGMA journal_mode = WAL`. |
| Claves ajenas | `PRAGMA foreign_keys = ON` en cada conexión; todas con `ON DELETE RESTRICT`. |
| Otros | `PRAGMA synchronous = NORMAL`, `PRAGMA busy_timeout = 2000`. |
| Versión del esquema | `PRAGMA user_version` = número de migraciones aplicadas (hoy, 4). Cada migración `NNNN_nombre.sql` se aplica en una transacción que sube la versión. Antes de migrar una base existente se copia a `jarvis.db.bak`. Una base con versión mayor que la del código no se abre. |
| Conexiones | Una por hilo que la usa: la del núcleo y, mientras está abierta, la de la ventana de configuración, que solo toca las tablas de contraseñas y custodia ([perfiles-protegidos.md](../Modulos/Accion/perfiles-protegidos.md)). WAL y `busy_timeout` evitan los bloqueos entre ellas. |
| Fechas | Texto ISO-8601 en UTC con desplazamiento explícito (`2026-11-14T17:32:05+00:00`). Nunca sin zona horaria. Así el orden alfabético coincide con el cronológico. |
| Borrado | Lógico, salvo las sesiones y sus actividades, que se borran del todo (RN-12, RES-34; sección 5). |
| Booleanos | `INTEGER` con `CHECK (x IN (0, 1))` y `NOT NULL`. |

## 2. Entidades

| Tabla | Descripción | Módulos | Migración |
|---|---|---|---|
| `sessions` | Sesiones de uso: nombre, importancia, marcas de prioridad y de ciclo de vida. | Sesión, Historial, Protocolos | 0001 |
| `session_activities` | Tareas ejecutadas en cada sesión. | Historial y, a través de `run_task`, todos | 0001 |
| `reminders` | Recordatorios de un perfil, con fecha límite opcional. | Recordatorio; Perfiles (al retirar un perfil) | 0001, 0002 |
| `reminder_triggers` | Fechas de aviso de cada recordatorio (1 a N). | Recordatorio | 0001 |
| `profile_credentials` | Hash de la contraseña de cada perfil protegido y fallos seguidos. | Núcleo (acceso), configuración, Perfiles | 0002 |
| `intrusion_alerts` | Avisos de intrusión: tres fallos seguidos en un perfil protegido. | Núcleo (acceso y entrega), configuración | 0002, 0003 |
| `profile_permissions` | Módulos restringidos o permitidos de forma explícita a cada perfil. | Permisos; núcleo (alcance de la sesión) | 0003 |
| `admin_keys` | Par de claves X25519 del Acedor, con la privada cifrada. | Núcleo, configuración, Credenciales | 0003 |
| `credential_escrow` | Contraseña de cada perfil protegido sellada con la clave pública del Acedor. | Configuración, núcleo, Credenciales | 0003 |

Relaciones con clave ajena: `sessions` 1—N `session_activities`; `reminders` 1—N `reminder_triggers`; `session_activities` 1—N `session_activities` (subtareas de un protocolo); `sessions` 1—N `sessions` (sesión desplazada por desbordamiento).

Relaciones sin clave ajena: `profile_id` en `reminders`, `profile_credentials`, `intrusion_alerts`, `profile_permissions` y `credential_escrow` es el id de un perfil de `profiles.toml` o `acedor`. Los perfiles no están en la base de datos: un perfil eliminado deja sus filas, retiradas de forma lógica (sección 5).

Los perfiles, los protocolos, el catálogo de aplicaciones, páginas y comandos y el resto de la configuración **no** se guardan en la base de datos: están en archivos TOML ([configuracion.md](../Modulos/Infraestructura/configuracion.md)).

## 3. Esquema

### `0001_initial.sql`

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

### `0002_perfiles_protegidos.sql`

```sql
-- Cada recordatorio pertenece a un perfil. Los que había no eran de ninguno: se descartan.
ALTER TABLE reminders ADD COLUMN profile_id TEXT NOT NULL DEFAULT '';
UPDATE reminders SET status = 'eliminado' WHERE status <> 'eliminado';
CREATE INDEX idx_reminders_profile ON reminders (profile_id, status);

CREATE TABLE profile_credentials (
    profile_id      TEXT    PRIMARY KEY CHECK (length(trim(profile_id)) > 0),
    password_hash   TEXT    NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    updated_at      TEXT    NOT NULL,
    is_deleted      INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
);

CREATE TABLE intrusion_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      TEXT    NOT NULL,
    attempted_at    TEXT    NOT NULL,
    attempts        INTEGER NOT NULL CHECK (attempts > 0),
    origin          TEXT    NOT NULL CHECK (origin IN ('inicio', 'configuracion')),
    acknowledged_at TEXT
);
CREATE INDEX idx_alerts_pending ON intrusion_alerts (profile_id, acknowledged_at);
```

### `0003_acedor.sql`

```sql
CREATE TABLE profile_permissions (
    profile_id TEXT    NOT NULL CHECK (length(trim(profile_id)) > 0),
    module     TEXT    NOT NULL CHECK (length(trim(module)) > 0),
    allowed    INTEGER NOT NULL CHECK (allowed IN (0, 1)),
    updated_at TEXT    NOT NULL,
    PRIMARY KEY (profile_id, module)
);

CREATE TABLE admin_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    public_key  TEXT    NOT NULL,
    private_key TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    is_deleted  INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
);

CREATE TABLE credential_escrow (
    profile_id TEXT    PRIMARY KEY CHECK (length(trim(profile_id)) > 0),
    sealed     TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
);

ALTER TABLE intrusion_alerts ADD COLUMN admin_acknowledged_at TEXT;
```

### `0004_sesiones_renumeradas.sql`

No cambia el esquema: pasa los datos existentes al borrado físico de sesiones (RN-12) y a la numeración 1..N (RN-53).

1. Con `PRAGMA defer_foreign_keys = ON`, borra las sesiones con `is_deleted = 1` y sus actividades. Antes suelta las subtareas (`parent_id = NULL`) y quita la marca de desbordamiento a las sesiones que esas habían desplazado.
2. Renumera las sesiones que quedan por orden de `id` (1, 2, 3…), también en `session_activities.session_id` y en `sessions.displaced_by`. Los ids se cambian en dos pasos (a negativo y de vuelta) para que ninguno choque a medio cambio.
3. Ajusta `sqlite_sequence` para que la siguiente sesión tome el id N+1.

La columna `sessions.is_deleted` se conserva, pero ya no se pone a 1.

## 4. Significado de las columnas

### `sessions`

| Columna | Significado |
|---|---|
| `id` | Identificador numérico que el usuario ve y escribe (RN-53). Siempre de 1 a N, sin huecos, por orden de creación: cambia cuando se borran sesiones anteriores. |
| `name` | Nombre; por defecto, la fecha local de apertura (RN-02). |
| `opened_at` | Momento de apertura. |
| `closed_at`, `close_reason` | Momento y motivo del cierre: `voz` (el usuario escribió la frase de cierre; el valor conserva su nombre de cuando la frase se decía, para no reconstruir la tabla), `salida` (desde la bandeja o fin de sesión de Windows) o `interrumpida` (RN-47). Ambos `NULL` mientras la sesión está abierta. Como máximo hay una sesión abierta. |
| `is_important` | Importancia (RN-05 a RN-08). |
| `name_set_by_module` | 1 si el usuario fijó el nombre mediante el módulo Sesión (RN-03). |
| `importance_locked_by_module` | 1 si el usuario la marcó importante mediante el módulo Sesión (RN-06). |
| `pending_purge_on_close` | 1 si fue desplazada por desbordamiento y se eliminará al cerrar la sesión que la desplazó (RN-08). |
| `displaced_by` | Sesión que la desplazó. Permite restaurarla (RN-08) y saber cuándo eliminarla (RN-09). |
| `is_deleted` | Obsoleta desde la migración 0004: siempre 0. Las consultas siguen filtrando por `is_deleted = 0`. |

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
| `profile_id` | Perfil al que pertenece (RN-56). Cada sesión solo ve y crea los de su perfil, también por id. `''` en los anteriores a la migración 0002, todos `eliminado`. |
| `trigger_at` | Fecha de aviso. Posponer un aviso la actualiza y pone `is_fired = 0` (RN-27). |
| `is_fired` | 1 cuando el aviso ya se disparó. |

### `profile_credentials`

| Columna | Significado |
|---|---|
| `profile_id` | Perfil protegido (o `acedor`). |
| `password_hash` | `scrypt$n$r$p$sal$clave`, con sal y clave en base64 (RNF-32). Nunca la contraseña. |
| `failed_attempts` | Fallos seguidos desde el último acierto. Al tercero se registra un aviso y vuelve a 0; un acierto también la pone a 0 (RN-58). |
| `updated_at` | Último cambio de la contraseña o de la protección. |
| `is_deleted` | 1: el perfil ya no está protegido (contraseña quitada, perfil retirado o Acedor reiniciado). Volver a poner contraseña reutiliza la fila con `is_deleted = 0`. |

### `intrusion_alerts`

| Columna | Significado |
|---|---|
| `profile_id` | Perfil al que se intentó entrar. |
| `attempted_at` | Momento del tercer fallo. |
| `attempts` | Fallos seguidos que lo provocaron (3). |
| `origin` | `inicio` (pantalla dormida) o `configuracion` (desbloqueo en la ventana de configuración). |
| `acknowledged_at` | Cuándo lo confirmó el dueño. `NULL`: se le vuelve a avisar al entrar (RN-59). Retirar el perfil lo rellena. |
| `admin_acknowledged_at` | Cuándo lo confirmó el Acedor, aparte del dueño. |

### `profile_permissions`

| Columna | Significado |
|---|---|
| `profile_id`, `module` | Perfil y nombre de módulo o id de medidor (`recursos`, `ruido`). Clave primaria. |
| `allowed` | 0: restringido; 1: permitido. Sin fila, permitido (RN-62). |
| `updated_at` | Último cambio hecho por el Acedor. |

### `admin_keys` y `credential_escrow`

| Columna | Significado |
|---|---|
| `admin_keys.public_key` | Clave pública X25519 del Acedor, en claro. |
| `admin_keys.private_key` | Clave privada cifrada con una clave derivada de la contraseña del Acedor (scrypt + AES-GCM). Cambiar la contraseña la vuelve a cifrar en la misma fila. |
| `admin_keys.is_deleted` | Solo hay una fila con 0. Activar al Acedor con claves nuevas o reiniciarlo marca la anterior. |
| `credential_escrow.sealed` | Contraseña del perfil sellada con la clave pública del Acedor (X25519 efímera + HKDF-SHA256 + AES-GCM). Solo la abre la privada. |
| `credential_escrow.is_deleted` | 1: el sello ya no vale (contraseña quitada, perfil retirado, claves nuevas o Acedor reiniciado). |

## 5. Reglas de integridad aplicadas por el código

- **Borrado de sesiones (RN-12):** `SessionRepository.delete(ids)` es el único `DELETE` físico del código, en una sola transacción:
  1. pone `parent_id = NULL` en las subtareas de esas sesiones y borra sus `session_activities` (`parent_id` es `ON DELETE RESTRICT` y se comprueba fila a fila);
  2. con `PRAGMA defer_foreign_keys = ON`, quita `displaced_by` y `pending_purge_on_close` a las sesiones que las borradas desplazaron, y borra las sesiones;
  3. renumera las que quedan por orden de `id` en `sessions.id`, `session_activities.session_id` y `sessions.displaced_by`, en orden ascendente para que el id nuevo esté siempre libre;
  4. pone `sqlite_sequence.seq` = número de sesiones, y devuelve los cambios de id, que se publican en `SessionsDeleted`.

  Lo usan la eliminación del historial, la purga del desbordamiento al cerrar (RN-09) y las sesiones vacías (RN-69).
- **Sesiones vacías (RN-69):** vacía es `is_important = 0`, sin actividades y sin ninguna sesión con `displaced_by` igual a su id. Se borra en lugar de cerrarse, al cerrar la sesión o al recuperarla interrumpida; al arrancar, `discard_empty` borra las cerradas que quedaron vacías.
- **Orden del cierre:** marcar `error` las actividades `pendiente`, fijar `closed_at` y `close_reason` y, por último, purgar las desplazadas, porque la purga renumera también la sesión que se cierra.
- **Borrado lógico de lo demás:** eliminar un recordatorio es `status = 'eliminado'` (sus avisos no se modifican; se ignoran por el estado del padre). Quitar una contraseña, retirar un perfil o reiniciar al Acedor es `is_deleted = 1` en `profile_credentials`, `credential_escrow` o `admin_keys`.
- **Retirar un perfil (RN-64):** en una transacción, sus recordatorios pasan a `eliminado`, su contraseña y su sello a `is_deleted = 1` y sus avisos pendientes reciben `acknowledged_at`. Sus filas de `profile_permissions` se conservan.
- **Tres intentos (RN-58):** el fallo, el aviso y la vuelta a cero van en la misma transacción; el aviso se inserta con `failed_attempts` del momento.
- **Límite de importantes (RN-07):** lo aplica el módulo Sesión en la misma transacción que el cambio de importancia.
- **Una sola sesión abierta:** `open_session` solo se llama en `DORMIDO`, tras `recover_interrupted`.
- **Historial (RN-10):**

  ```sql
  SELECT * FROM sessions WHERE is_deleted = 0
  ORDER BY is_important DESC, opened_at DESC, id DESC LIMIT 10;
  ```

- **Recordatorios del panel (RN-50):** `profile_id = :perfil AND status IN ('activo', 'vencido') ORDER BY id`.
- **Avisos pendientes al abrir sesión (RN-22):**

  ```sql
  SELECT t.* FROM reminder_triggers t JOIN reminders r ON r.id = t.reminder_id
  WHERE r.profile_id = :perfil AND r.status = 'activo' AND t.is_fired = 0 AND t.trigger_at <= :now
  ORDER BY t.trigger_at, t.id;
  ```

- **Fechas límite vencidas sin avisar (RN-31):** `profile_id = :perfil AND status = 'activo' AND deadline_at IS NOT NULL AND deadline_at <= :now`.
- **Avisos de intrusión por entregar (RN-59):** del dueño, `profile_id = :perfil AND acknowledged_at IS NULL`; del Acedor, `admin_acknowledged_at IS NULL`. Del más antiguo al más reciente.
- **Módulos restringidos de un perfil (RN-62):** `SELECT module FROM profile_permissions WHERE profile_id = :perfil AND allowed = 0`. Cambiar un permiso es un `INSERT … ON CONFLICT (profile_id, module) DO UPDATE`.

## 6. Cambios respecto al esquema anterior

| Cambio | Motivo |
|---|---|
| `sessions.id` pasa de `TEXT` a `INTEGER` autoincremental. | Es breve y fácil de escribir en una orden (RN-53). |
| `created_at` de `sessions` pasa a llamarse `opened_at`; se añaden `closed_at` y `close_reason`. | Ciclo de vida y recuperación de sesiones interrumpidas (RN-47). |
| Se añaden `pending_purge_on_close` y `displaced_by`. | La marca de desbordamiento no existía y se perdía ante un cierre inesperado (RN-08, RN-09). |
| Se añaden `parent_id` y `finished_at` a `session_activities`. | Tareas de protocolo y duración. |
| `ON DELETE CASCADE` pasa a `ON DELETE RESTRICT`. | Impide un borrado accidental; el borrado de sesiones suelta y borra las filas hijas de forma explícita. |
| Se añaden `NOT NULL`, `CHECK` e índices. | Integridad y rendimiento. |
| Las fechas se normalizan a UTC. | Orden correcto con cambios de hora (RES-35). |
| `reminders.profile_id` (0002). Los recordatorios previos pasan a `eliminado`. | Cada perfil tiene sus recordatorios (RN-56); los anteriores no eran de ninguno. |
| `profile_credentials` e `intrusion_alerts` (0002). | Perfiles protegidos y avisos de intrusión (RN-57 a RN-59). Las contraseñas viven en la base de datos y no en `profiles.toml`: editar la configuración a mano no quita la protección. |
| `profile_permissions`, `admin_keys`, `credential_escrow` e `intrusion_alerts.admin_acknowledged_at` (0003). | Acedor: permisos, custodia de contraseñas y avisos propios (RN-60 a RN-63). |
| Borrado físico y renumeración de sesiones (0004); `sessions.is_deleted` queda sin uso. | Los ids que ve el usuario siguen siendo 1..N tras eliminar (RN-12, RN-53). |
