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
    rig.sessions.soft_delete(ids[12])
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
        rig.sessions.soft_delete(session_id)
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


async def test_eliminar_un_id_inexistente_es_un_error(rig, two):
    result = await History().execute("eliminar", {"id": 99}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("historial.no_existe", {"id": 99}))
    assert rig.asked == []


async def test_eliminar_una_sesion_ya_eliminada_es_como_si_no_existiera(rig, two):
    old, _current = two
    rig.sessions.soft_delete(old)
    result = await History().execute("eliminar", {"id": old}, rig.ctx)
    assert result.speech == Phrase("historial.no_existe", {"id": old})


async def test_la_sesion_actual_no_se_puede_eliminar(rig, two):
    _old, current = two
    result = await History().execute("eliminar", {"id": current}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("historial.es_actual"))
    assert not rig.sessions.get(current).is_deleted
    assert rig.asked == []


async def test_con_un_si_se_elimina_de_forma_logica(rig, two):
    old, current = two
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
    shown = rig.last(events.HistoryShown)
    assert [s.id for s in shown.sessions] == [old] and shown.current_id == current
    assert (result.status, result.speech) == (
        "completado", Phrase("historial.eliminada", {"id": old}),
    )  # fmt: skip
    row = rig.sessions.get(old)
    assert row is not None and row.is_deleted  # RNF-12: la fila sigue
    assert old not in [s.id for s in rig.sessions.visible_history()]


async def test_con_un_no_no_se_elimina(rig, two):
    old, _current = two
    rig.answers = [False]
    result = await History().execute("eliminar", {"id": old}, rig.ctx)
    assert (result.status, result.speech, result.detail) == (
        "error", Phrase("general.operacion_cancelada"), "cancelada",
    )  # fmt: skip
    assert not rig.sessions.get(old).is_deleted


async def test_cancelada_o_vencida_no_se_elimina_y_no_repite_el_aviso(rig, two):
    old, _current = two
    rig.answers = [CANCEL]
    result = await History().execute("eliminar", {"id": old}, rig.ctx)
    # «Operación cancelada.» ya lo dice el orquestador al cancelar el diálogo.
    assert (result.status, result.speech, result.detail) == ("error", None, "cancelada")
    assert not rig.sessions.get(old).is_deleted
