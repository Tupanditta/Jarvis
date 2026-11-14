-- Esquema inicial (software/BaseDatos/especificacion-base-datos.md, sección 3).
-- Nunca se edita una migración ya publicada: se añade otra.

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
