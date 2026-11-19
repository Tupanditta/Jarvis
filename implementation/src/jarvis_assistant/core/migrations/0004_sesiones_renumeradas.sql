-- Sesiones numeradas de 1 a N, sin huecos.
-- Nunca se edita una migración ya publicada: se añade otra.

-- Eliminar una sesión pasa a ser un borrado físico: la sesión y sus actividades desaparecen y
-- las posteriores se renumeran. Aquí se aplica a lo que ya había: las sesiones con borrado
-- lógico se borran de verdad y las demás se numeran por orden de creación. `is_deleted` se
-- conserva en el esquema, pero ya no se pone a 1.
PRAGMA defer_foreign_keys = ON;

-- `parent_id` es ON DELETE RESTRICT y se comprueba fila a fila: primero se sueltan las hijas.
UPDATE session_activities SET parent_id = NULL
 WHERE parent_id IN (SELECT id FROM session_activities
                      WHERE session_id IN (SELECT id FROM sessions WHERE is_deleted = 1));
DELETE FROM session_activities
 WHERE session_id IN (SELECT id FROM sessions WHERE is_deleted = 1);
UPDATE sessions SET displaced_by = NULL, pending_purge_on_close = 0
 WHERE displaced_by IN (SELECT id FROM sessions WHERE is_deleted = 1);
DELETE FROM sessions WHERE is_deleted = 1;

CREATE TEMP TABLE session_renumber AS
    SELECT id AS old_id, row_number() OVER (ORDER BY id) AS new_id FROM sessions;

UPDATE session_activities
   SET session_id = (SELECT new_id FROM session_renumber WHERE old_id = session_id);
UPDATE sessions
   SET displaced_by = (SELECT new_id FROM session_renumber WHERE old_id = displaced_by)
 WHERE displaced_by IS NOT NULL;
-- En dos pasos (negativo y vuelta) para que ningún id choque con otro a medio cambiar.
UPDATE sessions SET id = -(SELECT new_id FROM session_renumber WHERE old_id = id);
UPDATE sessions SET id = -id;
UPDATE sqlite_sequence SET seq = (SELECT coalesce(max(id), 0) FROM sessions)
 WHERE name = 'sessions';

DROP TABLE session_renumber;
