"""Módulo Recordatorio (recordatorio.md; CU-11, CU-12).

Crea recordatorios con una o varias fechas de aviso y una fecha límite opcional, avisa de
ellos, los pospone y los confirma. La base de datos es la única fuente de verdad: los trabajos
del planificador (`trigger:{id}`, `deadline:{id}`, `autoconfirm:{id}`) solo existen mientras
la sesión está abierta y se recalculan al abrir la siguiente (RN-22).

Privacidad (RES-48): el texto de los recordatorios no se escribe en el registro.
"""
import asyncio
import logging
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, tzinfo
from functools import partial

from jarvis_assistant.core.action_api import (
    OFFER,
    ActionContext,
    ActionResult,
    ExpectedType,
    IntentSpec,
    Phrase,
    ReminderAction,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import ReminderItem
from jarvis_assistant.core.events import ActionRequested, PanelActivated, RemindersChanged
from jarvis_assistant.core.notices import Notice
from jarvis_assistant.core.repositories import ReminderRepository, ReminderRow
from jarvis_assistant.intent_router.normalizer import normalize, tokenize
from jarvis_assistant.intent_router.slots import datetimes
from jarvis_assistant.speaker import formats
from jarvis_assistant.speaker.phrases import count

logger = logging.getLogger(__name__)

PANEL = "recordatorios"
ACTIVE, OVERDUE, DELETED = "activo", "vencido", "eliminado"

# RN-20: sustituciones cerradas al inicio del texto (ya normalizadas).
_REPLACEMENTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("tenemos", "que"), "Tenéis que"),
    (("tengo", "que"), "Tienes que"),
    (("debo",), "Debes"),
)
_TEXT_EDGES = " .,;:!?¿¡\"'«»"
_JOBS = ("trigger:", "deadline:", "autoconfirm:")


def reminder_text(text: str) -> str:
    """Texto del recordatorio (RN-20): sustituciones cerradas al inicio y la primera letra en
    mayúscula. El resto se conserva intacto: sin reglas de conjugación (RES-26)."""
    words = text.strip(_TEXT_EDGES).split()
    for prefix, replacement in _REPLACEMENTS:
        size = len(prefix)
        if len(words) >= size and tuple(normalize(word) for word in words[:size]) == prefix:
            words = [replacement, *words[size:]]
            break
    result = " ".join(words).strip(_TEXT_EDGES)
    return result[:1].upper() + result[1:]


class ReminderManager:
    name = "recordatorio"
    title = "Recordatorios"

    def __init__(self, *, local_tz: tzinfo | None = None) -> None:
        self._tz = local_tz  # None: la zona horaria del sistema
        self._ctx: ActionContext | None = None  # el de la sesión abierta: avisos y panel
        self._last: int | None = None  # el último recordatorio notificado o leído (RN-27)
        self._highlighted: frozenset[int] = frozenset()
        self._fired: list[int] = []  # notificados que aún no se han agrupado en un aviso
        self._flush_pending = False

    # --- Registro ------------------------------------------------------------------------------

    def intents(self) -> Sequence[IntentSpec]:
        index = Slot("n", SlotType.INTEGER)
        return (
            IntentSpec(
                "crear", ("recuérdame {texto}", "recuérdame que {texto}",
                          "crea un recordatorio {texto}", "crea un recordatorio para {texto}"),
                (Slot("texto", SlotType.TEXT),),
                "Crear un recordatorio", "Recuérdame llamar a Ana mañana a las nueve", PANEL,
            ),
            IntentSpec(
                "mostrar", ("recordatorios", "muestra los recordatorios",
                            "qué recordatorios tengo"),
                (), "Mostrar los recordatorios", "Muestra los recordatorios", PANEL,
                record=False,
            ),
            IntentSpec(
                "leer", ("lee el recordatorio {n}", "recordatorio {n}", "lee el {n}"),
                (index,), "Leer un recordatorio", "Lee el recordatorio uno", PANEL,
                in_protocols=False, record=False,
            ),
            # También tras un aviso, que la pide con los avisados en `avisados` (`_offer`).
            IntentSpec(
                "dictar", ("léeme los recordatorios", "lee los recordatorios",
                           "díctame los recordatorios", "dicta los recordatorios"),
                (), "Dictar todos los recordatorios", "Léeme los recordatorios", PANEL,
                in_protocols=False, record=False,
            ),
            # Sin panel: confirmar mira si el panel ya está activo antes de activarlo (RN-25).
            IntentSpec(
                "confirmar", ("confirmar recordatorios {n}", "confirmar recordatorio {n}",
                              "confirmar recordatorios"),
                (Slot("n", SlotType.INTEGER, optional=True),),
                "Confirmar un recordatorio", "Confirmar recordatorios dos", None,
                in_protocols=False,
            ),
            IntentSpec(
                "posponer", ("posponer", "pospón", "más tarde", "posponer {duracion}",
                             "pospón {duracion}", "pospón el recordatorio {n}",
                             "pospón el recordatorio {n} durante {duracion}"),
                (Slot("n", SlotType.INTEGER, optional=True),
                 Slot("duracion", SlotType.DURATION, optional=True)),
                "Posponer un aviso", "Posponer media hora", PANEL, in_protocols=False,
            ),
            IntentSpec(
                "posponer_limite", ("pospón la fecha límite del recordatorio {n} hasta {fecha}",
                                    "cambia la fecha límite del recordatorio {n} hasta {fecha}"),
                (index, Slot("fecha", SlotType.DATETIME)),
                "Posponer la fecha límite",
                "Pospón la fecha límite del recordatorio uno hasta el viernes a las diez",
                PANEL, in_protocols=False,
            ),
            IntentSpec(
                "eliminar", ("elimina el recordatorio {n}", "borra el recordatorio {n}"),
                (index,), "Eliminar un recordatorio", "Elimina el recordatorio tres", PANEL,
                in_protocols=False,
            ),
        )  # fmt: skip

    # --- Sesión --------------------------------------------------------------------------------

    async def on_session_opened(self, ctx: ActionContext) -> None:
        """Avisa de lo que venció sin sesión y programa lo que está por venir (RN-22)."""
        self._ctx = ctx
        self._last, self._highlighted, self._fired = None, frozenset(), []
        reminders = ReminderRepository(ctx.db, ctx.profile)
        now = ctx.clock.now()
        due = reminders.due_triggers(now)
        for trigger in due:
            reminders.mark_fired(trigger.id)
        fired = list(dict.fromkeys(trigger.reminder_id for trigger in due))
        if fired:
            self._notify_fired(fired)  # todos juntos, en un solo aviso
        for reminder in reminders.overdue(now):
            self._notify_deadline(reminder.id)
        for reminder in reminders.listable():
            self._schedule(reminder)
        self._publish()

    async def on_session_closed(self, ctx: ActionContext) -> None:
        """Sin sesión no se dispara nada: los trabajos se pierden, también los plazos de
        autoconfirmación (RN-29)."""
        scheduler = ctx.scheduler or (self._ctx and self._ctx.scheduler)
        if scheduler is not None:
            for job_id in list(scheduler.jobs()):
                if job_id.startswith(_JOBS):
                    scheduler.remove(job_id)
        self._ctx = None
        self._last, self._highlighted, self._fired = None, frozenset(), []

    # --- Acciones ------------------------------------------------------------------------------

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        match action:
            case "crear":
                if ctx.origin == "protocolo":
                    return self._create_from_protocol(params, ctx)
                return await self._create(str(params.get("texto", "")), ctx)
            case "mostrar":
                return self._show(ctx)
            case "leer":
                return self._read(_index(params["n"]), ctx)
            case "dictar":
                notified = params.get("avisados")
                return await self._dictate(
                    None if notified is None else _sequence(notified), ctx  # type: ignore[arg-type]
                )
            case "confirmar":
                n = params.get("n")
                return self._confirm(None if n is None else _index(n), ctx)
            case "posponer":
                n, duration = params.get("n"), params.get("duracion")
                return self._snooze(
                    None if n is None else _index(n),
                    duration if isinstance(duration, timedelta) else None,
                    ctx,
                )
            case "posponer_limite":
                return self._move_deadline(_index(params["n"]), params["fecha"], ctx)  # type: ignore[arg-type]
            case "eliminar":
                return await self._delete(_index(params["n"]), ctx)
        raise ValueError(f"Acción desconocida: {action}")

    # --- Crear ---------------------------------------------------------------------------------

    async def _create(self, raw: str, ctx: ActionContext) -> ActionResult:
        """Orden escrita: la fecha final de la orden es el primer aviso; si no hay, se
        pregunta. Después, otros avisos o la fecha límite (recordatorio.md, «Creación»)."""
        tokens = tokenize(raw.strip())
        now = ctx.clock.now()
        found = datetimes.find_suffix(tokens.words, now, self._default_hour(ctx), self._tz)
        triggers: list[datetime] = []
        text = raw
        if found is not None:
            start, when = found
            text = tokens.original(0, start)
            triggers.append(when)
        content = reminder_text(text)
        if not content:
            return ActionResult("error", Phrase("recordatorio.vacio"))
        if triggers and triggers[0] <= now:
            await ctx.say(Phrase("entidad.fecha_pasada"))
            triggers.clear()
        subject = {"texto": content}
        if not triggers:
            first = await self._ask_when(ctx, subject)
            if first is None:
                return ActionResult.cancelled()  # «Operación cancelada.» ya se ha dicho
            triggers.append(first)
        deadline = await self._ask_more(ctx, triggers, subject)
        reminder_id = ReminderRepository(ctx.db, ctx.profile).create(
            content, triggers, deadline, ctx.clock.now()
        )
        logger.info("Recordatorio %d creado con %d avisos", reminder_id, len(triggers))
        self._scheduled(reminder_id, ctx)
        return ActionResult(
            "completado", Phrase("recordatorio.creado", {"fecha": self._moment(min(triggers), ctx)})
        )

    async def _ask_when(self, ctx: ActionContext, subject: Mapping[str, object]) -> datetime | None:
        """«¿Cuándo quiere que se lo recuerde?» hasta una fecha futura, o None si se cancela."""
        while True:
            answer = await ctx.ask(
                Phrase("recordatorio.cuando"), ExpectedType.DATETIME, subject=subject
            )
            if answer.cancelled or not isinstance(answer.value, datetime):
                return None
            if answer.value > ctx.clock.now():
                return answer.value
            await ctx.say(Phrase("entidad.fecha_pasada"))

    async def _ask_more(
        self, ctx: ActionContext, triggers: list[datetime], subject: Mapping[str, object]
    ) -> datetime | None:
        """Otros avisos (hasta el máximo) o la fecha límite. Una negación, «cancelar» o el
        tiempo agotado terminan sin más: el recordatorio se guarda con lo que tiene."""
        limit = ctx.config.settings.reminders.max_triggers
        while True:
            answer = await ctx.ask(
                Phrase("recordatorio.mas"), ExpectedType.REMINDER_ACTION, subject=subject
            )
            if answer.cancelled or not isinstance(answer.value, ReminderAction):
                return None
            action = answer.value
            if action.when <= ctx.clock.now():
                await ctx.say(Phrase("entidad.fecha_pasada"))
            elif action.kind == "aviso":
                if len(triggers) >= limit:
                    await ctx.say(Phrase("recordatorio.max_avisos"))
                else:
                    triggers.append(action.when)
            elif action.when < max(triggers):
                await ctx.say(Phrase("recordatorio.limite_anterior"))
            else:
                return action.when

    def _create_from_protocol(
        self, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        """Desde un protocolo: texto, avisos y fecha límite en los parámetros; sin diálogo."""
        content = reminder_text(str(params.get("texto", "")))
        if not content:
            return ActionResult("error", Phrase("recordatorio.vacio"))
        now = ctx.clock.now()
        moments = [self._as_moment(value, ctx) for value in _sequence(params.get("avisos"))]
        triggers = [moment for moment in moments if moment is not None]
        deadline = None
        if params.get("limite") is not None:
            deadline = self._as_moment(params["limite"], ctx)
            if deadline is None:
                return ActionResult("error", Phrase("entidad.fecha"))
        if not triggers or len(triggers) != len(moments):
            return ActionResult("error", Phrase("entidad.fecha"))
        if any(moment <= now for moment in (*triggers, *([deadline] if deadline else []))):
            return ActionResult("error", Phrase("entidad.fecha_pasada"))
        if len(triggers) > ctx.config.settings.reminders.max_triggers:
            return ActionResult("error", Phrase("recordatorio.max_avisos"))
        if deadline is not None and deadline < max(triggers):
            return ActionResult("error", Phrase("recordatorio.limite_anterior"))
        reminders = ReminderRepository(ctx.db, ctx.profile)
        reminder_id = reminders.create(content, triggers, deadline, now)
        self._scheduled(reminder_id, ctx)
        return ActionResult(
            "completado", Phrase("recordatorio.creado", {"fecha": self._moment(min(triggers), ctx)})
        )

    def _as_moment(self, value: object, ctx: ActionContext) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else None
        if isinstance(value, str):
            return datetimes.parse(
                normalize(value).split(), ctx.clock.now(), self._default_hour(ctx), self._tz
            )
        return None

    # --- Consultar -----------------------------------------------------------------------------

    def _show(self, ctx: ActionContext) -> ActionResult:
        total = len(self._publish(ctx))
        if not total:
            return ActionResult("completado", Phrase("recordatorio.ninguno"))
        return ActionResult(
            "completado",
            Phrase("recordatorio.lista",
                   {"recordatorios": count(total, "recordatorio", "recordatorios")}),
        )  # fmt: skip

    def _read(self, n: int, ctx: ActionContext) -> ActionResult:
        """Dice el texto; si está vencido, también su fecha límite. Leer no confirma (RN-24).
        Al terminar de leer uno sin avisos pendientes o vencido empieza el plazo de RN-29."""
        reminder = self._at(n, ctx)
        if reminder is None:
            return _no_item(n)
        self._last, self._highlighted = reminder.id, frozenset({reminder.id})
        self._publish(ctx)
        if reminder.status == OVERDUE and reminder.deadline is not None:
            phrase = Phrase(
                "recordatorio.lectura_vencido",
                {"texto": reminder.content, "fecha": self._moment(reminder.deadline, ctx)},
            )
        else:
            phrase = Phrase("recordatorio.lectura", {"texto": reminder.content})
        last_one = reminder.status == OVERDUE or not reminder.pending
        on_spoken = partial(self._start_autoconfirm, reminder.id) if last_one else None
        return ActionResult("completado", phrase, on_spoken=on_spoken)

    async def _dictate(self, notified: Sequence[int] | None, ctx: ActionContext) -> ActionResult:
        """Dice seguidos los textos, cada uno con su muletilla («El primero…», «El siguiente…»,
        «Y por último…»); de un vencido, también su fecha límite.

        `notified`: los que acaba de avisar un aviso. Antes se pregunta si se dictan (BOOLEAN);
        los ya confirmados o eliminados entretanto no se dicen. Sin `notified` (la orden
        «léeme los recordatorios»), todos los del panel, sin preguntar. Como al leer uno, no
        confirma nada y empieza el plazo de RN-29 de los que ya no tienen avisos pendientes."""
        description = "Dictar los recordatorios"
        wanted = None if notified is None else set(notified)
        if wanted is not None:
            listable = ReminderRepository(ctx.db, ctx.profile).listable()
            chosen = [r for r in listable if r.id in wanted]
            if not chosen:
                return ActionResult("completado", description=description)  # ya atendidos
            question = (
                Phrase("recordatorio.ofrecer_uno") if len(chosen) == 1
                else Phrase("recordatorio.ofrecer_varios")
            )  # fmt: skip
            answer = await ctx.ask(question, ExpectedType.BOOLEAN, metadata={OFFER: True})
            if answer.cancelled:
                return ActionResult.cancelled(description=description)
            if answer.value is not True:
                return ActionResult(
                    "completado", Phrase("recordatorio.no_dictar"), description=description
                )
        # Pudo cambiar mientras se preguntaba.
        listed = ReminderRepository(ctx.db, ctx.profile).listable()
        chosen = [r for r in listed if wanted is None or r.id in wanted]
        if not chosen:
            return ActionResult(
                "completado", Phrase("recordatorio.ninguno"), description=description
            )
        self._last, self._highlighted = chosen[-1].id, frozenset(r.id for r in chosen)
        self._publish(ctx)
        phrases: list[Phrase] = []
        for position, reminder in enumerate(chosen):
            phrase_id = _dictation_id(position, len(chosen))
            phrases.append(Phrase(phrase_id, {"texto": reminder.content}))
            if reminder.status == OVERDUE and reminder.deadline is not None:
                phrases.append(Phrase(
                    "recordatorio.dictado_vencido", {"fecha": self._moment(reminder.deadline, ctx)}
                ))  # fmt: skip
        for phrase in phrases[:-1]:
            await ctx.say(phrase)
        finished = [r.id for r in chosen if r.status == OVERDUE or not r.pending]
        return ActionResult(
            "completado", phrases[-1], description=description,
            on_spoken=partial(self._start_autoconfirms, finished) if finished else None,
        )  # fmt: skip

    # --- Confirmar, posponer, eliminar ---------------------------------------------------------

    def _confirm(self, n: int | None, ctx: ActionContext) -> ActionResult:
        """Solo con el panel de recordatorios activo; si no, lo activa y no confirma nada,
        aunque se haya escrito un índice (RN-25)."""
        if ctx.active_panel != PANEL or n is None:
            ctx.publish(PanelActivated(PANEL))
            self._publish(ctx)
            return ActionResult("completado", Phrase("recordatorio.activar"))
        reminder = self._at(n, ctx)
        if reminder is None:
            return _no_item(n)
        self._remove(reminder.id, ctx)
        return ActionResult("completado", Phrase("recordatorio.confirmado", {"n": n}))

    def _snooze(
        self, n: int | None, duration: timedelta | None, ctx: ActionContext
    ) -> ActionResult:
        """El último aviso dado se repite dentro de `duration` (10 minutos si no se dice). La
        fecha límite no cambia (RN-27). Sin índice: el último notificado o leído."""
        reminders = ReminderRepository(ctx.db, ctx.profile)
        if n is None:
            reminder = None if self._last is None else reminders.get(self._last)
            if reminder is None or reminder.status == DELETED:
                return ActionResult("error", Phrase("recordatorio.sin_aviso"))
        else:
            reminder = self._at(n, ctx)
            if reminder is None:
                return _no_item(n)
        if reminder.status == OVERDUE:  # un vencido no vuelve a avisar (RN-31)
            return ActionResult("error", Phrase("recordatorio.limite_vencido"))
        trigger = reminder.last_fired
        if trigger is None:
            return ActionResult("error", Phrase("recordatorio.sin_aviso"))
        delta = duration or timedelta(minutes=ctx.config.settings.reminders.snooze_minutes)
        reminders.reschedule_trigger(trigger.id, ctx.clock.now() + delta)
        self._cancel_autoconfirm(reminder.id)
        self._last, self._highlighted = reminder.id, frozenset({reminder.id})
        self._scheduled(reminder.id, ctx)
        return ActionResult(
            "completado", Phrase("recordatorio.pospuesto", {"duracion": formats.duration(delta)})
        )

    def _move_deadline(self, n: int, deadline: datetime, ctx: ActionContext) -> ActionResult:
        """Solo antes de que venza la original; la nueva, no anterior a los avisos pendientes
        (RN-28)."""
        reminder = self._at(n, ctx)
        if reminder is None:
            return _no_item(n)
        if reminder.deadline is None:
            return ActionResult("error", Phrase("recordatorio.sin_limite"))
        if reminder.status != ACTIVE or reminder.deadline <= ctx.clock.now():
            return ActionResult("error", Phrase("recordatorio.limite_vencido"))
        if deadline <= ctx.clock.now():
            return ActionResult("error", Phrase("entidad.fecha_pasada"))
        if any(trigger.at > deadline for trigger in reminder.pending):
            return ActionResult("error", Phrase("recordatorio.limite_anterior"))
        ReminderRepository(ctx.db, ctx.profile).set_deadline(reminder.id, deadline)
        self._scheduled(reminder.id, ctx)
        return ActionResult(
            "completado",
            Phrase("recordatorio.limite_pospuesto", {"fecha": self._moment(deadline, ctx)}),
        )

    async def _delete(self, n: int, ctx: ActionContext) -> ActionResult:
        """Con confirmación (`BOOLEAN`); con un sí, borrado lógico (RN-13)."""
        reminder = self._at(n, ctx)
        if reminder is None:
            return _no_item(n)
        self._highlighted = frozenset({reminder.id})
        self._publish(ctx)
        answer = await ctx.ask(
            Phrase("recordatorio.confirmar_eliminar", {"n": n}), ExpectedType.BOOLEAN,
            metadata={"reminder_id": reminder.id}, subject={"n": n, "texto": reminder.content},
        )  # fmt: skip
        if answer.cancelled:
            return ActionResult.cancelled()  # ya se ha dicho
        if answer.value is not True:
            return ActionResult.cancelled(Phrase("general.operacion_cancelada"))
        self._remove(reminder.id, ctx)
        return ActionResult("completado", Phrase("recordatorio.eliminado", {"n": n}))

    def _remove(self, reminder_id: int, ctx: ActionContext | None = None) -> None:
        """Confirmado, eliminado o autoconfirmado: `eliminado`, sin trabajos pendientes."""
        target = ctx or self._ctx
        if target is None:
            return
        reminders = ReminderRepository(target.db, target.profile)
        reminder = reminders.get(reminder_id)
        if reminder is None:
            return
        reminders.set_status(reminder_id, DELETED)
        self._unschedule(reminder)
        self._highlighted = self._highlighted - {reminder_id}
        if self._last == reminder_id:
            self._last = None
        logger.info("Recordatorio %d eliminado", reminder_id)
        self._publish(target)

    # --- Avisos --------------------------------------------------------------------------------

    def _trigger_due(self, reminder_id: int, trigger_id: int) -> None:
        """Vence un aviso: se marca como dado y se agrupa con los que venzan a la vez."""
        ctx = self._ctx
        if ctx is None:
            return
        reminders = ReminderRepository(ctx.db, ctx.profile)
        reminder = reminders.get(reminder_id)
        if reminder is None or reminder.status != ACTIVE:
            return
        if not any(trigger.id == trigger_id for trigger in reminder.pending):
            return
        reminders.mark_fired(trigger_id)
        if reminder_id not in self._fired:
            self._fired.append(reminder_id)
        if not self._flush_pending:
            self._flush_pending = True
            asyncio.get_running_loop().call_soon(self._flush)

    def _flush(self) -> None:
        self._flush_pending = False
        fired, self._fired = self._fired, []
        if fired and self._ctx is not None:
            self._notify_fired(fired)

    def _notify_fired(self, reminder_ids: Sequence[int]) -> None:
        """Un solo aviso para todos: «Tiene N recordatorios.», sin fechas ni textos (RN-23).
        Al decirlo se activa el panel, con ellos destacados; al terminar, se ofrece
        dictarlos (`_offer`)."""
        ctx = self._ctx
        if ctx is None:
            return
        self._last, self._highlighted = reminder_ids[-1], frozenset(reminder_ids)
        total = len(reminder_ids)
        phrase = (
            Phrase("recordatorio.aviso_uno") if total == 1
            else Phrase("recordatorio.aviso_varios", {"n": total})
        )  # fmt: skip
        ctx.notify(Notice(phrase, panel=PANEL, reminder=True,
                          on_delivered=partial(self._offer, tuple(reminder_ids))))  # fmt: skip
        self._publish()

    def _offer(self, reminder_ids: tuple[int, ...]) -> None:
        """Dicho el aviso, la acción `dictar` entra en la cola como una orden: pregunta si se
        dictan y, con un sí, los dice."""
        if self._ctx is not None:
            self._ctx.publish(ActionRequested(self.name, "dictar", {"avisados": reminder_ids}))

    def _deadline_due(self, reminder_id: int) -> None:
        ctx = self._ctx
        if ctx is None:
            return
        reminder = ReminderRepository(ctx.db, ctx.profile).get(reminder_id)
        if reminder is not None and reminder.status == ACTIVE:
            self._notify_deadline(reminder_id)

    def _notify_deadline(self, reminder_id: int) -> None:
        """«El recordatorio N ha vencido…». Al decirlo pasa a `vencido` (RN-31) y empieza el
        plazo de autoconfirmación (RN-29)."""
        ctx = self._ctx
        if ctx is None:
            return
        listed = ReminderRepository(ctx.db, ctx.profile).listable()
        position = next((i for i, r in enumerate(listed, 1) if r.id == reminder_id), None)
        reminder = next((r for r in listed if r.id == reminder_id), None)
        if position is None or reminder is None or reminder.deadline is None:
            return
        phrase = Phrase(
            "recordatorio.vencido",
            {"n": position, "fecha": self._moment(reminder.deadline, ctx)},
        )
        ctx.notify(
            Notice(phrase, panel=PANEL, reminder=True,
                   on_delivered=partial(self._deadline_said, reminder_id))
        )  # fmt: skip

    def _deadline_said(self, reminder_id: int) -> None:
        ctx = self._ctx
        if ctx is None:
            return
        reminders = ReminderRepository(ctx.db, ctx.profile)
        reminder = reminders.get(reminder_id)
        if reminder is None or reminder.status != ACTIVE:
            return
        reminders.set_status(reminder_id, OVERDUE)
        logger.info("Recordatorio %d vencido", reminder_id)
        self._last, self._highlighted = reminder_id, frozenset({reminder_id})
        self._start_autoconfirm(reminder_id)
        self._publish()

    # --- Autoconfirmación (RN-29, RN-30, RN-32) ------------------------------------------------

    def _start_autoconfirm(self, reminder_id: int) -> None:
        ctx = self._ctx
        if ctx is None or ctx.scheduler is None:
            return  # sin sesión el plazo se pierde
        seconds = ctx.config.settings.reminders.autoconfirm_seconds
        ctx.scheduler.add(
            f"autoconfirm:{reminder_id}",
            ctx.clock.now() + timedelta(seconds=seconds),
            partial(self._autoconfirm, reminder_id),
        )

    def _start_autoconfirms(self, reminder_ids: Sequence[int]) -> None:
        for reminder_id in reminder_ids:
            self._start_autoconfirm(reminder_id)

    def _cancel_autoconfirm(self, reminder_id: int) -> None:
        if self._ctx is not None and self._ctx.scheduler is not None:
            self._ctx.scheduler.remove(f"autoconfirm:{reminder_id}")

    def _autoconfirm(self, reminder_id: int) -> None:
        """Se cumple el plazo sin confirmar ni posponer: se elimina en silencio."""
        ctx = self._ctx
        if ctx is None:
            return
        reminder = ReminderRepository(ctx.db, ctx.profile).get(reminder_id)
        if reminder is not None and reminder.status in (ACTIVE, OVERDUE):
            logger.info("Recordatorio %d autoconfirmado", reminder_id)
            self._remove(reminder_id)

    # --- Programación ----------------------------------------------------------------------------

    def _scheduled(self, reminder_id: int, ctx: ActionContext) -> None:
        """Tras un cambio: reprograma el recordatorio y publica la lista."""
        reminder = ReminderRepository(ctx.db, ctx.profile).get(reminder_id)
        if reminder is not None:
            self._schedule(reminder)
        self._publish(ctx)

    def _schedule(self, reminder: ReminderRow) -> None:
        """Sus avisos pendientes y su fecha límite futuros, si está activo y hay sesión."""
        ctx = self._ctx
        if ctx is None or ctx.scheduler is None or reminder.status != ACTIVE:
            return
        now = ctx.clock.now()
        for trigger in reminder.pending:
            if trigger.at > now:
                ctx.scheduler.add(
                    f"trigger:{trigger.id}", trigger.at,
                    partial(self._trigger_due, reminder.id, trigger.id),
                )  # fmt: skip
        if reminder.deadline is not None and reminder.deadline > now:
            ctx.scheduler.add(
                f"deadline:{reminder.id}", reminder.deadline,
                partial(self._deadline_due, reminder.id),
            )  # fmt: skip

    def _unschedule(self, reminder: ReminderRow) -> None:
        ctx = self._ctx
        if ctx is None or ctx.scheduler is None:
            return
        for trigger in reminder.triggers:
            ctx.scheduler.remove(f"trigger:{trigger.id}")
        ctx.scheduler.remove(f"deadline:{reminder.id}")
        ctx.scheduler.remove(f"autoconfirm:{reminder.id}")

    # --- Panel ---------------------------------------------------------------------------------

    def _publish(self, ctx: ActionContext | None = None) -> list[ReminderRow]:
        """Publica la lista numerada del panel (activos y vencidos, por identificador) y la
        devuelve."""
        target = ctx or self._ctx
        if target is None:
            return []
        listed = ReminderRepository(target.db, target.profile).listable()
        items = tuple(
            ReminderItem(
                index, reminder.id, reminder.content, reminder.status,  # type: ignore[arg-type]
                reminder.next_trigger, reminder.deadline, reminder.id in self._highlighted,
            )
            for index, reminder in enumerate(listed, 1)
        )  # fmt: skip
        target.publish(RemindersChanged(items))
        return listed

    def _at(self, n: int, ctx: ActionContext) -> ReminderRow | None:
        """El recordatorio que ocupa la posición `n` del panel (RN-50)."""
        listed = ReminderRepository(ctx.db, ctx.profile).listable()
        return listed[n - 1] if 1 <= n <= len(listed) else None

    def _moment(self, when: datetime, ctx: ActionContext) -> str:
        return formats.moment(when, ctx.clock.now(), self._tz)

    @staticmethod
    def _default_hour(ctx: ActionContext) -> int:
        return ctx.config.settings.router.default_hour


def _index(value: object) -> int:
    return int(value)  # type: ignore[call-overload]


def _dictation_id(position: int, total: int) -> str:
    """La frase de cada recordatorio al dictar: su muletilla depende del lugar que ocupa."""
    if total == 1:
        return "recordatorio.dictado_unico"
    if position == 0:
        return "recordatorio.dictado_primero"
    if position == total - 1:
        return "recordatorio.dictado_ultimo"
    return "recordatorio.dictado_siguiente"


def _no_item(n: int) -> ActionResult:
    return ActionResult("error", Phrase("general.indice_invalido", {"n": n}))


def _sequence(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, str | datetime):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]
