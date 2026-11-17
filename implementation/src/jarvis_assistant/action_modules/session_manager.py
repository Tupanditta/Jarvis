"""Módulo Sesión: la parte de datos del ciclo de vida de la sesión (sesion.md).

`SessionManager` es el módulo Sesión: el orquestador lo llama para abrir y cerrar la sesión, y
sus acciones fijan el nombre y la importancia, con prioridad sobre lo que propongan los
protocolos (RN-03 a RN-06). `History` es el módulo Historial (historial.md): consulta las
sesiones y sus actividades, y elimina una sesión tras confirmarlo.
"""
import logging
from collections.abc import Mapping, Sequence
from datetime import tzinfo

from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    ActionContext,
    ActionResult,
    ExpectedType,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.clock import Clock
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import SessionChanged, SessionOverflowed
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository, SessionRow
from jarvis_assistant.speaker.phrases import count

logger = logging.getLogger(__name__)

CLOSED_REASON = "sesión cerrada"  # motivo de las tareas pendientes al cerrar (RN-46)
IMPORTANT_LIMIT = 10  # RN-07


class SessionManager:
    name = "sesion"
    always_allowed = True  # nombrar y marcar la sesión no se restringe
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

    # --- Acciones ------------------------------------------------------------------------------

    def intents(self) -> Sequence[IntentSpec]:
        # `proponer_nombre` e `importante_por_protocolo` no tienen patrones: solo las invoca
        # el módulo Protocolos.
        return (
            IntentSpec(
                "nombrar", ("llama a la sesión {nombre}", "nombra la sesión {nombre}",
                            "ponle a la sesión el nombre {nombre}"),
                (Slot("nombre", SlotType.TEXT),),
                "Poner nombre a la sesión", "Llama a la sesión práctica de redes",
                in_protocols=False,
            ),
            IntentSpec(
                "marcar_importante", ("marca la sesión como importante", "sesión importante",
                                      "esta sesión es importante"),
                description="Marcar la sesión como importante",
                example="Marca la sesión como importante", in_protocols=False,
            ),
            IntentSpec(
                "desmarcar_importante", ("marca la sesión como no importante",
                                         "la sesión no es importante", "quita la importancia"),
                description="Quitar la importancia a la sesión",
                example="La sesión no es importante", in_protocols=False,
            ),
        )  # fmt: skip

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        session = self._current
        if session is None:
            return ActionResult("error", Phrase("general.error"))
        match action:
            case "nombrar":
                return self._rename(session, str(params.get("nombre", "")).strip(), ctx)
            case "marcar_importante":
                return await self._mark(session, ctx, by_user=True)
            case "desmarcar_importante":
                return self._unmark(session, ctx)
            case "proponer_nombre":
                return await self._propose(session, str(params.get("nombre", "")).strip(), ctx)
            case "importante_por_protocolo":
                if session.is_important:
                    return ActionResult("completado")  # RN-05: nada que cambiar
                return await self._mark(session, ctx, by_user=False)
        raise ValueError(f"Acción desconocida: {action}")

    def _rename(self, session: SessionRow, name: str, ctx: ActionContext) -> ActionResult:
        """Nombre fijado por el usuario: ningún protocolo lo cambia después (RN-03)."""
        if not name:
            return ActionResult("error", Phrase("entidad.nombre"))
        self._sessions.rename(session.id, name, by_user=True)
        self._changed(ctx)
        return ActionResult(
            "completado", Phrase("sesion.nombrada", {"nombre": name}),
            description=f"nombrar la sesión {name}",
        )  # fmt: skip

    async def _propose(self, session: SessionRow, name: str, ctx: ActionContext) -> ActionResult:
        """Un protocolo propone un nombre: solo si el usuario no fijó uno, y con su
        confirmación (RN-04)."""
        if not name:
            return ActionResult("error", Phrase("entidad.nombre"))
        if session.name_set_by_module:
            return ActionResult("completado")
        answer = await ctx.ask(
            Phrase("sesion.proponer_nombre", {"nombre": name}), ExpectedType.BOOLEAN,
            metadata={"session_id": session.id, "nombre": name},
        )  # fmt: skip
        if answer.by_user:  # «cancelar»: el protocolo se detiene («Operación cancelada.» ya dicho)
            return ActionResult.cancelled(description=f"proponer el nombre {name}")
        if answer.cancelled or answer.value is not True:
            return ActionResult("completado", description=f"proponer el nombre {name}")
        self._sessions.rename(session.id, name, by_user=False)
        self._changed(ctx)
        return ActionResult(
            "completado", Phrase("sesion.nombrada", {"nombre": name}),
            description=f"nombrar la sesión {name}",
        )  # fmt: skip

    async def _mark(
        self, session: SessionRow, ctx: ActionContext, *, by_user: bool
    ) -> ActionResult:
        """`is_important = 1` y, en la misma transacción, el desbordamiento (RN-07, RN-08).
        Del usuario: también bloquea la importancia. De un protocolo: no toca el bloqueo."""
        with self._db.transaction():
            self._sessions.set_importance(session.id, True, by_user=by_user)
            displaced = None
            if self._sessions.count_important() > IMPORTANT_LIMIT:
                displaced = self._sessions.oldest_important(excluding=session.id)
                if displaced is not None:
                    self._sessions.set_importance(displaced.id, False, by_user=False)
                    self._sessions.mark_pending_purge(displaced.id, True, session.id)
        self._changed(ctx)
        if displaced is not None:
            logger.info("Sesión %d desplazada por la %d", displaced.id, session.id)
            ctx.publish(SessionOverflowed(displaced.id, displaced.name))
            await ctx.say(Phrase("sesion.desbordamiento", {"nombre": displaced.name}))
        speech = Phrase("sesion.importante") if by_user else None
        return ActionResult("completado", speech, description="marcar la sesión como importante")

    def _unmark(self, session: SessionRow, ctx: ActionContext) -> ActionResult:
        """Solo el usuario quita la importancia (RN-06). La sesión desplazada, si la hay,
        recupera la suya."""
        with self._db.transaction():
            self._sessions.set_importance(session.id, False, by_user=True)
            restored = self._sessions.restore_displaced(session.id)
        if restored:
            logger.info("Sesiones restauradas: %s", restored)
        self._changed(ctx)
        return ActionResult(
            "completado", Phrase("sesion.no_importante"),
            description="marcar la sesión como no importante",
        )  # fmt: skip

    def _changed(self, ctx: ActionContext) -> None:
        """Relee la sesión actual y publica sus datos."""
        if self._current is None:
            return
        session = self._sessions.get(self._current.id)
        if session is None:
            return
        self._current = session
        ctx.publish(SessionChanged(session.id, session.name, session.is_important))

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


HISTORY_PANEL = "historial"
HISTORY_LIMIT = 10  # RN-10


class History:
    name = "historial"
    title = "Historial"

    def intents(self) -> Sequence[IntentSpec]:
        return (
            IntentSpec(
                "mostrar", ("muestra el historial", "historial de sesiones",
                            "enséñame el historial"),
                (), "Mostrar las sesiones recientes", "Muestra el historial", HISTORY_PANEL,
            ),
            IntentSpec(
                "actividades", ("actividades de la sesión {id}",
                                "muestra las actividades de la sesión {id}",
                                "qué hice en la sesión {id}", "actividades de esta sesión",
                                "qué he hecho"),
                (Slot("id", SlotType.INTEGER, optional=True),),
                "Mostrar las actividades de una sesión", "Actividades de la sesión doce",
                HISTORY_PANEL,
            ),
            IntentSpec(
                "eliminar", ("elimina la sesión {id}", "borra la sesión {id}"),
                (Slot("id", SlotType.INTEGER),),
                "Eliminar una sesión del historial", "Elimina la sesión doce", HISTORY_PANEL,
                in_protocols=False,
            ),
        )  # fmt: skip

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        match action:
            case "mostrar":
                return self._show(ctx)
            case "actividades":
                return self._activities(params.get("id"), ctx)  # type: ignore[arg-type]
            case "eliminar":
                return await self._delete(int(params["id"]), ctx)  # type: ignore[call-overload]
        raise ValueError(f"Acción desconocida: {action}")

    async def _delete(self, session_id: int, ctx: ActionContext) -> ActionResult:
        """Borrado lógico, siempre con confirmación explícita (RN-11, RN-12)."""
        description = f"eliminar la sesión {session_id}"
        sessions = SessionRepository(ctx.db)
        session = sessions.get(session_id)
        if session is None or session.is_deleted:
            return ActionResult(
                "error", Phrase("historial.no_existe", {"id": session_id}), description
            )
        if ctx.session is not None and session.id == ctx.session.id:
            return ActionResult("error", Phrase("historial.es_actual"), description)
        current = None if ctx.session is None else ctx.session.id
        ctx.publish(events.HistoryShown((session,), current))
        answer = await ctx.ask(
            Phrase("historial.confirmar_eliminar", {"id": session.id, "nombre": session.name}),
            ExpectedType.BOOLEAN,
            metadata={"session_id": session.id},
            subject={"id": session.id, "nombre": session.name},
        )
        if answer.cancelled:
            return ActionResult.cancelled(description=description)  # ya se ha dicho
        if answer.value is not True:
            return ActionResult.cancelled(Phrase("general.operacion_cancelada"), description)
        sessions.soft_delete(session.id)
        logger.info("Sesión %d eliminada", session.id)
        return ActionResult(
            "completado", Phrase("historial.eliminada", {"id": session.id}), description
        )

    def _show(self, ctx: ActionContext) -> ActionResult:
        sessions = SessionRepository(ctx.db).visible_history(HISTORY_LIMIT)
        current = None if ctx.session is None else ctx.session.id
        ctx.publish(events.HistoryShown(tuple(sessions), current))
        return ActionResult(
            "completado",
            Phrase("historial.mostrado", {"sesiones": count(len(sessions), "sesión", "sesiones")}),
        )

    def _activities(self, session_id: int | None, ctx: ActionContext) -> ActionResult:
        if session_id is None and ctx.session is not None:
            session_id = ctx.session.id
        session = None if session_id is None else SessionRepository(ctx.db).get(session_id)
        if session is None or session.is_deleted:  # una sesión eliminada no es consultable
            return ActionResult("error", Phrase("historial.no_existe", {"id": session_id}))
        activities = ActivityRepository(ctx.db).of_session(session.id)
        ctx.publish(events.SessionActivitiesShown(session, tuple(activities)))
        return ActionResult(
            "completado",
            Phrase("historial.actividades", {
                "nombre": session.name,
                "actividades": count(len(activities), "actividad", "actividades"),
            }),
        )  # fmt: skip
