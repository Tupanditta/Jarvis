"""Repositorios de sesiones, actividades y recordatorios (persistencia.md).

Los módulos no escriben SQL: usan estos repositorios. Cada operación es una transacción;
varias operaciones relacionadas se agrupan con `Database.transaction()`. Los repositorios no
aplican reglas de negocio (límite de importantes, prioridad del usuario): eso es del módulo
Sesión.
"""
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from jarvis_assistant.core.database import Database, from_db, to_db


@dataclass(frozen=True)
class SessionRow:
    id: int
    name: str
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None  # 'voz', 'salida' o 'interrumpida'
    is_important: bool
    name_set_by_module: bool
    importance_locked_by_module: bool
    pending_purge_on_close: bool
    displaced_by: int | None
    is_deleted: bool


@dataclass(frozen=True)
class ActivityRow:
    id: int
    session_id: int
    parent_id: int | None
    module: str
    description: str
    status: str  # 'pendiente', 'error' o 'completado'
    executed_at: datetime
    finished_at: datetime | None


def _optional_date(text: str | None) -> datetime | None:
    return None if text is None else from_db(text)


def _session(row: sqlite3.Row) -> SessionRow:
    return SessionRow(
        id=row["id"],
        name=row["name"],
        opened_at=from_db(row["opened_at"]),
        closed_at=_optional_date(row["closed_at"]),
        close_reason=row["close_reason"],
        is_important=bool(row["is_important"]),
        name_set_by_module=bool(row["name_set_by_module"]),
        importance_locked_by_module=bool(row["importance_locked_by_module"]),
        pending_purge_on_close=bool(row["pending_purge_on_close"]),
        displaced_by=row["displaced_by"],
        is_deleted=bool(row["is_deleted"]),
    )


def _activity(row: sqlite3.Row) -> ActivityRow:
    return ActivityRow(
        id=row["id"],
        session_id=row["session_id"],
        parent_id=row["parent_id"],
        module=row["module_name"],
        description=row["task_description"],
        status=row["status"],
        executed_at=from_db(row["executed_at"]),
        finished_at=_optional_date(row["finished_at"]),
    )


class SessionRepository:
    """Tabla `sessions`. Lo usan Sesión e Historial."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, name: str, opened_at: datetime) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (name, opened_at) VALUES (?, ?)", (name, to_db(opened_at))
            )
            return cursor.lastrowid

    def close(self, session_id: int, closed_at: datetime, reason: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET closed_at = ?, close_reason = ? WHERE id = ?",
                (to_db(closed_at), reason, session_id),
            )

    def find_open(self) -> list[SessionRow]:
        rows = self._db.conn.execute("SELECT * FROM sessions WHERE closed_at IS NULL ORDER BY id")
        return [_session(row) for row in rows]

    def get(self, session_id: int) -> SessionRow | None:
        """La sesión, también si está eliminada (`is_deleted`), o None si no existe."""
        row = self._db.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return None if row is None else _session(row)

    def rename(self, session_id: int, name: str, by_user: bool) -> None:
        """Cambia el nombre. `by_user` fija `name_set_by_module` (RN-03)."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET name = ?, name_set_by_module = max(name_set_by_module, ?)"
                " WHERE id = ?",
                (name, int(by_user), session_id),
            )

    def set_importance(self, session_id: int, important: bool, by_user: bool) -> None:
        """Cambia la importancia. Con `by_user`, el bloqueo sigue a la importancia (RN-06)."""
        with self._db.transaction() as conn:
            if by_user:
                conn.execute(
                    "UPDATE sessions SET is_important = ?, importance_locked_by_module = ?"
                    " WHERE id = ?",
                    (int(important), int(important), session_id),
                )
            else:
                conn.execute(
                    "UPDATE sessions SET is_important = ? WHERE id = ?",
                    (int(important), session_id),
                )

    def count_important(self) -> int:
        return self._db.conn.execute(
            "SELECT count(*) FROM sessions WHERE is_important = 1 AND is_deleted = 0"
        ).fetchone()[0]

    def oldest_important(self, excluding: int) -> SessionRow | None:
        row = self._db.conn.execute(
            "SELECT * FROM sessions WHERE is_important = 1 AND is_deleted = 0 AND id != ?"
            " ORDER BY opened_at ASC, id ASC LIMIT 1",
            (excluding,),
        ).fetchone()
        return None if row is None else _session(row)

    def mark_pending_purge(self, session_id: int, marked: bool, displaced_by: int | None) -> None:
        """Pone o quita la marca de desbordamiento (RN-08). No cambia la importancia."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET pending_purge_on_close = ?, displaced_by = ? WHERE id = ?",
                (int(marked), displaced_by if marked else None, session_id),
            )

    def purge_pending(self, displaced_by: int) -> list[int]:
        """Elimina (borrado lógico) las sesiones desplazadas por `displaced_by` (RN-09)."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT id FROM sessions WHERE displaced_by = ? AND pending_purge_on_close = 1"
                " AND is_deleted = 0 ORDER BY id",
                (displaced_by,),
            ).fetchall()
            ids = [row["id"] for row in rows]
            conn.executemany("UPDATE sessions SET is_deleted = 1 WHERE id = ?", [(i,) for i in ids])
            return ids

    def restore_displaced(self, displaced_by: int) -> list[int]:
        """Devuelve la importancia a las sesiones que desplazó `displaced_by` y les quita la
        marca de desbordamiento (RN-08, restauración)."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT id FROM sessions WHERE displaced_by = ? AND pending_purge_on_close = 1"
                " AND is_deleted = 0 ORDER BY id",
                (displaced_by,),
            ).fetchall()
            ids = [row["id"] for row in rows]
            conn.executemany(
                "UPDATE sessions SET is_important = 1, pending_purge_on_close = 0,"
                " displaced_by = NULL WHERE id = ?",
                [(i,) for i in ids],
            )
            return ids

    def soft_delete(self, session_id: int) -> None:
        with self._db.transaction() as conn:
            conn.execute("UPDATE sessions SET is_deleted = 1 WHERE id = ?", (session_id,))

    def visible_history(self, limit: int = 10) -> list[SessionRow]:
        """Sesiones visibles: primero las importantes y, después, las más recientes (RN-10)."""
        rows = self._db.conn.execute(
            "SELECT * FROM sessions WHERE is_deleted = 0"
            " ORDER BY is_important DESC, opened_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [_session(row) for row in rows]

    def name_exists(self, name: str) -> bool:
        """Si alguna sesión no eliminada tiene ese nombre, sin distinguir mayúsculas."""
        wanted = name.strip().casefold()
        rows = self._db.conn.execute("SELECT name FROM sessions WHERE is_deleted = 0")
        return any(row["name"].strip().casefold() == wanted for row in rows)


class ActivityRepository:
    """Tabla `session_activities`. Lo usan `run_task` e Historial."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def add(
        self,
        session_id: int,
        module: str,
        description: str,
        at: datetime,
        parent_id: int | None = None,
    ) -> int:
        """Registra una tarea en `pendiente`."""
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO session_activities"
                " (session_id, parent_id, module_name, task_description, status, executed_at)"
                " VALUES (?, ?, ?, ?, 'pendiente', ?)",
                (session_id, parent_id, module, description, to_db(at)),
            )
            return cursor.lastrowid

    def finish(
        self,
        activity_id: int,
        status: str,
        description: str | None = None,
        at: datetime | None = None,
    ) -> None:
        """Fija el estado final y, si se indican, la descripción y el momento del fin."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE session_activities SET status = ?,"
                " task_description = coalesce(?, task_description),"
                " finished_at = coalesce(?, finished_at) WHERE id = ?",
                (status, description, None if at is None else to_db(at), activity_id),
            )

    def fail_pending(self, session_id: int, reason: str, at: datetime | None = None) -> None:
        """Pasa a `error` las tareas pendientes de la sesión, con su motivo (RN-46)."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE session_activities SET status = 'error',"
                " task_description = task_description || ' (' || ? || ')',"
                " finished_at = coalesce(?, finished_at)"
                " WHERE session_id = ? AND status = 'pendiente'",
                (reason, None if at is None else to_db(at), session_id),
            )

    def of_session(self, session_id: int) -> list[ActivityRow]:
        rows = self._db.conn.execute(
            "SELECT * FROM session_activities WHERE session_id = ? ORDER BY id", (session_id,)
        )
        return [_activity(row) for row in rows]


@dataclass(frozen=True)
class TriggerRow:
    id: int
    reminder_id: int
    at: datetime
    is_fired: bool


@dataclass(frozen=True)
class ReminderRow:
    id: int
    content: str
    created_at: datetime
    deadline: datetime | None
    status: str  # 'activo', 'vencido' o 'eliminado'
    triggers: tuple[TriggerRow, ...]  # por fecha

    @property
    def pending(self) -> tuple[TriggerRow, ...]:
        """Avisos que aún no se han dado."""
        return tuple(trigger for trigger in self.triggers if not trigger.is_fired)

    @property
    def next_trigger(self) -> datetime | None:
        return min((trigger.at for trigger in self.pending), default=None)

    @property
    def last_fired(self) -> TriggerRow | None:
        """El último aviso ya dado: el que se pospone (RN-27)."""
        fired = [trigger for trigger in self.triggers if trigger.is_fired]
        return max(fired, key=lambda trigger: (trigger.at, trigger.id), default=None)


def _trigger(row: sqlite3.Row) -> TriggerRow:
    return TriggerRow(
        id=row["id"],
        reminder_id=row["reminder_id"],
        at=from_db(row["trigger_at"]),
        is_fired=bool(row["is_fired"]),
    )


class ReminderRepository:
    """Tablas `reminders` y `reminder_triggers`. Lo usa Recordatorio. Eliminar es cambiar el
    estado a `eliminado`: los avisos no se tocan (RN-13).

    Cada recordatorio es de un perfil (`profile_id`): el repositorio solo ve y crea los del
    perfil con el que se construye. Los de otro perfil no existen para él, tampoco por id."""

    def __init__(self, db: Database, profile_id: str = "") -> None:
        self._db = db
        self._profile = profile_id

    def create(
        self, content: str, triggers: Sequence[datetime], deadline: datetime | None, at: datetime
    ) -> int:
        """El recordatorio y sus avisos, en una transacción."""
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO reminders (content, created_at, deadline_at, profile_id)"
                " VALUES (?, ?, ?, ?)",
                (content, to_db(at), None if deadline is None else to_db(deadline), self._profile),
            )
            reminder_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO reminder_triggers (reminder_id, trigger_at) VALUES (?, ?)",
                [(reminder_id, to_db(moment)) for moment in triggers],
            )
            return reminder_id

    def get(self, reminder_id: int) -> ReminderRow | None:
        row = self._db.conn.execute(
            "SELECT * FROM reminders WHERE id = ? AND profile_id = ?", (reminder_id, self._profile)
        ).fetchone()
        return None if row is None else self._reminder(row)

    def listable(self) -> list[ReminderRow]:
        """Activos y vencidos, por identificador: el orden del panel (RN-50)."""
        rows = self._db.conn.execute(
            "SELECT * FROM reminders WHERE profile_id = ? AND status IN ('activo', 'vencido')"
            " ORDER BY id",
            (self._profile,),
        ).fetchall()
        return [self._reminder(row) for row in rows]

    def due_triggers(self, now: datetime) -> list[TriggerRow]:
        """Avisos no dados de recordatorios activos cuya fecha ya ha llegado (RN-22)."""
        return self._triggers("t.trigger_at <= ?", now)

    def future_triggers(self, now: datetime) -> list[TriggerRow]:
        """Avisos no dados de recordatorios activos con fecha futura."""
        return self._triggers("t.trigger_at > ?", now)

    def overdue(self, now: datetime) -> list[ReminderRow]:
        """Activos cuya fecha límite ya ha llegado sin avisar de ella (RN-31)."""
        rows = self._db.conn.execute(
            "SELECT * FROM reminders WHERE profile_id = ? AND status = 'activo'"
            " AND deadline_at IS NOT NULL AND deadline_at <= ? ORDER BY id",
            (self._profile, to_db(now)),
        ).fetchall()
        return [self._reminder(row) for row in rows]

    def mark_fired(self, trigger_id: int) -> None:
        with self._db.transaction() as conn:
            conn.execute("UPDATE reminder_triggers SET is_fired = 1 WHERE id = ?", (trigger_id,))

    def reschedule_trigger(self, trigger_id: int, new_at: datetime) -> None:
        """Nueva fecha de un aviso, otra vez pendiente (RN-27)."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE reminder_triggers SET trigger_at = ?, is_fired = 0 WHERE id = ?",
                (to_db(new_at), trigger_id),
            )

    def set_deadline(self, reminder_id: int, deadline: datetime) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE reminders SET deadline_at = ? WHERE id = ? AND profile_id = ?",
                (to_db(deadline), reminder_id, self._profile),
            )

    def set_status(self, reminder_id: int, status: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE reminders SET status = ? WHERE id = ? AND profile_id = ?",
                (status, reminder_id, self._profile),
            )

    def _triggers(self, condition: str, now: datetime) -> list[TriggerRow]:
        # Las fechas se guardan en UTC con el mismo formato: se comparan como texto.
        rows = self._db.conn.execute(
            "SELECT t.* FROM reminder_triggers t JOIN reminders r ON r.id = t.reminder_id"
            " WHERE r.profile_id = ? AND r.status = 'activo' AND t.is_fired = 0"
            f" AND {condition} ORDER BY t.trigger_at, t.id",
            (self._profile, to_db(now)),
        ).fetchall()
        return [_trigger(row) for row in rows]

    def _reminder(self, row: sqlite3.Row) -> ReminderRow:
        triggers = self._db.conn.execute(
            "SELECT * FROM reminder_triggers WHERE reminder_id = ? ORDER BY trigger_at, id",
            (row["id"],),
        ).fetchall()
        return ReminderRow(
            id=row["id"],
            content=row["content"],
            created_at=from_db(row["created_at"]),
            deadline=_optional_date(row["deadline_at"]),
            status=row["status"],
            triggers=tuple(_trigger(trigger) for trigger in triggers),
        )


class PermissionRepository:
    """Tabla `profile_permissions`: qué módulos tiene restringidos cada perfil. Sin fila, el
    módulo está permitido (los permisos por defecto). Solo el Acedor los cambia."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def restricted(self, profile_id: str) -> frozenset[str]:
        rows = self._db.conn.execute(
            "SELECT module FROM profile_permissions WHERE profile_id = ? AND allowed = 0",
            (profile_id,),
        ).fetchall()
        return frozenset(row["module"] for row in rows)

    def all_restricted(self) -> dict[str, frozenset[str]]:
        """Perfil → módulos restringidos (solo los perfiles con alguno)."""
        found: dict[str, set[str]] = {}
        for row in self._db.conn.execute(
            "SELECT profile_id, module FROM profile_permissions WHERE allowed = 0"
        ).fetchall():
            found.setdefault(row["profile_id"], set()).add(row["module"])
        return {profile: frozenset(modules) for profile, modules in found.items()}

    def set_allowed(self, profile_id: str, module: str, allowed: bool, at: datetime) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO profile_permissions (profile_id, module, allowed, updated_at)"
                " VALUES (?, ?, ?, ?) ON CONFLICT (profile_id, module) DO UPDATE SET"
                " allowed = excluded.allowed, updated_at = excluded.updated_at",
                (profile_id, module, int(allowed), to_db(at)),
            )
