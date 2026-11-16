"""Módulo Recordatorio (recordatorio.md, criterios de aceptación; T-5.3 a T-5.6).

Con reloj falso, planificador sobre ese reloj y base de datos en memoria. Ahora es el jueves
1 de enero de 2026 a las 12:00; la hora local es UTC.
"""
import ast
import inspect
from datetime import UTC, timedelta

import pytest

from fakes.clock import DEFAULT_START
from fakes.context import CANCEL, ContextRig, settle
from jarvis_assistant.action_modules import reminder_manager
from jarvis_assistant.action_modules.reminder_manager import PANEL, ReminderManager, reminder_text
from jarvis_assistant.config import Config, RemindersSettings, Settings
from jarvis_assistant.core import repositories
from jarvis_assistant.core.action_api import OFFER, ExpectedType, Phrase, ReminderAction
from jarvis_assistant.core.events import ActionRequested, PanelActivated, RemindersChanged
from jarvis_assistant.core.repositories import ReminderRepository
from jarvis_assistant.core.scheduler import ClockScheduler

NOW = DEFAULT_START  # jueves 1 de enero de 2026, 12:00 UTC
TOMORROW_9 = NOW.replace(day=2, hour=9)


def later(**delta) -> object:
    return NOW + timedelta(**delta)


class World:
    def __init__(self, tmp_path, config: Config | None = None) -> None:
        self.rig = ContextRig(tmp_path, config=config)
        self.ctx = self.rig.ctx
        self.ctx.scheduler = ClockScheduler(self.rig.clock)
        self.module = ReminderManager(local_tz=UTC)
        self.repo = ReminderRepository(self.rig.database)

    async def open(self) -> None:
        await self.module.on_session_opened(self.ctx)

    async def close(self) -> None:
        await self.module.on_session_closed(self.ctx)

    async def run(self, action: str, **params):
        return await self.module.execute(action, params, self.ctx)

    async def advance(self, seconds: float) -> None:
        self.rig.clock.advance(seconds)
        await settle()

    def add(self, *triggers, deadline=None, text: str = "Llamar a Ana") -> int:
        """Un recordatorio creado antes de abrir la sesión."""
        return self.repo.create(text, list(triggers), deadline, NOW - timedelta(days=1))

    def status(self, reminder_id: int) -> str:
        return self.repo.get(reminder_id).status

    def jobs(self) -> set[str]:
        return set(self.ctx.scheduler.jobs())

    def panel(self) -> RemindersChanged:
        return self.rig.last(RemindersChanged)

    @property
    def notices(self):
        return self.rig.notices

    @property
    def answers(self) -> list:
        return self.rig.answers


@pytest.fixture
async def world(tmp_path):
    world = World(tmp_path)
    await world.open()
    yield world
    world.rig.close()


# --- Texto (RN-20) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("tengo que llamar a Ana", "Tienes que llamar a Ana"),
        ("Tengo que llamar a Ana", "Tienes que llamar a Ana"),
        ("debo ir al médico", "Debes ir al médico"),
        ("tenemos que salir", "Tenéis que salir"),
        ("llamar a Ana", "Llamar a Ana"),
        ("comprar pan.", "Comprar pan"),
        ("deberías estudiar", "Deberías estudiar"),  # sin conjugación: solo «debo»
        ("iPhone nuevo", "IPhone nuevo"),
        ("", ""),
    ],
)
def test_texto_del_recordatorio(text, expected):
    assert reminder_text(text) == expected


# --- Crear (CU-11) ---------------------------------------------------------------------------


async def test_cu11_flujo_principal(world):
    world.answers.append(False)
    result = await world.run("crear", texto="tengo que llamar a Ana mañana a las nueve")
    assert result.status == "completado"
    assert result.speech == Phrase("recordatorio.creado", {"fecha": "mañana a las 9"})
    assert [asked.expected_type for asked in world.rig.asked] == [ExpectedType.REMINDER_ACTION]
    assert world.rig.asked[0].question == Phrase("recordatorio.mas")
    (reminder,) = world.repo.listable()
    assert reminder.content == "Tienes que llamar a Ana"
    assert [t.at for t in reminder.triggers] == [TOMORROW_9]
    assert reminder.deadline is None
    assert world.jobs() == {f"trigger:{reminder.triggers[0].id}"}
    (item,) = world.panel().items
    assert (item.index, item.content, item.next_trigger) == (1, "Tienes que llamar a Ana",
                                                              TOMORROW_9)


async def test_cu11_a1_sin_fecha_se_pregunta(world):
    world.answers.extend([later(hours=2), False])
    result = await world.run("crear", texto="comprar pan")
    assert result.status == "completado"
    assert [a.question.id for a in world.rig.asked] == ["recordatorio.cuando", "recordatorio.mas"]
    assert world.rig.asked[0].expected_type is ExpectedType.DATETIME
    (reminder,) = world.repo.listable()
    assert (reminder.content, reminder.triggers[0].at) == ("Comprar pan", later(hours=2))


async def test_cu11_a1_si_se_cancela_la_fecha_no_se_crea_nada(world):
    world.answers.append(CANCEL)
    result = await world.run("crear", texto="comprar pan")
    assert (result.status, result.detail, result.speech) == ("error", "cancelada", None)
    assert world.repo.listable() == []


async def test_cu11_a2_otro_aviso_y_a3_fecha_limite(world):
    world.answers.extend([
        ReminderAction("aviso", later(days=2)),
        ReminderAction("limite", later(days=3)),
    ])  # fmt: skip
    await world.run("crear", texto="regar mañana a las 9")
    assert [a.question.id for a in world.rig.asked] == ["recordatorio.mas"] * 2
    (reminder,) = world.repo.listable()
    assert [t.at for t in reminder.triggers] == [TOMORROW_9, later(days=2)]
    assert reminder.deadline == later(days=3)
    assert len([job for job in world.jobs() if job.startswith("trigger:")]) == 2
    assert f"deadline:{reminder.id}" in world.jobs()


async def test_cu11_a2_como_mucho_los_avisos_configurados(tmp_path):
    config = Config(settings=Settings(reminders=RemindersSettings(max_triggers=2)))
    world = World(tmp_path, config)
    await world.open()
    world.answers.extend([
        ReminderAction("aviso", later(days=2)), ReminderAction("aviso", later(days=3)), False,
    ])  # fmt: skip
    await world.run("crear", texto="regar mañana a las 9")
    assert world.rig.said == [Phrase("recordatorio.max_avisos")]
    (reminder,) = world.repo.listable()
    assert len(reminder.triggers) == 2
    world.rig.close()


@pytest.mark.parametrize("answer", [False, CANCEL])
async def test_cu11_a4_una_negacion_o_cancelar_guardan_lo_que_hay(world, answer):
    world.answers.append(answer)
    result = await world.run("crear", texto="regar mañana a las 9")
    assert result.status == "completado"
    assert len(world.repo.listable()) == 1


async def test_cu11_a6_una_fecha_pasada_se_rechaza_y_se_repite_la_pregunta(world):
    world.answers.extend([later(hours=-1), later(hours=1), ReminderAction("aviso", later(hours=-2)),
                          False])  # fmt: skip
    await world.run("crear", texto="comprar pan")
    assert world.rig.said == [Phrase("entidad.fecha_pasada")] * 2
    assert [a.question.id for a in world.rig.asked] == [
        "recordatorio.cuando", "recordatorio.cuando", "recordatorio.mas", "recordatorio.mas",
    ]  # fmt: skip
    (reminder,) = world.repo.listable()
    assert [t.at for t in reminder.triggers] == [later(hours=1)]


async def test_cu11_a6_una_fecha_pasada_en_la_orden_se_pregunta_de_nuevo(world):
    world.answers.extend([later(hours=1), False])
    await world.run("crear", texto="llamar hoy a las 9")  # son las 12
    assert world.rig.said == [Phrase("entidad.fecha_pasada")]
    assert world.rig.asked[0].question.id == "recordatorio.cuando"
    assert world.repo.listable()[0].content == "Llamar"


async def test_cu11_a7_fecha_limite_anterior_a_un_aviso(world):
    world.answers.extend([ReminderAction("limite", later(hours=1)), False])
    await world.run("crear", texto="regar mañana a las 9")
    assert world.rig.said == [Phrase("recordatorio.limite_anterior")]
    assert world.repo.listable()[0].deadline is None


async def test_cu11_a8_texto_vacio(world):
    result = await world.run("crear", texto="mañana a las 9")
    assert (result.status, result.speech) == ("error", Phrase("recordatorio.vacio"))
    assert world.rig.asked == [] and world.repo.listable() == []


async def test_cu11_a9_desde_un_protocolo_sin_dialogo(tmp_path):
    world = World(tmp_path)
    world.ctx.origin = "protocolo"
    await world.open()
    result = await world.run(
        "crear", texto="debo revisar el correo", avisos=["mañana a las 9", later(days=2)],
        limite="el 10 de enero",
    )  # fmt: skip
    assert result.status == "completado"
    assert world.rig.asked == []
    (reminder,) = world.repo.listable()
    assert reminder.content == "Debes revisar el correo"
    assert reminder.deadline == NOW.replace(day=10, hour=9)
    bad = await world.run("crear", texto="x", avisos=["patata"])
    assert bad.speech == Phrase("entidad.fecha")
    world.rig.close()


# --- Avisos (CU-12) --------------------------------------------------------------------------


async def test_aviso_con_la_sesion_abierta(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(minutes=1))
    await world.open()
    assert world.notices == []
    await world.advance(60)
    (notice,) = world.notices
    assert notice.phrase == Phrase("recordatorio.aviso_uno")
    assert (notice.panel, notice.reminder) == (PANEL, True)
    assert world.repo.get(reminder_id).triggers[0].is_fired
    (item,) = world.panel().items
    assert item.highlighted
    world.rig.close()


async def test_avisos_simultaneos_se_agrupan(tmp_path):
    world = World(tmp_path)
    world.add(later(minutes=1))
    world.add(later(minutes=1))
    await world.open()
    await world.advance(60)
    (notice,) = world.notices
    assert notice.phrase == Phrase("recordatorio.aviso_varios", {"n": 2})
    assert [item.highlighted for item in world.panel().items] == [True, True]
    world.rig.close()


async def test_un_aviso_sin_sesion_se_da_al_abrir_la_siguiente(tmp_path):
    world = World(tmp_path)
    first = world.add(later(minutes=-30))
    second = world.add(later(minutes=-10), later(hours=1))
    await world.open()
    (notice,) = world.notices  # todos juntos (RN-22)
    assert notice.phrase == Phrase("recordatorio.aviso_varios", {"n": 2})
    assert world.repo.get(first).triggers[0].is_fired
    pending = world.repo.get(second).pending
    assert [t.at for t in pending] == [later(hours=1)]
    assert world.jobs() == {f"trigger:{pending[0].id}"}
    world.rig.close()


async def test_sin_sesion_no_se_dispara_nada(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(minutes=1))
    await world.open()
    await world.close()
    await world.advance(120)
    assert world.notices == [] and world.jobs() == set()
    assert not world.repo.get(reminder_id).triggers[0].is_fired


async def test_vencimiento_con_la_sesion_abierta(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(minutes=1), deadline=later(minutes=2))
    await world.open()
    await world.advance(60)
    await world.advance(60)
    aviso, vencido = world.notices
    assert aviso.phrase == Phrase("recordatorio.aviso_uno")
    assert vencido.phrase == Phrase(
        "recordatorio.vencido", {"n": 1, "fecha": "hoy a las 12 y 2"}
    )
    assert world.status(reminder_id) == "activo"  # pasa a vencido al decirlo (RN-31)
    vencido.on_delivered()
    assert world.status(reminder_id) == "vencido"
    assert world.panel().items[0].status == "vencido"
    assert f"autoconfirm:{reminder_id}" in world.jobs()
    await world.advance(300)  # RN-29
    assert world.status(reminder_id) == "eliminado"
    assert world.panel().items == ()
    world.rig.close()


async def test_vencimiento_sin_sesion_y_un_vencido_no_vuelve_a_avisar(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=-3), deadline=later(hours=-1))
    world.repo.mark_fired(world.repo.get(reminder_id).triggers[0].id)
    await world.open()
    (notice,) = world.notices
    assert notice.phrase.id == "recordatorio.vencido"
    notice.on_delivered()
    assert world.status(reminder_id) == "vencido"
    await world.close()
    world.rig.notices.clear()
    await world.open()
    assert world.notices == []  # RN-31
    result = await world.run("posponer", n=1)
    assert result.speech == Phrase("recordatorio.limite_vencido")
    world.rig.close()


# --- Dictar tras el aviso --------------------------------------------------------------------


async def test_dicho_el_aviso_se_pide_dictarlos(tmp_path):
    world = World(tmp_path)
    first = world.add(later(minutes=1))
    second = world.add(later(minutes=1))
    await world.open()
    await world.advance(60)
    (notice,) = world.notices
    notice.on_delivered()
    assert world.rig.last(ActionRequested) == ActionRequested(
        "recordatorio", "dictar", {"avisados": (first, second)}
    )
    world.rig.close()


async def test_con_un_si_los_dicta_seguidos_con_muletillas(tmp_path):
    world = World(tmp_path)
    ids = [world.add(later(hours=1), text=text) for text in ("Regar", "Pagar", "Llamar a Ana")]
    await world.open()
    world.answers.append(True)
    result = await world.run("dictar", avisados=tuple(ids))
    (asked,) = world.rig.asked
    assert asked.question == Phrase("recordatorio.ofrecer_varios")
    assert (asked.expected_type, asked.metadata) == (ExpectedType.BOOLEAN, {OFFER: True})
    assert world.rig.said == [
        Phrase("recordatorio.dictado_primero", {"texto": "Regar"}),
        Phrase("recordatorio.dictado_siguiente", {"texto": "Pagar"}),
    ]
    assert result.status == "completado"
    assert result.speech == Phrase("recordatorio.dictado_ultimo", {"texto": "Llamar a Ana"})
    assert result.on_spoken is None  # aún tienen avisos pendientes
    assert [world.status(i) for i in ids] == ["activo"] * 3  # dictar no confirma (RN-24)
    assert [item.highlighted for item in world.panel().items] == [True] * 3
    world.rig.close()


async def test_con_un_no_no_dicta_nada(world):
    reminder_id = world.add(later(hours=1))
    world.answers.append(False)
    result = await world.run("dictar", avisados=(reminder_id,))
    assert world.rig.asked[0].question == Phrase("recordatorio.ofrecer_uno")
    assert (result.status, result.speech) == ("completado", Phrase("recordatorio.no_dictar"))
    assert world.rig.said == []


async def test_cancelar_el_ofrecimiento(world):
    reminder_id = world.add(later(hours=1))
    world.answers.append(CANCEL)
    result = await world.run("dictar", avisados=(reminder_id,))
    assert (result.status, result.detail, result.speech) == ("error", "cancelada", None)
    assert world.rig.said == []


async def test_solo_se_dictan_los_avisados_que_siguen_en_el_panel(world):
    kept = world.add(later(hours=1), text="Regar")
    gone = world.add(later(hours=1), text="Pagar")
    world.add(later(hours=1), text="Otro")  # no avisado
    world.repo.set_status(gone, "eliminado")
    world.answers.append(True)
    result = await world.run("dictar", avisados=(kept, gone))
    assert world.rig.asked[0].question == Phrase("recordatorio.ofrecer_uno")
    assert result.speech == Phrase("recordatorio.dictado_unico", {"texto": "Regar"})
    assert world.rig.said == []


async def test_si_ya_no_queda_ninguno_no_pregunta(world):
    reminder_id = world.add(later(hours=1))
    world.repo.set_status(reminder_id, "eliminado")
    result = await world.run("dictar", avisados=(reminder_id,))
    assert (result.status, result.speech, world.rig.asked) == ("completado", None, [])


async def test_por_voz_dicta_todos_sin_preguntar_y_un_vencido_dice_su_fecha(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=-3), deadline=later(hours=-1), text="Pagar")
    world.repo.mark_fired(world.repo.get(reminder_id).triggers[0].id)
    world.repo.set_status(reminder_id, "vencido")
    await world.open()
    result = await world.run("dictar")
    assert world.rig.asked == []
    assert world.rig.said == [Phrase("recordatorio.dictado_unico", {"texto": "Pagar"})]
    assert result.speech == Phrase("recordatorio.dictado_vencido", {"fecha": "hoy a las 11"})
    result.on_spoken()  # sin avisos pendientes: empieza el plazo de RN-29
    assert f"autoconfirm:{reminder_id}" in world.jobs()
    world.rig.close()


async def test_por_voz_sin_recordatorios(world):
    result = await world.run("dictar")
    assert result.speech == Phrase("recordatorio.ninguno")


# --- Leer, confirmar (RN-24, RN-25) ----------------------------------------------------------


async def test_leer_no_confirma(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=1), text="Comprar pan")
    await world.open()
    result = await world.run("leer", n=1)
    assert result.speech == Phrase("recordatorio.lectura", {"texto": "Comprar pan"})
    assert result.on_spoken is None  # aún tiene avisos pendientes
    assert world.status(reminder_id) == "activo"
    assert world.panel().items[0].highlighted
    world.rig.close()


async def test_leer_un_vencido_dice_su_fecha_limite(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=-3), deadline=later(hours=-1), text="Pagar")
    world.repo.set_status(reminder_id, "vencido")
    await world.open()
    result = await world.run("leer", n=1)
    assert result.speech == Phrase(
        "recordatorio.lectura_vencido", {"texto": "Pagar", "fecha": "hoy a las 11"}
    )


async def test_confirmar_con_el_panel_inactivo_solo_lo_activa(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=1))
    await world.open()
    world.ctx.active_panel = "comandos"
    result = await world.run("confirmar", n=1)
    assert result.speech == Phrase("recordatorio.activar")
    assert world.rig.last(PanelActivated) == PanelActivated(PANEL)
    assert world.status(reminder_id) == "activo"
    world.ctx.active_panel = PANEL
    result = await world.run("confirmar", n=1)
    assert result.speech == Phrase("recordatorio.confirmado", {"n": 1})
    assert world.status(reminder_id) == "eliminado"
    assert world.jobs() == set()
    world.rig.close()


async def test_confirmar_sin_indice_con_el_panel_activo_pide_el_numero(world):
    world.ctx.active_panel = PANEL
    result = await world.run("confirmar")
    assert result.speech == Phrase("recordatorio.activar")


async def test_un_indice_que_no_existe(world):
    for action in ("leer", "confirmar", "posponer", "eliminar"):
        world.ctx.active_panel = PANEL
        result = await world.run(action, n=4)
        assert (result.status, result.speech) == (
            "error", Phrase("general.indice_invalido", {"n": 4})
        ), action


async def test_mostrar_dice_cuantos_hay(tmp_path):
    world = World(tmp_path)
    await world.open()
    assert (await world.run("mostrar")).speech == Phrase("recordatorio.ninguno")
    world.add(later(hours=1))
    world.add(later(hours=2))
    result = await world.run("mostrar")
    assert result.speech == Phrase("recordatorio.lista", {"recordatorios": "2 recordatorios"})
    assert [item.index for item in world.panel().items] == [1, 2]
    world.rig.close()


# --- Posponer (RN-27, RN-28) -----------------------------------------------------------------


async def notified(tmp_path, *triggers, deadline=None) -> tuple[World, int]:
    """Un recordatorio cuyo primer aviso acaba de darse."""
    world = World(tmp_path)
    reminder_id = world.add(later(minutes=1), *triggers, deadline=deadline)
    await world.open()
    await world.advance(60)
    return world, reminder_id


async def test_posponer_sin_indice_el_ultimo_notificado(tmp_path):
    world, reminder_id = await notified(tmp_path, deadline=later(hours=5))
    result = await world.run("posponer")
    assert result.speech == Phrase("recordatorio.pospuesto", {"duracion": "10 minutos"})
    (trigger,) = world.repo.get(reminder_id).triggers
    assert (trigger.at, trigger.is_fired) == (later(minutes=11), False)
    assert world.repo.get(reminder_id).deadline == later(hours=5)  # no cambia
    await world.advance(600)
    assert len(world.notices) == 2  # vuelve a avisar
    world.rig.close()


async def test_posponer_con_indice_y_duracion(tmp_path):
    world, reminder_id = await notified(tmp_path)
    result = await world.run("posponer", n=1, duracion=timedelta(minutes=30))
    assert result.speech == Phrase("recordatorio.pospuesto", {"duracion": "media hora"})
    assert world.repo.get(reminder_id).triggers[0].at == later(minutes=31)
    world.rig.close()


async def test_posponer_uno_que_aun_no_ha_avisado(tmp_path):
    world = World(tmp_path)
    world.add(later(hours=1))
    await world.open()
    assert (await world.run("posponer", n=1)).speech == Phrase("recordatorio.sin_aviso")
    assert (await world.run("posponer")).speech == Phrase("recordatorio.sin_aviso")
    world.rig.close()


async def test_posponer_la_fecha_limite_antes_y_despues_de_vencer(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=1), deadline=later(hours=2))
    world.add(later(hours=1))
    await world.open()
    early = await world.run("posponer_limite", n=1, fecha=later(minutes=30))
    assert early.speech == Phrase("recordatorio.limite_anterior")
    moved = await world.run("posponer_limite", n=1, fecha=later(days=1))
    assert moved.speech == Phrase("recordatorio.limite_pospuesto", {"fecha": "mañana a las 12"})
    assert world.repo.get(reminder_id).deadline == later(days=1)
    assert world.ctx.scheduler.jobs()[f"deadline:{reminder_id}"] == later(days=1)
    none = await world.run("posponer_limite", n=2, fecha=later(days=1))
    assert none.speech == Phrase("recordatorio.sin_limite")
    await world.advance(3600)  # los avisos
    await world.advance(23 * 3600)  # la fecha límite
    world.notices[-1].on_delivered()
    late = await world.run("posponer_limite", n=1, fecha=later(days=3))
    assert late.speech == Phrase("recordatorio.limite_vencido")
    world.rig.close()


# --- Autoconfirmación (RN-29, RN-30, RN-32) --------------------------------------------------


async def read_last(tmp_path) -> tuple[World, int]:
    """Un recordatorio leído en su última fecha de aviso: el plazo empieza al terminar."""
    world, reminder_id = await notified(tmp_path)
    result = await world.run("leer", n=1)
    assert result.on_spoken is not None
    result.on_spoken()
    return world, reminder_id


async def test_autoconfirmacion_a_los_300_segundos(tmp_path):
    world, reminder_id = await read_last(tmp_path)
    await world.advance(299)
    assert world.status(reminder_id) == "activo"
    await world.advance(1)
    assert world.status(reminder_id) == "eliminado"
    assert world.panel().items == ()
    world.rig.close()


async def test_autoconfirmacion_aunque_tenga_fecha_limite_futura(tmp_path):
    world, reminder_id = await notified(tmp_path, deadline=later(days=1))
    (await world.run("leer", n=1)).on_spoken()
    await world.advance(300)
    assert world.status(reminder_id) == "eliminado"
    world.rig.close()


async def test_avisos_completados_y_fecha_limite_futura_sigue_activo(tmp_path):
    """RN-32: sin leerlo, sigue visible y avisa al llegar la fecha límite."""
    world, reminder_id = await notified(tmp_path, deadline=later(hours=1))
    await world.advance(3600)
    assert world.status(reminder_id) == "activo"
    assert world.notices[-1].phrase.id == "recordatorio.vencido"
    world.rig.close()


async def test_posponer_cancela_la_autoconfirmacion(tmp_path):
    world, reminder_id = await read_last(tmp_path)
    await world.run("posponer")
    assert f"autoconfirm:{reminder_id}" not in world.jobs()
    await world.advance(300)
    assert world.status(reminder_id) == "activo"
    world.rig.close()


async def test_confirmar_cancela_la_autoconfirmacion(tmp_path):
    world, reminder_id = await read_last(tmp_path)
    world.ctx.active_panel = PANEL
    await world.run("confirmar", n=1)
    assert world.jobs() == set()
    assert world.status(reminder_id) == "eliminado"
    world.rig.close()


async def test_la_autoconfirmacion_se_pierde_al_cerrar_la_sesion(tmp_path):
    world, reminder_id = await read_last(tmp_path)
    await world.close()
    await world.advance(600)
    assert world.status(reminder_id) == "activo"  # sigue visible en la siguiente (A11)
    world.rig.close()


# --- Eliminar --------------------------------------------------------------------------------


async def test_eliminar_tras_confirmacion(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=1), text="Pagar")
    await world.open()
    world.answers.append(True)
    result = await world.run("eliminar", n=1)
    assert world.rig.asked[0].question == Phrase("recordatorio.confirmar_eliminar", {"n": 1})
    assert world.rig.asked[0].subject == {"n": 1, "texto": "Pagar"}
    assert result.speech == Phrase("recordatorio.eliminado", {"n": 1})
    assert world.status(reminder_id) == "eliminado"
    world.rig.close()


async def test_eliminar_con_un_no_no_hace_nada(tmp_path):
    world = World(tmp_path)
    reminder_id = world.add(later(hours=1))
    await world.open()
    world.answers.append(False)
    result = await world.run("eliminar", n=1)
    assert (result.status, result.speech) == ("error", Phrase("general.operacion_cancelada"))
    assert world.status(reminder_id) == "activo"
    world.rig.close()


# --- Prohibiciones ---------------------------------------------------------------------------


def test_ningun_delete_fisico():
    for module in (reminder_manager, repositories):
        source = inspect.getsource(module)
        strings = [
            node.value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]  # fmt: skip
        assert not any("DELETE" in text.upper().split() for text in strings), module.__name__
