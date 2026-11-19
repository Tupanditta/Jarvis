"""Módulo Historial: `mostrar`, `actividades` y `eliminar` (historial.md)."""
from datetime import timedelta

import pytest

from fakes.context import CANCEL, ContextRig
from jarvis_assistant.action_modules.session_manager import History
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import ExpectedType, Phrase
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path)
    rig.sessions = SessionRepository(rig.database)
    rig.activities = ActivityRepository(rig.database)
    yield rig
    rig.close()


def create(rig, count: int) -> list[int]:
    """Crea `count` sesiones, cada una un minuto más reciente que la anterior."""
    start = rig.clock.now()
    return [
        rig.sessions.create(f"sesión {index}", start + timedelta(minutes=index))
        for index in range(1, count + 1)
    ]


async def test_mostrar_orden_y_limite_con_mas_de_diez_sesiones(rig):
    ids = create(rig, 13)
    for important in (ids[1], ids[4]):
        rig.sessions.set_importance(important, True, by_user=True)
    rig.sessions.delete([ids[12]])
    rig.ctx.session = rig.sessions.get(ids[11])
    result = await History().execute("mostrar", {}, rig.ctx)
    shown = rig.last(events.HistoryShown)
    # Primero las importantes; dentro de cada grupo, de la más reciente a la más antigua.
    assert [session.id for session in shown.sessions] == [
        ids[4], ids[1], ids[11], ids[10], ids[9], ids[8], ids[7], ids[6], ids[5], ids[3],
    ]  # fmt: skip
    assert shown.current_id == ids[11]
    assert result.speech == Phrase("historial.mostrado", {"sesiones": "10 sesiones"})


async def test_mostrar_una_sola_sesion_lo_dice_en_singular(rig):
    create(rig, 1)
    result = await History().execute("mostrar", {}, rig.ctx)
    assert result.speech.params == {"sesiones": "1 sesión"}


async def test_actividades_de_la_sesion_indicada(rig):
    first, second = create(rig, 2)
    now = rig.clock.now()
    rig.activities.add(first, "comandos", "ls", now)
    task = rig.activities.add(first, "apertura", "abrir GitHub", now)
    rig.activities.finish(task, "completado")
    rig.activities.add(second, "busqueda", "buscar notas", now)
    result = await History().execute("actividades", {"id": first}, rig.ctx)
    shown = rig.last(events.SessionActivitiesShown)
    assert shown.session.id == first
    assert [(a.module, a.description, a.status) for a in shown.activities] == [
        ("comandos", "ls", "pendiente"), ("apertura", "abrir GitHub", "completado"),
    ]  # fmt: skip
    assert result.speech == Phrase(
        "historial.actividades", {"nombre": "sesión 1", "actividades": "2 actividades"}
    )


async def test_actividades_sin_identificador_usa_la_sesion_actual(rig):
    _first, second = create(rig, 2)
    rig.activities.add(second, "busqueda", "buscar notas", rig.clock.now())
    rig.ctx.session = rig.sessions.get(second)
    result = await History().execute("actividades", {}, rig.ctx)
    assert rig.last(events.SessionActivitiesShown).session.id == second
    assert result.speech.params == {"nombre": "sesión 2", "actividades": "1 actividad"}


@pytest.mark.parametrize("deleted", [False, True])
async def test_actividades_de_una_sesion_inexistente_o_eliminada(rig, deleted):
    (session_id,) = create(rig, 1)
    if deleted:
        rig.sessions.delete([session_id])
    else:
        session_id = 99
    result = await History().execute("actividades", {"id": session_id}, rig.ctx)
    assert (result.status, result.speech) == (
        "error", Phrase("historial.no_existe", {"id": session_id}),
    )  # fmt: skip
    assert rig.events == []


def test_las_consultas_valen_en_protocolos_y_eliminar_no():
    specs = History().intents()
    assert {spec.action for spec in specs} == {"mostrar", "actividades", "eliminar"}
    assert all(spec.panel == "historial" for spec in specs)
    assert {spec.action for spec in specs if spec.in_protocols} == {"mostrar", "actividades"}




# --- eliminar --------------------------------------------------------------------------------


@pytest.fixture
def two(rig):
    """Una sesión antigua y la actual."""
    old, current = create(rig, 2)
    rig.ctx.session = rig.sessions.get(current)
    return old, current


def names(rig) -> list[tuple[int, str]]:
    return sorted((s.id, s.name) for s in rig.sessions.visible_history(None))


async def test_eliminar_un_id_inexistente_es_un_error(rig, two):
    result = await History().execute("eliminar", {"id": 99}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("historial.no_existe", {"id": 99}))
    assert rig.asked == []


async def test_la_sesion_actual_no_se_puede_eliminar(rig, two):
    _old, current = two
    result = await History().execute("eliminar", {"id": current}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("historial.es_actual"))
    assert rig.sessions.get(current) is not None
    assert rig.asked == []


async def test_con_un_si_se_borra_del_todo_y_se_renumera(rig, two):
    old, current = two
    rig.activities.add(old, "comandos", "ls", rig.clock.now())
    rig.answers = [True]
    result = await History().execute("eliminar", {"id": old}, rig.ctx)
    (asked,) = rig.asked
    assert asked.question == Phrase(
        "historial.confirmar_eliminar", {"id": old, "nombre": "sesión 1"}
    )
    assert asked.expected_type is ExpectedType.BOOLEAN
    assert asked.metadata == {"session_id": old}
    assert asked.subject == {"id": old, "nombre": "sesión 1"}
    # Antes de preguntar se muestra solo esa sesión.
    shown = rig.of(events.HistoryShown)[0]
    assert [s.id for s in shown.sessions] == [old] and shown.current_id == current
    assert (result.status, result.speech, result.description) == (
        "completado", Phrase("historial.eliminada", {"id": old}), "eliminar la sesión 1",
    )  # fmt: skip
    # Ni la fila ni sus actividades: la actual pasa a ser la 1.
    assert names(rig) == [(1, "sesión 2")]
    assert rig.activities.of_session(1) == []
    assert rig.last(events.SessionsDeleted) == events.SessionsDeleted((old,), {current: 1})
    # Al terminar se muestra el historial ya renumerado.
    after = rig.last(events.HistoryShown)
    assert [s.id for s in after.sessions] == [1] and after.current_id == 1
    assert rig.said == []  # no es importante: no hay aviso


async def test_con_un_no_no_se_elimina(rig, two):
    old, _current = two
    rig.answers = [False]
    result = await History().execute("eliminar", {"id": old}, rig.ctx)
    assert (result.status, result.speech, result.detail) == (
        "error", Phrase("general.operacion_cancelada"), "cancelada",
    )  # fmt: skip
    assert names(rig) == [(1, "sesión 1"), (2, "sesión 2")]
    assert rig.of(events.SessionsDeleted) == []


async def test_cancelada_o_vencida_no_se_elimina_y_no_repite_el_aviso(rig, two):
    old, _current = two
    rig.answers = [CANCEL]
    result = await History().execute("eliminar", {"id": old}, rig.ctx)
    # «Operación cancelada.» ya lo dice el orquestador al cancelar el diálogo.
    assert (result.status, result.speech, result.detail) == ("error", None, "cancelada")
    assert names(rig) == [(1, "sesión 1"), (2, "sesión 2")]


async def test_una_sesion_importante_se_avisa_antes_de_confirmar(rig, two):
    old, _current = two
    rig.sessions.set_importance(old, True, by_user=True)
    rig.answers = [True]
    await History().execute("eliminar", {"id": old}, rig.ctx)
    assert rig.said == [Phrase("historial.aviso_importantes", {"sesiones": "la sesión 1"})]
    assert names(rig) == [(1, "sesión 2")]


# --- eliminar varias: se muestran todas y se pregunta cuáles ---------------------------------


@pytest.fixture
def six(rig):
    """Cinco sesiones antiguas y la actual, la 6."""
    ids = create(rig, 6)
    rig.ctx.session = rig.sessions.get(ids[-1])
    return ids


async def test_sin_id_muestra_todas_y_pregunta_cuales(rig):
    ids = create(rig, 13)
    rig.ctx.session = rig.sessions.get(ids[-1])
    rig.answers = [CANCEL]
    await History().execute("eliminar", {}, rig.ctx)
    (asked,) = rig.asked
    assert (asked.question, asked.expected_type) == (
        Phrase("historial.cuales_eliminar"), ExpectedType.SESSION_IDS,
    )  # fmt: skip
    shown = rig.last(events.HistoryShown)
    assert len(shown.sessions) == 13  # todas, no solo las 10 del historial
    assert shown.current_id == ids[-1]


async def test_se_eliminan_todas_las_elegidas_a_la_vez(rig, six):
    rig.answers = [(1, 3, 4), True]
    result = await History().execute("eliminar", {}, rig.ctx)
    confirm = rig.asked[1]
    assert confirm.question == Phrase(
        "historial.confirmar_eliminar_varias", {"sesiones": "1, 3 y 4"}
    )
    assert confirm.expected_type is ExpectedType.BOOLEAN
    assert confirm.metadata == {"session_ids": (1, 3, 4)}
    # Antes de confirmar se muestran solo las elegidas.
    assert [s.id for s in rig.of(events.HistoryShown)[1].sessions] == [1, 3, 4]
    assert (result.status, result.speech, result.description) == (
        "completado", Phrase("historial.eliminadas", {"sesiones": "1, 3 y 4"}),
        "eliminar las sesiones 1, 3 y 4",
    )  # fmt: skip
    assert names(rig) == [(1, "sesión 2"), (2, "sesión 5"), (3, "sesión 6")]
    assert rig.last(events.SessionsDeleted) == events.SessionsDeleted(
        (1, 3, 4), {2: 1, 5: 2, 6: 3}
    )
    assert rig.last(events.HistoryShown).current_id == 3


async def test_las_importantes_elegidas_se_avisan(rig, six):
    for important in (2, 4):
        rig.sessions.set_importance(important, True, by_user=True)
    rig.answers = [(1, 2, 3, 4), False]
    await History().execute("eliminar", {}, rig.ctx)
    assert rig.said == [
        Phrase("historial.aviso_importantes", {"sesiones": "las sesiones 2 y 4"})
    ]
    assert len(names(rig)) == 6  # con un «no» no se borra nada


async def test_sin_respuesta_a_la_confirmacion_no_se_elimina_nada(rig, six):
    rig.answers = [(1, 2), CANCEL]
    result = await History().execute("eliminar", {}, rig.ctx)
    assert (result.status, result.speech, result.detail) == ("error", None, "cancelada")
    assert len(names(rig)) == 6
    assert rig.of(events.SessionsDeleted) == []


async def test_sin_respuesta_a_cuales_no_se_elimina_nada(rig, six):
    rig.answers = [CANCEL]
    result = await History().execute("eliminar", {}, rig.ctx)
    assert (result.status, result.detail) == ("error", "cancelada")
    assert len(rig.asked) == 1 and len(names(rig)) == 6


@pytest.mark.parametrize(
    ("chosen", "speech"),
    [((2, 9), Phrase("historial.no_existe", {"id": 9})), ((1, 6), Phrase("historial.es_actual"))],
)
async def test_una_eleccion_no_valida_no_elimina_ninguna(rig, six, chosen, speech):
    rig.answers = [chosen]
    result = await History().execute("eliminar", {}, rig.ctx)
    assert (result.status, result.speech) == ("error", speech)
    assert len(rig.asked) == 1 and len(names(rig)) == 6


async def test_si_solo_esta_la_actual_no_hay_nada_que_eliminar(rig):
    (only,) = create(rig, 1)
    rig.ctx.session = rig.sessions.get(only)
    result = await History().execute("eliminar", {}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("historial.nada_que_eliminar"))
    assert rig.asked == []
