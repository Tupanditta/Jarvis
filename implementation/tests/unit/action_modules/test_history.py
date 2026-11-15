"""Módulo Historial: `mostrar` y `actividades` (historial.md)."""
from datetime import timedelta

import pytest

from fakes.context import ContextRig
from jarvis_assistant.action_modules.session_manager import History
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import Phrase
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


def test_las_dos_acciones_valen_en_protocolos_y_activan_el_panel_de_historial():
    specs = History().intents()
    assert {spec.action for spec in specs} == {"mostrar", "actividades"}
    assert all(spec.in_protocols and spec.panel == "historial" for spec in specs)
