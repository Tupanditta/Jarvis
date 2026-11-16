"""Acciones del módulo Sesión: nombre, importancia, desbordamiento, restauración y las acciones
de protocolo (sesion.md, RN-03 a RN-09; CU-10)."""
from datetime import UTC, timedelta

import pytest

from fakes.context import CANCEL, ContextRig
from jarvis_assistant.action_modules.session_manager import SessionManager
from jarvis_assistant.core.action_api import ExpectedType, Phrase
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import SessionChanged, SessionOverflowed
from jarvis_assistant.core.repositories import SessionRepository


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path)
    rig.sessions = SessionRepository(rig.database)
    rig.manager = SessionManager(rig.database, rig.clock, EventBus(), local_tz=UTC)
    yield rig
    rig.close()


def open_current(rig):
    session = rig.manager.open_session()
    rig.ctx.session = session
    return session


def row(rig, session_id: int):
    return rig.sessions.get(session_id)


async def run(rig, action: str, **params):
    return await rig.manager.execute(action, params, rig.ctx)


def important_sessions(rig, count: int) -> list[int]:
    """`count` sesiones importantes y cerradas, cada una un minuto más reciente."""
    start = rig.clock.now() - timedelta(days=1)
    ids = []
    for index in range(count):
        session_id = rig.sessions.create(f"vieja {index}", start + timedelta(minutes=index))
        rig.sessions.set_importance(session_id, True, by_user=True)
        rig.sessions.close(session_id, start + timedelta(minutes=index, seconds=30), "voz")
        ids.append(session_id)
    return ids


# --- Nombre ----------------------------------------------------------------------------------


async def test_nombrar_fija_el_nombre_por_el_usuario(rig):
    session = open_current(rig)
    result = await run(rig, "nombrar", nombre="práctica de redes")
    assert (result.status, result.speech) == (
        "completado", Phrase("sesion.nombrada", {"nombre": "práctica de redes"}),
    )  # fmt: skip
    current = row(rig, session.id)
    assert current.name == "práctica de redes" and current.name_set_by_module
    assert rig.last(SessionChanged) == SessionChanged(session.id, "práctica de redes", False)
    assert rig.manager.current.name == "práctica de redes"


async def test_un_nombre_vacio_no_es_valido(rig):
    session = open_current(rig)
    result = await run(rig, "nombrar", nombre="   ")
    assert (result.status, result.speech) == ("error", Phrase("entidad.nombre"))
    assert not row(rig, session.id).name_set_by_module


async def test_se_permiten_nombres_repetidos_fijados_por_el_usuario(rig):
    other = rig.sessions.create("redes", rig.clock.now() - timedelta(days=1))
    session = open_current(rig)
    await run(rig, "nombrar", nombre="redes")
    assert row(rig, session.id).name == row(rig, other).name == "redes"


async def test_rn03_un_protocolo_no_cambia_un_nombre_fijado_por_el_usuario(rig):
    session = open_current(rig)
    await run(rig, "nombrar", nombre="mía")
    result = await run(rig, "proponer_nombre", nombre="modo trabajo")
    assert result.status == "completado" and result.speech is None
    assert rig.asked == []  # ni siquiera se pregunta
    assert row(rig, session.id).name == "mía"


async def test_rn04_un_protocolo_propone_el_nombre_y_con_un_si_lo_cambia(rig):
    session = open_current(rig)
    rig.answers = [True]
    result = await run(rig, "proponer_nombre", nombre="modo trabajo")
    (asked,) = rig.asked
    assert asked.question == Phrase("sesion.proponer_nombre", {"nombre": "modo trabajo"})
    assert asked.expected_type is ExpectedType.BOOLEAN
    assert result.speech == Phrase("sesion.nombrada", {"nombre": "modo trabajo"})
    current = row(rig, session.id)
    # El nombre cambia, pero no queda como fijado por el usuario.
    assert current.name == "modo trabajo" and not current.name_set_by_module


@pytest.mark.parametrize("answer", [False, CANCEL])
async def test_rn04_sin_un_si_el_nombre_no_cambia(rig, answer):
    session = open_current(rig)
    rig.answers = [answer]
    result = await run(rig, "proponer_nombre", nombre="modo trabajo")
    assert result.status == "completado" and result.speech is None
    assert row(rig, session.id).name == session.name


# --- Importancia -----------------------------------------------------------------------------


async def test_marcar_importante_bloquea_la_importancia(rig):
    session = open_current(rig)
    result = await run(rig, "marcar_importante")
    assert result.speech == Phrase("sesion.importante")
    current = row(rig, session.id)
    assert current.is_important and current.importance_locked_by_module
    assert rig.last(SessionChanged).is_important


async def test_desmarcar_quita_la_importancia_y_el_bloqueo(rig):
    session = open_current(rig)
    await run(rig, "marcar_importante")
    result = await run(rig, "desmarcar_importante")
    assert result.speech == Phrase("sesion.no_importante")
    current = row(rig, session.id)
    assert not current.is_important and not current.importance_locked_by_module
    assert not rig.last(SessionChanged).is_important


async def test_rn05_un_protocolo_la_marca_importante_aunque_el_usuario_la_desmarcara(rig):
    session = open_current(rig)
    await run(rig, "marcar_importante")
    await run(rig, "desmarcar_importante")
    result = await run(rig, "importante_por_protocolo")
    assert result.status == "completado" and result.speech is None
    current = row(rig, session.id)
    assert current.is_important and not current.importance_locked_by_module


async def test_rn05_si_ya_es_importante_el_protocolo_no_cambia_nada(rig):
    session = open_current(rig)
    await run(rig, "marcar_importante")
    rig.events.clear()
    await run(rig, "importante_por_protocolo")
    assert row(rig, session.id).importance_locked_by_module
    assert rig.events == []


def test_rn06_ninguna_accion_permite_a_un_protocolo_quitar_la_importancia(rig):
    # Las órdenes del usuario no valen en protocolos; las de protocolo solo suben la
    # importancia o proponen un nombre.
    in_protocols = {spec.action for spec in rig.manager.intents() if spec.in_protocols}
    assert in_protocols == set()


# --- Desbordamiento --------------------------------------------------------------------------


async def test_con_diez_importantes_marcar_la_actual_desplaza_la_mas_antigua(rig):
    old = important_sessions(rig, 10)
    session = open_current(rig)
    result = await run(rig, "marcar_importante")
    displaced = row(rig, old[0])
    assert not displaced.is_important
    assert displaced.pending_purge_on_close and displaced.displaced_by == session.id
    assert all(row(rig, other).is_important for other in old[1:])
    assert rig.sessions.count_important() == 10
    assert rig.last(SessionOverflowed) == SessionOverflowed(old[0], "vieja 0")
    assert rig.said == [Phrase("sesion.desbordamiento", {"nombre": "vieja 0"})]
    assert result.speech == Phrase("sesion.importante")


async def test_con_nueve_importantes_no_hay_desbordamiento(rig):
    old = important_sessions(rig, 9)
    open_current(rig)
    await run(rig, "marcar_importante")
    assert all(row(rig, other).is_important for other in old)
    assert rig.of(SessionOverflowed) == [] and rig.said == []


async def test_desmarcar_la_actual_restaura_la_desplazada(rig):
    old = important_sessions(rig, 10)
    open_current(rig)
    await run(rig, "marcar_importante")
    await run(rig, "desmarcar_importante")
    restored = row(rig, old[0])
    assert restored.is_important
    assert not restored.pending_purge_on_close and restored.displaced_by is None


async def test_cerrar_la_actual_elimina_la_desplazada_de_forma_logica(rig):
    old = important_sessions(rig, 10)
    open_current(rig)
    await run(rig, "marcar_importante")
    rig.manager.close_session("voz")
    purged = row(rig, old[0])
    assert purged is not None and purged.is_deleted  # no hay DELETE físico


async def test_el_desbordamiento_tambien_vale_para_un_protocolo(rig):
    old = important_sessions(rig, 10)
    session = open_current(rig)
    await run(rig, "importante_por_protocolo")
    assert row(rig, old[0]).displaced_by == session.id
    assert rig.said == [Phrase("sesion.desbordamiento", {"nombre": "vieja 0"})]


async def test_sin_sesion_abierta_las_acciones_fallan(rig):
    result = await run(rig, "marcar_importante")
    assert result.status == "error"
