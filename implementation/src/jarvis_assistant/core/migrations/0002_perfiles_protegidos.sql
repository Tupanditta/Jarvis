-- Perfiles como entornos: recordatorios propios y perfiles protegidos con contraseña.
-- Nunca se edita una migración ya publicada: se añade otra.

-- Cada recordatorio pertenece a un perfil. Los que había no eran de ninguno: se descartan
-- (borrado lógico, RES-34).
ALTER TABLE reminders ADD COLUMN profile_id TEXT NOT NULL DEFAULT '';
UPDATE reminders SET status = 'eliminado' WHERE status <> 'eliminado';
CREATE INDEX idx_reminders_profile ON reminders (profile_id, status);

-- Contraseña de un perfil protegido. Vive aquí y no en `profiles.toml`: editar la
-- configuración a mano no quita la protección. Solo se guarda el hash (scrypt con sal).
-- `failed_attempts`: fallos seguidos desde el último acierto; al llegar a 3 se registra un
-- aviso de intrusión y la cuenta vuelve a cero. Quitar la contraseña es `is_deleted = 1`.
CREATE TABLE profile_credentials (
    profile_id      TEXT    PRIMARY KEY CHECK (length(trim(profile_id)) > 0),
    password_hash   TEXT    NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    updated_at      TEXT    NOT NULL,
    is_deleted      INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
);

-- Intentos de acceso no autorizados a un perfil protegido. Se entregan al dueño al entrar y
-- se dan por vistos cuando los confirma (`acknowledged_at`).
CREATE TABLE intrusion_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      TEXT    NOT NULL,
    attempted_at    TEXT    NOT NULL,
    attempts        INTEGER NOT NULL CHECK (attempts > 0),
    origin          TEXT    NOT NULL CHECK (origin IN ('inicio', 'configuracion')),
    acknowledged_at TEXT
);
CREATE INDEX idx_alerts_pending ON intrusion_alerts (profile_id, acknowledged_at);
