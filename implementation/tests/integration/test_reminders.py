"""Recordatorios de principio a fin, con dobles (fase 5; CU-11 y CU-12).

El grafo es el de `build_app`, con el planificador sobre el reloj falso. Ahora es el jueves 1
de enero de 2026 a las 12:00 UTC; las fechas se dicen en la hora local del sistema.
"""
from datetime import timedelta

import pytest

from integration.test_orders import Rig, said
from jarvis_assistant.core import events
from jarvis_assistant.core.repositories import ReminderRepository
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.speaker import formats, phrases, speaker
from jarvis_assistant.speaker.phrases import PHRASES

S = AssistantState
EXTRA = (events.DialogueOpened, events.DialogueClosed, events.RemindersChanged)


async def started(tmp_path, monkeypatch) -> Rig:
    rig = Rig(tmp_path, monkeypatch)
    for event_type in EXTRA:
        rig.app.bus.subscribe(event_type, rig.events.append)
    await rig.start()
    return rig


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    rig = await started(tmp_path, monkeypatch)
    await rig.open_session()
    yield rig
    await rig.stop()


def reminders(rig) -> ReminderRepository:
    return ReminderRepository(rig.database)


def statuses(rig) -> list[str]:
    rows = rig.database.conn.execute("SELECT status FROM reminders ORDER BY id")
    return [row["status"] for row in rows]


def moment(rig, when) -> str:
    return formats.moment(when, rig.clock.now())


async def create_in_a_minute(rig, text: str = "recuérdame regar las plantas en un minuto") -> None:
    await rig.order(text)
    assert rig.state is S.AWAITING_PARAMETER
    await rig.order("no")
    rig.events.clear()


# --- CU-11. Crear un recordatorio ------------------------------------------------------------


async def test_cu11_flujo_principal(rig):
    await rig.order("Recuérdame que tengo que llamar a Ana mañana a las nueve")
    assert rig.state is S.AWAITING_PARAMETER
    (opened,) = rig.of(events.DialogueOpened)
    assert opened.expected_type == "REMINDER_ACTION"
    assert opened.hints == ("Otro aviso", "Fecha límite", "No")
    assert opened.subject == {"texto": "Tienes que llamar a Ana"}
    assert rig.spoken() == [said("recordatorio.mas")]
    rig.events.clear()
    await rig.order("No")
    (reminder,) = reminders(rig).listable()
    assert reminder.content == "Tienes que llamar a Ana"
    assert rig.spoken() == [said("recordatorio.creado", fecha=moment(rig, reminder.triggers[0].at))]
    assert rig.spoken()[0] == said("recordatorio.creado", fecha="mañana a las 9")
    assert rig.tasks()[-1][2] == "completado"
    assert rig.of(events.RemindersChanged)[-1].items[0].content == "Tienes que llamar a Ana"
    assert rig.state is S.LISTENING_COMMAND


async def test_cu11_a1_y_a5_sin_fecha_y_fecha_no_entendida(rig):
    await rig.order("recuérdame comprar pan")
    assert rig.spoken() == [said("recordatorio.cuando")]
    rig.events.clear()
    await rig.write("patata")
    await rig.advance(2.0)
    assert rig.spoken() == [said("entidad.fecha"), said("recordatorio.cuando")]
    rig.events.clear()
    answered = rig.clock.now()
    await rig.order("en dos horas")
    assert rig.spoken() == [said("recordatorio.mas")]
    await rig.order("fecha límite pasado mañana")
    (reminder,) = reminders(rig).listable()
    assert reminder.triggers[0].at - answered == timedelta(hours=2)
    assert reminder.deadline is not None


async def test_cu11_a4_cancelar_guarda_sin_decir_cancelado(rig):
    await rig.order("recuérdame regar mañana")
    rig.events.clear()
    await rig.order("cancelar")
    assert rig.of(events.DialogueClosed) == [events.DialogueClosed("cancelled")]
    assert said("general.operacion_cancelada") not in rig.spoken()
    assert rig.spoken() == [said("recordatorio.creado", fecha="mañana a las 9")]
    assert statuses(rig) == ["activo"]


async def test_cu11_a4_tiempo_agotado_tambien_guarda(rig):
    await rig.order("recuérdame regar mañana")
    await rig.advance(21.0)
    assert statuses(rig) == ["activo"]
    assert rig.state is S.LISTENING_COMMAND


async def test_cu11_a8_texto_vacio(rig):
    await rig.order("recuérdame mañana a las nueve")
    assert rig.spoken() == [said("recordatorio.vacio")]
    assert rig.tasks()[-1][2] == "error"
    assert statuses(rig) == []


# --- CU-12. Atender un recordatorio ----------------------------------------------------------


async def test_cu12_flujo_principal(rig):
    await create_in_a_minute(rig)
    await rig.advance(60.0)
    assert said("recordatorio.aviso_uno") in rig.spoken()
    assert events.PanelActivated("recordatorios") in rig.of(events.PanelActivated)
    assert rig.of(events.RemindersChanged)[-1].items[0].highlighted
    assert said("recordatorio.ofrecer_uno") in rig.spoken()  # ¿Se lo leo?
    assert rig.state is S.AWAITING_CONFIRMATION
    rig.events.clear()
    await rig.order("no")
    assert rig.spoken() == [said("recordatorio.no_dictar")]
    rig.events.clear()
    await rig.order("lee el recordatorio uno")
    assert rig.spoken() == [said("recordatorio.lectura", texto="Regar las plantas")]
    assert statuses(rig) == ["activo"]  # leer no confirma (RN-24)
    rig.events.clear()
    await rig.order("Confirmar recordatorios uno")
    assert rig.spoken() == [said("recordatorio.confirmado", n=1)]
    assert statuses(rig) == ["eliminado"]
    assert rig.of(events.RemindersChanged)[-1].items == ()


async def test_cu12_a1_posponer(rig):
    await create_in_a_minute(rig)
    await rig.advance(60.0)
    await rig.order("no")
    rig.events.clear()
    await rig.order("posponer media hora")
    assert rig.spoken() == [said("recordatorio.pospuesto", duracion="media hora")]
    await rig.advance(30 * 60.0)
    assert said("recordatorio.aviso_uno") in rig.spoken()


async def test_cu12_a3_autoconfirmacion_tras_leer_el_ultimo_aviso(rig):
    await create_in_a_minute(rig)
    await rig.advance(60.0)
    await rig.order("no")
    await rig.order("lee el recordatorio uno")
    await rig.advance(298.0)
    assert statuses(rig) == ["activo"]
    await rig.advance(2.0)
    assert statuses(rig) == ["eliminado"]


async def test_cu12_a2_callar_la_lectura_y_posponer(rig):
    await create_in_a_minute(rig)
    await rig.advance(60.0)
    await rig.order("no")
    await rig.write("lee el recordatorio uno")
    await rig.advance(0.25)  # la lectura está sonando
    await rig.write("Hey Jarvis")
    rig.events.clear()
    await rig.order("posponer")
    assert rig.spoken() == [said("recordatorio.pospuesto", duracion="10 minutos")]
    await rig.advance(400.0)
    assert statuses(rig) == ["activo"]  # posponer cancela el plazo


async def test_cu12_a4_confirmar_con_el_panel_inactivo(rig):
    await create_in_a_minute(rig)
    await rig.order("dónde estoy")  # otro panel pasa a ser el activo
    rig.events.clear()
    await rig.order("confirmar recordatorios uno")
    assert rig.spoken() == [said("recordatorio.activar")]
    assert rig.of(events.PanelActivated) == [events.PanelActivated("recordatorios")]
    assert statuses(rig) == ["activo"]
    await rig.order("confirmar recordatorios uno")
    assert statuses(rig) == ["eliminado"]


async def test_cu12_a5_avisos_sin_sesion_tras_la_frase_de_apertura(tmp_path, monkeypatch):
    rig = await started(tmp_path, monkeypatch)
    now = rig.clock.now()
    for text in ("Regar", "Pagar"):
        reminders(rig).create(text, [now - timedelta(hours=1)], None, now - timedelta(days=1))
    await rig.write("Hey Jarvis")
    await rig.until(lambda: rig.app.orchestrator.modules["apertura"]._discovery.done())
    await rig.advance(3.0)
    spoken = rig.spoken()
    assert spoken[0] == said("ciclo.apertura")
    assert spoken[1:] == [said("recordatorio.aviso_varios", n=2),
                          said("recordatorio.ofrecer_varios")]
    await rig.stop()


async def test_cu12_a6_vence_la_fecha_limite(rig):
    await rig.order("recuérdame pagar en un minuto")
    await rig.order("fecha límite en dos minutos")
    await rig.advance(120.0)
    (reminder,) = reminders(rig).listable()
    assert said("recordatorio.vencido", n=1, fecha=moment(rig, reminder.deadline)) in (
        rig.spoken()
    )
    assert reminder.status == "vencido"
    await rig.advance(300.0)
    assert statuses(rig) == ["eliminado"]


async def test_cu12_a8_el_aviso_espera_al_dialogo(rig):
    await create_in_a_minute(rig)
    await rig.advance(45.0)
    await rig.write("recuérdame comprar pan")
    await rig.advance(1.0)
    assert rig.state is S.AWAITING_PARAMETER
    rig.events.clear()
    await rig.advance(15.0)  # vence el aviso con la pregunta abierta
    assert said("recordatorio.aviso_uno") not in rig.spoken()
    await rig.order("cancelar")
    await rig.advance(2.0)
    assert said("recordatorio.aviso_uno") in rig.spoken()


async def opened_with_due(tmp_path, monkeypatch, *texts: str) -> Rig:
    """Recordatorios cuyo aviso venció sin sesión: se avisan tras la frase de apertura."""
    rig = await started(tmp_path, monkeypatch)
    now = rig.clock.now()
    for text in texts:
        reminders(rig).create(text, [now - timedelta(hours=1)], None, now - timedelta(days=1))
    await rig.write("Hey Jarvis")
    await rig.until(lambda: rig.app.orchestrator.modules["apertura"]._discovery.done())
    await rig.advance(3.0)
    return rig


async def test_tras_el_aviso_con_un_si_los_dicta_variando_las_muletillas(tmp_path, monkeypatch):
    monkeypatch.setattr(speaker, "advance", phrases.advance)  # aquí sí rotan las variantes
    rig = await opened_with_due(tmp_path, monkeypatch, "Regar", "Pagar", "Llamar a Ana", "Ir")
    assert rig.spoken()[-1] == PHRASES["recordatorio.ofrecer_varios"][0]
    assert rig.state is S.AWAITING_CONFIRMATION
    rig.events.clear()
    await rig.order("sí")
    await rig.advance(2.0)
    assert rig.spoken() == [
        PHRASES["recordatorio.dictado_primero"][0].format(texto="Regar"),
        PHRASES["recordatorio.dictado_siguiente"][0].format(texto="Pagar"),
        PHRASES["recordatorio.dictado_siguiente"][1].format(texto="Llamar a Ana"),
        PHRASES["recordatorio.dictado_ultimo"][0].format(texto="Ir"),
    ]
    assert statuses(rig) == ["activo"] * 4
    await rig.advance(305.0)  # sin avisos pendientes: RN-29 al terminar de dictarlos
    assert statuses(rig) == ["eliminado"] * 4
    await rig.stop()


async def test_si_no_contesta_al_ofrecimiento_no_dice_operacion_cancelada(rig):
    await create_in_a_minute(rig)
    await rig.advance(60.0)
    assert rig.state is S.AWAITING_CONFIRMATION
    await rig.advance(21.0)
    assert rig.state is not S.AWAITING_CONFIRMATION
    assert not set(PHRASES["general.operacion_cancelada"]) & set(rig.spoken())
    assert statuses(rig) == ["activo"]


async def test_leeme_los_recordatorios_los_dicta_sin_preguntar(rig):
    await create_in_a_minute(rig)
    await rig.order("léeme los recordatorios")
    assert rig.of(events.DialogueOpened) == []
    assert rig.spoken() == [
        PHRASES["recordatorio.dictado_unico"][0].format(texto="Regar las plantas")
    ]


async def test_rn39_en_reposo_un_aviso_pone_en_escucha(rig):
    await create_in_a_minute(rig)
    await rig.write("gracias jarvis")
    await rig.advance(5.0)
    assert rig.state is S.IDLE
    await rig.advance(60.0)
    assert rig.state is S.AWAITING_CONFIRMATION  # en escucha, y ya le pregunta
    assert said("recordatorio.aviso_uno") in rig.spoken()


async def test_al_cerrar_la_sesion_no_queda_nada_programado(rig):
    await create_in_a_minute(rig)
    await rig.write("buenas noches jarvis")
    await rig.advance(3.0)
    assert rig.state is S.DORMIDO
    assert rig.app.orchestrator._scheduler.jobs() == {}
    await rig.advance(120.0)
    assert reminders(rig).listable()[0].pending  # sin sesión no se dispara (RN-22)
