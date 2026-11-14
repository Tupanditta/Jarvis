"""Módulo Sesión: la parte de datos del ciclo de vida de la sesión (sesion.md).

Lo llama el orquestador, no una intención de voz. Las acciones por voz (nombrar, importancia)
y el directorio de trabajo llegan con sus fases.
"""
import logging
from datetime import tzinfo

from jarvis_assistant.core.clock import Clock
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import SessionChanged
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository, SessionRow

logger = logging.getLogger(__name__)

CLOSED_REASON = "sesión cerrada"  # motivo de las tareas pendientes al cerrar (RN-46)


class SessionManager:
    name = "sesion"
    title = "Sesión"

    def __init__(
        self, db: Database, clock: Clock, bus: EventBus, *, local_tz: tzinfo | None = None
    ) -> None:
        self._db = db
        self._clock = clock
        self._bus = bus
        self._tz = local_tz  # None: la zona horaria del sistema
        self._sessions = SessionRepository(db)
        self._activities = ActivityRepository(db)
        self._current: SessionRow | None = None

    @property
    def current(self) -> SessionRow | None:
        return self._current

    def open_session(self) -> SessionRow:
        """Crea la sesión con el nombre por defecto y sin importancia (RN-02)."""
        now = self._clock.now()
        session_id = self._sessions.create(self._default_name(), now)
        session = self._sessions.get(session_id)
        assert session is not None
        self._current = session
        logger.info("Sesión %d abierta", session.id)
        self._bus.publish(SessionChanged(session.id, session.name, session.is_important))
        return session

    def close_session(self, reason: str) -> None:
        """Cierra la sesión actual con motivo `voz` o `salida` (RN-09, RN-46)."""
        session, self._current = self._current, None
        if session is None:
            return
        self._close(session.id, reason, at=self._clock.now())
        logger.info("Sesión %d cerrada (%s)", session.id, reason)

    def recover_interrupted(self) -> list[int]:
        """Cierra como «interrumpida» cada sesión que quedó abierta (RN-47)."""
        recovered = []
        for session in self._sessions.find_open():
            moments = [
                activity.finished_at or activity.executed_at
                for activity in self._activities.of_session(session.id)
            ]
            self._close(session.id, "interrumpida", at=max(moments, default=session.opened_at))
            logger.info("Sesión %d recuperada como interrumpida", session.id)
            recovered.append(session.id)
        return recovered

    def _close(self, session_id: int, reason: str, *, at) -> None:
        with self._db.transaction():
            self._activities.fail_pending(session_id, CLOSED_REASON, at)
            self._sessions.purge_pending(session_id)
            self._sessions.close(session_id, at, reason)

    def _default_name(self) -> str:
        base = self._clock.now().astimezone(self._tz).date().isoformat()
        name, suffix = base, 2
        while self._sessions.name_exists(name):
            name = f"{base} ({suffix})"
            suffix += 1
        return name
