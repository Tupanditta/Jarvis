"""Repositorios de sesiones y actividades sobre las migraciones reales (T-0.7)."""
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from jarvis_assistant.core.database import Database
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository

T0 = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


@pytest.fixture
def db():
    database = Database(":memory:")
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def sessions(db):
    return SessionRepository(db)


@pytest.fixture
def activities(db):
    return ActivityRepository(db)


# --- Sesiones --------------------------------------------------------------------------------


def test_crear_una_sesion_la_deja_abierta_y_sin_marcas(sessions):
    session_id = sessions.create("14 de noviembre", at(0))
    row = sessions.get(session_id)
    assert (row.id, row.name, row.opened_at) == (session_id, "14 de noviembre", at(0))
    assert (row.closed_at, row.close_reason, row.displaced_by) == (None, None, None)
    assert not any(
        [
            row.is_important,
            row.name_set_by_module,
            row.importance_locked_by_module,
            row.pending_purge_on_close,
            row.is_deleted,
        ]
    )


def test_los_identificadores_son_numeros_crecientes(sessions):
    first = sessions.create("a", at(0))
    second = sessions.create("b", at(1))
    assert isinstance(first, int) and second == first + 1


def test_get_de_una_sesion_inexistente_devuelve_none(sessions):
    assert sessions.get(99) is None


def test_un_nombre_vacio_se_rechaza(sessions):
    with pytest.raises(sqlite3.IntegrityError):
        sessions.create("   ", at(0))


def test_cerrar_fija_el_momento_y_el_motivo(sessions):
    session_id = sessions.create("a", at(0))
    sessions.close(session_id, at(30), "voz")
    row = sessions.get(session_id)
    assert (row.closed_at, row.close_reason) == (at(30), "voz")


def test_un_motivo_de_cierre_desconocido_se_rechaza(sessions):
    session_id = sessions.create("a", at(0))
    with pytest.raises(sqlite3.IntegrityError):
        sessions.close(session_id, at(1), "porque sí")
    assert sessions.get(session_id).closed_at is None


def test_find_open_devuelve_solo_las_sesiones_sin_cerrar(sessions):
    closed = sessions.create("cerrada", at(0))
    sessions.close(closed, at(5), "salida")
    opened = sessions.create("abierta", at(10))
    assert [row.id for row in sessions.find_open()] == [opened]


def test_renombrar_por_el_usuario_fija_la_marca(sessions):
    session_id = sessions.create("a", at(0))
    sessions.rename(session_id, "trabajo", by_user=True)
    row = sessions.get(session_id)
    assert (row.name, row.name_set_by_module) == ("trabajo", True)


def test_renombrar_por_un_protocolo_no_toca_la_marca(sessions):
    session_id = sessions.create("a", at(0))
    sessions.rename(session_id, "modo trabajo", by_user=False)
    assert sessions.get(session_id).name_set_by_module is False
    sessions.rename(session_id, "mío", by_user=True)
    sessions.rename(session_id, "otro", by_user=False)
    assert sessions.get(session_id).name_set_by_module is True


def test_la_importancia_marcada_por_el_usuario_queda_bloqueada(sessions):
    session_id = sessions.create("a", at(0))
    sessions.set_importance(session_id, True, by_user=True)
    row = sessions.get(session_id)
    assert (row.is_important, row.importance_locked_by_module) == (True, True)
    sessions.set_importance(session_id, False, by_user=True)
    row = sessions.get(session_id)
    assert (row.is_important, row.importance_locked_by_module) == (False, False)


def test_la_importancia_por_protocolo_no_toca_el_bloqueo(sessions):
    session_id = sessions.create("a", at(0))
    sessions.set_importance(session_id, True, by_user=False)
    row = sessions.get(session_id)
    assert (row.is_important, row.importance_locked_by_module) == (True, False)


def test_count_important_no_cuenta_las_eliminadas(sessions):
    ids = [sessions.create(f"s{i}", at(i)) for i in range(3)]
    for session_id in ids:
        sessions.set_importance(session_id, True, by_user=True)
    sessions.soft_delete(ids[0])
    assert sessions.count_important() == 2


def test_oldest_important_es_la_de_apertura_mas_antigua_distinta_de_la_excluida(sessions):
    old = sessions.create("vieja", at(0))
    middle = sessions.create("media", at(10))
    new = sessions.create("nueva", at(20))
    plain = sessions.create("normal", at(-5))
    for session_id in (old, middle, new):
        sessions.set_importance(session_id, True, by_user=True)
    assert sessions.oldest_important(excluding=new).id == old
    assert sessions.oldest_important(excluding=old).id == middle
    sessions.soft_delete(old)
    assert sessions.oldest_important(excluding=new).id == middle
    assert plain not in {old, middle, new}


def test_oldest_important_sin_candidatas_devuelve_none(sessions):
    only = sessions.create("única", at(0))
    sessions.set_importance(only, True, by_user=True)
    assert sessions.oldest_important(excluding=only) is None


def test_marcar_y_desmarcar_el_desbordamiento(sessions):
    displaced = sessions.create("desplazada", at(0))
    current = sessions.create("actual", at(10))
    sessions.mark_pending_purge(displaced, True, displaced_by=current)
    row = sessions.get(displaced)
    assert (row.pending_purge_on_close, row.displaced_by) == (True, current)
    sessions.mark_pending_purge(displaced, False, displaced_by=None)
    row = sessions.get(displaced)
    assert (row.pending_purge_on_close, row.displaced_by) == (False, None)


def test_purge_pending_elimina_solo_las_marcadas_por_esa_sesion(sessions):
    marked = sessions.create("marcada", at(0))
    other = sessions.create("de otra", at(1))
    restored = sessions.create("restaurada", at(2))
    current = sessions.create("actual", at(10))
    another = sessions.create("otra actual", at(11))
    sessions.mark_pending_purge(marked, True, displaced_by=current)
    sessions.mark_pending_purge(other, True, displaced_by=another)
    sessions.mark_pending_purge(restored, True, displaced_by=current)
    sessions.mark_pending_purge(restored, False, displaced_by=None)

    assert sessions.purge_pending(displaced_by=current) == [marked]
    assert sessions.get(marked).is_deleted is True
    assert sessions.get(other).is_deleted is False
    assert sessions.get(restored).is_deleted is False
    assert sessions.purge_pending(displaced_by=current) == []


def test_soft_delete_conserva_la_fila(sessions):
    session_id = sessions.create("a", at(0))
    sessions.soft_delete(session_id)
    row = sessions.get(session_id)
    assert row is not None and row.is_deleted is True


def test_el_historial_muestra_primero_las_importantes_y_despues_las_mas_recientes(sessions):
    ids = {name: sessions.create(name, at(i)) for i, name in enumerate("abcde")}
    sessions.set_importance(ids["b"], True, by_user=True)
    sessions.set_importance(ids["d"], True, by_user=False)
    sessions.soft_delete(ids["e"])
    assert [row.name for row in sessions.visible_history()] == ["d", "b", "c", "a"]


def test_el_historial_muestra_como_maximo_10_sesiones(sessions):
    for i in range(12):
        sessions.create(f"s{i:02}", at(i))
    history = sessions.visible_history()
    assert [row.name for row in history] == [f"s{i:02}" for i in range(11, 1, -1)]
    assert len(sessions.visible_history(limit=3)) == 3


def test_name_exists_ignora_mayusculas_espacios_y_sesiones_eliminadas(sessions):
    kept = sessions.create("Modo Trabajo", at(0))
    deleted = sessions.create("Antigua", at(1))
    sessions.soft_delete(deleted)
    assert sessions.name_exists("  modo trabajo ")
    assert not sessions.name_exists("antigua")
    assert not sessions.name_exists("otra")
    assert kept != deleted


# --- Actividades -----------------------------------------------------------------------------


def test_una_actividad_nace_pendiente(sessions, activities):
    session_id = sessions.create("a", at(0))
    activity_id = activities.add(session_id, "comandos", "Listar la carpeta", at(1))
    (row,) = activities.of_session(session_id)
    assert (row.id, row.session_id, row.parent_id) == (activity_id, session_id, None)
    assert (row.module, row.description) == ("comandos", "Listar la carpeta")
    assert row.status == "pendiente"
    assert (row.executed_at, row.finished_at) == (at(1), None)


def test_una_actividad_necesita_una_sesion_existente(activities):
    with pytest.raises(sqlite3.IntegrityError):
        activities.add(99, "comandos", "x", at(0))


def test_finish_fija_el_estado_final_y_el_momento(sessions, activities):
    session_id = sessions.create("a", at(0))
    activity_id = activities.add(session_id, "comandos", "Listar", at(1))
    activities.finish(activity_id, "completado", at=at(2))
    (row,) = activities.of_session(session_id)
    assert (row.status, row.description, row.finished_at) == ("completado", "Listar", at(2))


def test_finish_puede_sustituir_la_descripcion(sessions, activities):
    session_id = sessions.create("a", at(0))
    activity_id = activities.add(session_id, "apertura", "Abrir", at(1))
    activities.finish(activity_id, "error", "Abrir Paint: no encontrada")
    (row,) = activities.of_session(session_id)
    assert (row.status, row.description) == ("error", "Abrir Paint: no encontrada")


def test_finish_rechaza_un_estado_desconocido(sessions, activities):
    session_id = sessions.create("a", at(0))
    activity_id = activities.add(session_id, "comandos", "Listar", at(1))
    with pytest.raises(sqlite3.IntegrityError):
        activities.finish(activity_id, "cancelado")
    assert activities.of_session(session_id)[0].status == "pendiente"


def test_las_subtareas_de_un_protocolo_llevan_a_su_padre(sessions, activities):
    session_id = sessions.create("a", at(0))
    parent = activities.add(session_id, "protocolos", "Protocolo modo trabajo", at(1))
    child = activities.add(session_id, "comandos", "cd proyectos", at(2), parent_id=parent)
    rows = activities.of_session(session_id)
    assert [(row.id, row.parent_id) for row in rows] == [(parent, None), (child, parent)]


def test_of_session_devuelve_solo_las_de_esa_sesion_en_orden(sessions, activities):
    first = sessions.create("a", at(0))
    second = sessions.create("b", at(1))
    ids = [activities.add(first, "m", f"t{i}", at(i)) for i in range(3)]
    activities.add(second, "m", "ajena", at(5))
    assert [row.id for row in activities.of_session(first)] == ids


def test_fail_pending_pasa_a_error_las_pendientes_con_su_motivo(sessions, activities):
    session_id = sessions.create("a", at(0))
    other_session = sessions.create("b", at(0))
    done = activities.add(session_id, "m", "terminada", at(1))
    activities.finish(done, "completado", at=at(2))
    activities.add(session_id, "comandos", "git status", at(3))
    activities.add(other_session, "m", "de otra sesión", at(3))

    activities.fail_pending(session_id, "sesión cerrada", at=at(9))

    rows = activities.of_session(session_id)
    assert [(row.status, row.description) for row in rows] == [
        ("completado", "terminada"),
        ("error", "git status (sesión cerrada)"),
    ]
    assert (rows[0].finished_at, rows[1].finished_at) == (at(2), at(9))
    assert activities.of_session(other_session)[0].status == "pendiente"


# --- Transacciones y concurrencia ------------------------------------------------------------


def test_varias_operaciones_de_repositorio_caben_en_una_transaccion(db, sessions):
    current = sessions.create("actual", at(10))
    old = sessions.create("vieja", at(0))
    sessions.set_importance(old, True, by_user=True)
    with pytest.raises(RuntimeError), db.transaction():
        sessions.set_importance(old, False, by_user=False)
        sessions.mark_pending_purge(old, True, displaced_by=current)
        raise RuntimeError("fallo a mitad del desbordamiento")
    row = sessions.get(old)
    assert (row.is_important, row.pending_purge_on_close, row.displaced_by) == (True, False, None)


def test_consultar_el_historial_mientras_se_registra_una_actividad_no_bloquea(tmp_path):
    db = Database(tmp_path / "jarvis.db")
    db.migrate()
    sessions, activities = SessionRepository(db), ActivityRepository(db)
    session_id = sessions.create("a", at(0))
    reader = sqlite3.connect(tmp_path / "jarvis.db", timeout=0)
    try:
        with db.transaction():
            activities.add(session_id, "comandos", "en curso", at(1))
            # RNF-08: ni la propia conexión ni un lector externo ven un bloqueo.
            assert [row.id for row in sessions.visible_history()] == [session_id]
            assert reader.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        assert len(activities.of_session(session_id)) == 1
    finally:
        reader.close()
        db.close()
