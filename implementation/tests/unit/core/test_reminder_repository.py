"""`ReminderRepository` (T-5.2; persistencia.md) y el planificador sobre el reloj (T-5.4)."""
from datetime import UTC, datetime, timedelta

import pytest

from fakes.clock import FakeClock
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.repositories import ReminderRepository
from jarvis_assistant.core.scheduler import ApsScheduler, ClockScheduler, Scheduler

NOW = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)


@pytest.fixture
def db():
    database = Database(":memory:")
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def repo(db):
    return ReminderRepository(db)


def test_crear_guarda_el_recordatorio_y_sus_avisos(repo):
    reminder_id = repo.create("Llamar a Ana", [NOW + 2 * HOUR, NOW + HOUR], NOW + 3 * HOUR, NOW)
    reminder = repo.get(reminder_id)
    assert reminder is not None
    assert (reminder.content, reminder.status, reminder.deadline) == (
        "Llamar a Ana", "activo", NOW + 3 * HOUR,
    )  # fmt: skip
    assert [t.at for t in reminder.triggers] == [NOW + HOUR, NOW + 2 * HOUR]  # por fecha
    assert reminder.next_trigger == NOW + HOUR
    assert reminder.last_fired is None


def test_crear_es_una_transaccion(repo, db):
    with pytest.raises(ValueError):
        repo.create("Sin zona", [datetime(2026, 3, 2, 10)], None, NOW)  # fecha sin zona
    assert db.conn.execute("SELECT count(*) FROM reminders").fetchone()[0] == 0


def test_listable_son_activos_y_vencidos_por_identificador(repo):
    first = repo.create("a", [NOW + HOUR], None, NOW)
    second = repo.create("b", [NOW + HOUR], None, NOW)
    third = repo.create("c", [NOW + HOUR], None, NOW)
    repo.set_status(second, "eliminado")
    repo.set_status(third, "vencido")
    assert [r.id for r in repo.listable()] == [first, third]


def test_avisos_vencidos_y_futuros_de_recordatorios_activos(repo):
    active = repo.create("a", [NOW - HOUR, NOW + HOUR], None, NOW - 2 * HOUR)
    gone = repo.create("b", [NOW - HOUR], None, NOW - 2 * HOUR)
    repo.set_status(gone, "eliminado")
    (due,) = repo.due_triggers(NOW)
    (future,) = repo.future_triggers(NOW)
    assert (due.reminder_id, due.at) == (active, NOW - HOUR)
    assert (future.reminder_id, future.at) == (active, NOW + HOUR)
    repo.mark_fired(due.id)
    assert repo.due_triggers(NOW) == []
    assert repo.get(active).last_fired.id == due.id


def test_posponer_un_aviso_lo_reprograma_sin_disparar(repo):
    reminder_id = repo.create("a", [NOW], None, NOW - HOUR)
    (trigger,) = repo.get(reminder_id).triggers
    repo.mark_fired(trigger.id)
    repo.reschedule_trigger(trigger.id, NOW + HOUR)
    (moved,) = repo.get(reminder_id).triggers
    assert (moved.at, moved.is_fired) == (NOW + HOUR, False)


def test_fechas_limite_vencidas(repo):
    late = repo.create("a", [NOW - 2 * HOUR], NOW - HOUR, NOW - 3 * HOUR)
    repo.create("b", [NOW + HOUR], NOW + 2 * HOUR, NOW)
    assert [r.id for r in repo.overdue(NOW)] == [late]
    repo.set_status(late, "vencido")
    assert repo.overdue(NOW) == []


def test_cambiar_la_fecha_limite(repo):
    reminder_id = repo.create("a", [NOW + HOUR], NOW + 2 * HOUR, NOW)
    repo.set_deadline(reminder_id, NOW + 5 * HOUR)
    assert repo.get(reminder_id).deadline == NOW + 5 * HOUR


def test_eliminar_no_toca_los_avisos(repo, db):
    reminder_id = repo.create("a", [NOW + HOUR], None, NOW)
    repo.set_status(reminder_id, "eliminado")
    assert repo.get(reminder_id).status == "eliminado"
    assert db.conn.execute("SELECT count(*) FROM reminder_triggers").fetchone()[0] == 1


def test_una_fecha_en_otra_zona_se_compara_en_utc(repo):
    madrid = datetime(2026, 3, 2, 10, 30, tzinfo=UTC).astimezone()  # misma hora, otra zona
    repo.create("a", [madrid], None, NOW)
    assert repo.due_triggers(datetime(2026, 3, 2, 10, 31, tzinfo=UTC)) != []
    assert repo.due_triggers(datetime(2026, 3, 2, 10, 29, tzinfo=UTC)) == []


# --- Planificador ----------------------------------------------------------------------------


def test_el_planificador_del_reloj_cumple_la_interfaz():
    assert isinstance(ClockScheduler(FakeClock()), Scheduler)
    assert isinstance(ApsScheduler(), Scheduler)


def test_un_trabajo_vence_en_su_fecha():
    clock = FakeClock(NOW)
    scheduler = ClockScheduler(clock)
    ran: list[str] = []
    scheduler.add("a", NOW + timedelta(seconds=30), lambda: ran.append("a"))
    assert scheduler.jobs() == {"a": NOW + timedelta(seconds=30)}
    clock.advance(29)
    assert ran == []
    clock.advance(1)
    assert ran == ["a"]
    assert scheduler.jobs() == {}


def test_el_mismo_identificador_sustituye_al_trabajo():
    clock = FakeClock(NOW)
    scheduler = ClockScheduler(clock)
    ran: list[str] = []
    scheduler.add("a", NOW + timedelta(seconds=10), lambda: ran.append("viejo"))
    scheduler.add("a", NOW + timedelta(seconds=20), lambda: ran.append("nuevo"))
    clock.advance(30)
    assert ran == ["nuevo"]


def test_una_fecha_pasada_vence_en_seguida_y_se_puede_anular():
    clock = FakeClock(NOW)
    scheduler = ClockScheduler(clock)
    ran: list[str] = []
    scheduler.add("pasado", NOW - HOUR, lambda: ran.append("pasado"))
    scheduler.add("b", NOW + HOUR, lambda: ran.append("b"))
    scheduler.add("c", NOW + HOUR, lambda: ran.append("c"))
    scheduler.remove("b")
    scheduler.remove("no existe")
    clock.advance(0)
    assert ran == ["pasado"]
    scheduler.remove_all()
    clock.advance(2 * 3600)
    assert ran == ["pasado"]


def test_un_trabajo_que_falla_no_detiene_a_los_demas():
    clock = FakeClock(NOW)
    scheduler = ClockScheduler(clock)
    ran: list[str] = []
    scheduler.add("roto", NOW, lambda: 1 / 0)
    scheduler.add("bien", NOW, lambda: ran.append("bien"))
    clock.advance(0)
    assert ran == ["bien"]


async def test_apscheduler_ejecuta_el_trabajo_en_el_bucle():
    import asyncio
    import threading

    scheduler = ApsScheduler()
    done = asyncio.Event()
    threads: list[int] = []

    def job() -> None:
        threads.append(threading.get_ident())
        done.set()

    try:
        scheduler.add("a", datetime.now(UTC) + timedelta(milliseconds=50), job)
        assert set(scheduler.jobs()) == {"a"}
        await asyncio.wait_for(done.wait(), 5)
        assert threads == [threading.get_ident()]  # el hilo del núcleo, no uno del ejecutor
        scheduler.add("b", datetime.now(UTC) + HOUR, job)
        scheduler.remove("b")
        scheduler.remove("b")
        assert scheduler.jobs() == {}
    finally:
        scheduler.shutdown()


# --- Perfiles --------------------------------------------------------------------------------


def test_cada_perfil_solo_ve_sus_recordatorios(db):
    work, home = ReminderRepository(db, "trabajo"), ReminderRepository(db, "casa")
    mine = work.create("Informe", [NOW - HOUR], NOW - HOUR, NOW - 2 * HOUR)
    home.create("Comprar pan", [NOW - HOUR], NOW - HOUR, NOW - 2 * HOUR)
    assert [r.content for r in work.listable()] == ["Informe"]
    assert [r.content for r in home.listable()] == ["Comprar pan"]
    assert [t.reminder_id for t in work.due_triggers(NOW)] == [mine]
    assert [r.id for r in work.overdue(NOW)] == [mine]
    assert home.get(mine) is None  # tampoco por su id


def test_un_perfil_no_cambia_los_recordatorios_de_otro(db):
    work, home = ReminderRepository(db, "trabajo"), ReminderRepository(db, "casa")
    mine = work.create("Informe", [NOW + HOUR], None, NOW)
    home.set_status(mine, "eliminado")
    home.set_deadline(mine, NOW + 2 * HOUR)
    reminder = work.get(mine)
    assert reminder is not None
    assert (reminder.status, reminder.deadline) == ("activo", None)
