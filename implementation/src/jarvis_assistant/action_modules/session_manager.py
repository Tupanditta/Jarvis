"""Módulo Sesión: la parte de datos del ciclo de vida de la sesión (sesion.md).

`SessionManager` es el módulo Sesión: el orquestador lo llama para abrir y cerrar la sesión, y
sus acciones fijan el nombre y la importancia, con prioridad sobre lo que propongan los
protocolos (RN-03 a RN-06). `History` es el módulo Historial (historial.md): consulta las
sesiones y sus actividades, y elimina sesiones tras confirmarlo. Eliminar es un borrado
físico que renumera las demás: los ids de las sesiones son siempre 1..N.
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
from jarvis_assistant.core.events import SessionChanged, SessionOverflowed, SessionsDeleted
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository, SessionRow
from jarvis_assistant.speaker.phrases import count, enumeration

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
        bus.subscribe(SessionsDeleted, self._renumbered)

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
        if self._close(session.id, reason, at=self._clock.now()):
            logger.info("Sesión %d vacía: eliminada al cerrar (%s)", session.id, reason)
        else:
            logger.info("Sesión %d cerrada (%s)", session.id, reason)

    def recover_interrupted(self) -> list[int]:
        """Cierra como «interrumpida» cada sesión que quedó abierta (RN-47); la vacía se
        elimina. Devuelve los ids que tenían al recuperarlas."""
        recovered = []
        # Se relee cada vez: borrar una sesión (vacía o desplazada) renumera las demás.
        while opened := self._sessions.find_open():
            session = opened[0]
            moments = [
                activity.finished_at or activity.executed_at
                for activity in self._activities.of_session(session.id)
            ]
            at = max(moments, default=session.opened_at)
            if self._close(session.id, "interrumpida", at=at):
                logger.info("Sesión %d vacía: eliminada al recuperarla", session.id)
            else:
                logger.info("Sesión %d recuperada como interrumpida", session.id)
            recovered.append(session.id)
        return recovered

    def discard_empty(self) -> list[int]:
        """Elimina las sesiones cerradas que quedaron vacías: no se guardan en el historial.
        Devuelve sus ids de antes del borrado."""
        with self._db.transaction():
            empty = self._sessions.closed_empty()
            moves = self._sessions.delete(empty)
        if empty:
            logger.info("Sesiones vacías eliminadas: %s; renumeradas: %s", empty, moves)
            self._bus.publish(SessionsDeleted(tuple(empty), moves))
        return empty

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

    def _renumbered(self, event: SessionsDeleted) -> None:
        """Historial ha borrado sesiones anteriores: la actual cambia de id."""
        if self._current is None or self._current.id not in event.renumbered:
            return
        session = self._sessions.get(event.renumbered[self._current.id])
        if session is None:
            return
        self._current = session
        self._bus.publish(SessionChanged(session.id, session.name, session.is_important))

    def _close(self, session_id: int, reason: str, *, at) -> bool:
        """Cierra la sesión o, si está vacía, la elimina del todo: una sesión sin actividades
        no se guarda en el historial. Devuelve si se ha eliminado."""
        with self._db.transaction():
            if self._sessions.is_empty(session_id):
                # Vacía: no es importante ni ha desplazado a nadie, no hay nada que purgar.
                moves = self._sessions.delete([session_id])
            else:
                self._activities.fail_pending(session_id, CLOSED_REASON, at)
                self._sessions.close(session_id, at, reason)
                # La última: borrar renumera las sesiones, también esta.
                self._sessions.purge_pending(session_id)
                return False
        self._bus.publish(SessionsDeleted((session_id,), moves))
        return True

    def _default_name(self) -> str:
        base = self._clock.now().astimezone(self._tz).date().isoformat()
        name, suffix = base, 2
        while self._sessions.name_exists(name):
            name = f"{base} ({suffix})"
            suffix += 1
        return name


HISTORY_PANEL = "historial"
HISTORY_LIMIT = 10  # RN-10


def _ids(session_ids: Sequence[int]) -> str:
    """«3», «3 y 5», «1, 3 y 5»."""
    return enumeration([str(session_id) for session_id in session_ids])


def _named(session_ids: Sequence[int]) -> str:
    """«la sesión 3», «las sesiones 1, 3 y 5»."""
    if len(session_ids) == 1:
        return f"la sesión {session_ids[0]}"
    return f"las sesiones {_ids(session_ids)}"


def _deletion(session_ids: Sequence[int]) -> str:
    """Descripción de la tarea: «eliminar la sesión 3», «eliminar las sesiones 1, 3 y 5»."""
    return f"eliminar {_named(session_ids)}"


class History:
    name = "historial"
    title = "Historial"

    def intents(self) -> Sequence[IntentSpec]:
        return (
            IntentSpec(
                "mostrar", ("muestra el historial", "historial de sesiones",
                            "enséñame el historial"),
                (), "Mostrar las sesiones recientes", "Muestra el historial", HISTORY_PANEL,
                record=False,
            ),
            IntentSpec(
                "actividades", ("actividades de la sesión {id}",
                                "muestra las actividades de la sesión {id}",
                                "qué hice en la sesión {id}", "actividades de esta sesión",
                                "qué he hecho"),
                (Slot("id", SlotType.INTEGER, optional=True),),
                "Mostrar las actividades de una sesión", "Actividades de la sesión doce",
                HISTORY_PANEL, record=False,
            ),
            IntentSpec(
                "eliminar", ("elimina sesiones", "borra sesiones", "elimina sesiones del historial",
                             "borra sesiones del historial", "elimina la sesión {id}",
                             "borra la sesión {id}"),
                (Slot("id", SlotType.INTEGER, optional=True),),
                "Eliminar sesiones del historial", "Elimina sesiones", HISTORY_PANEL,
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
                return await self._delete(params.get("id"), ctx)  # type: ignore[arg-type]
        raise ValueError(f"Acción desconocida: {action}")

    async def _delete(self, session_id: int | None, ctx: ActionContext) -> ActionResult:
        """Borrado físico de una o varias sesiones, siempre con confirmación explícita
        (RN-11, RN-12). Sin id se muestra el historial y se pregunta cuáles: «1, 3, 5» o
        «1-5». Las demás se renumeran: los ids siguen siendo 1..N."""
        sessions = SessionRepository(ctx.db)
        current = None if ctx.session is None else ctx.session.id
        if session_id is not None:
            chosen: tuple[int, ...] = (int(session_id),)
        else:
            shown = sessions.visible_history(None)
            if all(session.id == current for session in shown):
                return ActionResult("error", Phrase("historial.nada_que_eliminar"),
                                    "eliminar sesiones")  # fmt: skip
            ctx.publish(events.HistoryShown(tuple(shown), current))
            answer = await ctx.ask(Phrase("historial.cuales_eliminar"), ExpectedType.SESSION_IDS)
            if answer.cancelled:
                return ActionResult.cancelled(description="eliminar sesiones")  # ya se ha dicho
            chosen = tuple(answer.value)  # type: ignore[arg-type]
        description = _deletion(chosen)
        selected = []
        for wanted in chosen:
            session = sessions.get(wanted)
            if session is None or session.is_deleted:
                return ActionResult(
                    "error", Phrase("historial.no_existe", {"id": wanted}), description
                )
            if wanted == current:
                return ActionResult("error", Phrase("historial.es_actual"), description)
            selected.append(session)
        ctx.publish(events.HistoryShown(tuple(selected), current))
        important = [session.id for session in selected if session.is_important]
        if important:
            await ctx.say(Phrase("historial.aviso_importantes", {"sesiones": _named(important)}))
        if len(selected) == 1:
            (only,) = selected
            subject: dict[str, object] = {"id": only.id, "nombre": only.name}
            question = Phrase("historial.confirmar_eliminar", subject)
            metadata: dict[str, object] = {"session_id": only.id}
        else:
            subject = {"sesiones": _ids(chosen)}
            question = Phrase("historial.confirmar_eliminar_varias", subject)
            metadata = {"session_ids": chosen}
        answer = await ctx.ask(
            question, ExpectedType.BOOLEAN, metadata=metadata, subject=subject
        )
        if answer.cancelled:
            return ActionResult.cancelled(description=description)  # ya se ha dicho
        if answer.value is not True:
            return ActionResult.cancelled(Phrase("general.operacion_cancelada"), description)
        renumbered = sessions.delete(chosen)
        logger.info("Sesiones eliminadas: %s; renumeradas: %s", list(chosen), renumbered)
        ctx.publish(events.SessionsDeleted(chosen, renumbered))
        current = None if current is None else renumbered.get(current, current)
        ctx.publish(events.HistoryShown(tuple(sessions.visible_history(HISTORY_LIMIT)), current))
        if len(chosen) == 1:
            speech = Phrase("historial.eliminada", {"id": chosen[0]})
        else:
            speech = Phrase("historial.eliminadas", {"sesiones": _ids(chosen)})
        return ActionResult("completado", speech, description)

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
