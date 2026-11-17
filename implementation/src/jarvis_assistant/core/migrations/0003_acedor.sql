-- Perfil Acedor: permisos por módulo, claves del Acedor y custodia de contraseñas.
-- Nunca se edita una migración ya publicada: se añade otra.

-- Permisos de cada perfil por módulo. Sin fila, el módulo está permitido (permisos por
-- defecto); restringir es `allowed = 0`. Solo el Acedor los cambia.
CREATE TABLE profile_permissions (
    profile_id TEXT    NOT NULL CHECK (length(trim(profile_id)) > 0),
    module     TEXT    NOT NULL CHECK (length(trim(module)) > 0),
    allowed    INTEGER NOT NULL CHECK (allowed IN (0, 1)),
    updated_at TEXT    NOT NULL,
    PRIMARY KEY (profile_id, module)
);

-- Par de claves X25519 del Acedor (una sola fila activa). La privada va cifrada con una clave
-- derivada de su contraseña (scrypt + AES-GCM). Reiniciar el Acedor es `is_deleted = 1`.
CREATE TABLE admin_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    public_key  TEXT    NOT NULL,
    private_key TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    is_deleted  INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
);

-- Contraseña de cada perfil protegido sellada con la clave pública del Acedor: solo él la
-- puede leer. Quitar la contraseña, retirar el perfil o reiniciar al Acedor es `is_deleted = 1`.
CREATE TABLE credential_escrow (
    profile_id TEXT    PRIMARY KEY CHECK (length(trim(profile_id)) > 0),
    sealed     TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
);

-- El Acedor confirma los avisos de intrusión aparte del dueño del perfil.
ALTER TABLE intrusion_alerts ADD COLUMN admin_acknowledged_at TEXT;
