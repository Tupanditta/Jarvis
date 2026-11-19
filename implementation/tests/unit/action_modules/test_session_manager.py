"""Sesión mínima: abrir, cerrar y recuperar sobre la base de datos (sesion.md)."""
from datetime import UTC, datetime, timedelta, timezone

import pytest

from fakes.clock import FakeClock
from jarvis_assistant.action_modules.session_manager import SessionManager
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import SessionChanged, SessionsDeleted
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository

START = datetime(2026, 11, 14, 22, 30, tzinfo=UTC)


@pytest.fixture
def db():
    database = Database(":memory:")
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def clock():
    return FakeClock(START)


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def manager(db, clock, bus):
    return SessionManager(db, clock, bus, local_tz=UTC)


def test_abrir_crea_la_fila_con_los_valores_por_defecto(manager, db, bus):
    published = []
    bus.subscribe(SessionChanged, published.append)
    session = manager.open_session()
    row = SessionRepository(db).get(session.id)
    assert row.name == "2026-11-14"
    assert not row.is_important
    assert row.opened_at == START
    assert row.closed_at is None
    assert manager.current == row
    assert published == [SessionChanged(row.id, "2026-11-14", False)]


def test_el_nombre_es_la_fecha_local(db, clock, bus):
    manager = SessionManager(db, clock, bus, local_tz=timezone(timedelta(hours=2)))
    assert manager.open_session().name == "2026-11-15"


def test_sufijo_cuando_el_nombre_ya_existe(manager, clock):
    names = []
    for _ in range(3):
        names.append(manager.open_session().name)
        manager.close_session("voz")
        clock.advance(60)
    assert names == ["2026-11-14", "2026-11-14 (2)", "2026-11-14 (3)"]


def test_cerrar_fija_la_fecha_y_el_motivo_y_falla_las_pendientes(manager, db, clock):
    session = manager.open_session()
    activities = ActivityRepository(db)
    pending = activities.add(session.id, "comandos", "ejecutar git status", clock.now())
    done = activities.add(session.id, "comandos", "ls", clock.now())
    activities.finish(done, "completado", at=clock.now())
    clock.advance(120)
    manager.close_session("voz")
    row = SessionRepository(db).get(session.id)
    assert row.closed_at == START + timedelta(seconds=120)
    assert row.close_reason == "voz"
    assert manager.current is None
    by_id = {a.id: a for a in activities.of_session(session.id)}
    assert by_id[pending].status == "error"
    assert by_id[pending].description == "ejecutar git status (sesión cerrada)"
    assert by_id[done].status == "completado"


def test_cerrar_elimina_las_sesiones_desplazadas_por_desbordamiento(manager, db, clock):
    sessions = SessionRepository(db)
    displaced = sessions.create("antigua", START - timedelta(days=30))
    sessions.close(displaced, START - timedelta(days=29), "voz")
    current = manager.open_session()
    sessions.mark_pending_purge(displaced, True, current.id)
    manager.close_session("salida")
    # La desplazada se borra del todo y la actual pasa a ser la 1.
    (remaining,) = sessions.visible_history(None)
    assert (remaining.id, remaining.name, remaining.close_reason) == (1, current.name, "salida")


def test_borrar_sesiones_anteriores_renumera_la_actual(manager, db, bus):
    sessions = SessionRepository(db)
    old = sessions.create("antigua", START - timedelta(days=3))
    current = manager.open_session()
    published = []
    bus.subscribe(SessionChanged, published.append)
    moves = sessions.delete([old])
    bus.publish(SessionsDeleted((old,), moves))
    assert manager.current.id == 1 == moves[current.id]
    assert published == [SessionChanged(1, current.name, False)]
    # Al cerrar se cierra la fila con su id nuevo.
    manager.close_session("voz")
    assert sessions.get(1).close_reason == "voz"


def test_borrar_sesiones_posteriores_no_cambia_la_actual(manager, db, bus):
    current = manager.open_session()
    published = []
    bus.subscribe(SessionChanged, published.append)
    bus.publish(SessionsDeleted((current.id + 1,), {}))
    assert manager.current == current and published == []


def test_cerrar_sin_sesion_no_hace_nada(manager):
    manager.close_session("voz")
    assert manager.current is None


def test_recuperar_cierra_la_sesion_huerfana_en_su_ultima_actividad(manager, db, clock):
    sessions, activities = SessionRepository(db), ActivityRepository(db)
    orphan = sessions.create("huérfana", START - timedelta(hours=5))
    last = START - timedelta(hours=4)
    activities.add(orphan, "comandos", "ls", START - timedelta(hours=4, minutes=30))
    pending = activities.add(orphan, "comandos", "ejecutar gcc", last)
    displaced = sessions.create("desplazada", START - timedelta(days=9))
    sessions.close(displaced, START - timedelta(days=8), "voz")
    sessions.mark_pending_purge(displaced, True, orphan)

    assert manager.recover_interrupted() == [orphan]
    row = sessions.get(orphan)
    assert row.close_reason == "interrumpida"
    assert row.closed_at == last
    assert activities.of_session(orphan)[1].id == pending
    assert all(a.status == "error" for a in activities.of_session(orphan))
    assert sessions.get(displaced) is None  # borrada del todo; era la última, nadie se mueve
    assert sessions.find_open() == []


def test_recuperar_sin_actividades_usa_la_fecha_de_apertura(manager, db):
    sessions = SessionRepository(db)
    opened = START - timedelta(hours=1)
    orphan = sessions.create("vacía", opened)
    manager.recover_interrupted()
    assert sessions.get(orphan).closed_at == opened
    assert manager.recover_interrupted() == []
