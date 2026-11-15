"""Cola de órdenes: qué puede empezar y cuándo (`core/task_queue.py`)."""
import pytest

from jarvis_assistant.core.task_queue import Claim, TaskQueue


def claim(*lanes: str, reads: str = "", writes: str = "") -> Claim:
    return Claim(frozenset(lanes), frozenset(reads.split()), frozenset(writes.split()))


def texts(jobs) -> list[str]:
    return [job.payload for job in jobs]


def test_las_ordenes_de_modulos_distintos_empiezan_a_la_vez():
    queue: TaskQueue[str] = TaskQueue()
    queue.add(claim("comandos"), "lista")
    queue.add(claim("apertura"), "abre github")
    queue.add(claim("busqueda"), "busca informe")
    assert texts(queue.take_ready()) == ["lista", "abre github", "busca informe"]
    assert queue.waiting == [] and len(queue.running) == 3


def test_las_ordenes_de_un_mismo_modulo_se_ejecutan_de_una_en_una_y_en_su_orden():
    queue: TaskQueue[str] = TaskQueue()
    first = queue.add(claim("comandos"), "uno")
    second = queue.add(claim("comandos"), "dos")
    queue.add(claim("comandos"), "tres")
    assert texts(queue.take_ready()) == ["uno"]
    assert queue.take_ready() == []  # nada nuevo hasta que termine la primera
    queue.finish(first)
    assert texts(queue.take_ready()) == ["dos"]
    queue.finish(second)
    assert texts(queue.take_ready()) == ["tres"]


def test_una_orden_espera_a_la_anterior_que_cambia_lo_que_ella_usa():
    """«ve a proyectos -- crea el archivo notas»: módulos distintos, pero en orden."""
    queue: TaskQueue[str] = TaskQueue()
    cd = queue.add(claim("comandos", reads="workdir", writes="workdir"), "ve a proyectos")
    queue.add(claim("creacion", reads="workdir"), "crea notas")
    queue.add(claim("busqueda"), "busca informe")
    assert texts(queue.take_ready()) == ["ve a proyectos", "busca informe"]
    queue.finish(cd)
    assert texts(queue.take_ready()) == ["crea notas"]


def test_quien_cambia_un_recurso_espera_a_los_anteriores_que_lo_usan():
    queue: TaskQueue[str] = TaskQueue()
    reader = queue.add(claim("apertura", reads="workdir"), "abre esta carpeta")
    queue.add(claim("comandos", writes="workdir"), "ve a docs")
    assert texts(queue.take_ready()) == ["abre esta carpeta"]
    queue.finish(reader)
    assert texts(queue.take_ready()) == ["ve a docs"]


def test_varias_lecturas_del_mismo_recurso_no_se_esperan():
    queue: TaskQueue[str] = TaskQueue()
    queue.add(claim("comandos", reads="workdir"), "lista")
    queue.add(claim("apertura", reads="workdir"), "abre esta carpeta")
    assert len(queue.take_ready()) == 2


def test_una_orden_en_espera_tambien_bloquea_a_las_posteriores():
    """El orden se respeta aunque la que bloquea todavía no haya empezado."""
    queue: TaskQueue[str] = TaskQueue()
    running = queue.add(claim("comandos"), "ejecuta algo")
    queue.add(claim("comandos", writes="workdir"), "ve a docs")
    queue.add(claim("apertura", reads="workdir"), "abre esta carpeta")
    assert texts(queue.take_ready()) == ["ejecuta algo"]
    assert texts(queue.waiting) == ["ve a docs", "abre esta carpeta"]
    queue.finish(running)
    assert texts(queue.take_ready()) == ["ve a docs"]


def test_una_orden_ambigua_ocupa_todos_sus_modulos_hasta_que_se_resuelve():
    queue: TaskQueue[str] = TaskQueue()
    ambiguous = queue.add(claim("apertura", "comandos"), "abre la consola")
    queue.add(claim("comandos"), "lista")
    assert queue.take_ready() == [ambiguous]
    queue.narrow(ambiguous, claim("apertura"))  # al resolverse era de «apertura»
    assert texts(queue.take_ready()) == ["lista"]


def test_lo_que_ocupa_una_orden_solo_se_puede_reducir():
    queue: TaskQueue[str] = TaskQueue()
    job = queue.add(claim("comandos"), "lista")
    with pytest.raises(ValueError):
        queue.narrow(job, claim("comandos", writes="workdir"))
    with pytest.raises(ValueError):
        queue.narrow(job, claim("apertura"))


def test_vaciar_la_cola_devuelve_las_que_quedaban():
    queue: TaskQueue[str] = TaskQueue()
    queue.add(claim("comandos"), "uno")
    queue.add(claim("comandos"), "dos")
    (started,) = queue.take_ready()
    assert texts(queue.clear()) == ["uno", "dos"]
    assert len(queue) == 0
    queue.finish(started)  # terminar una orden que ya no está no hace nada
    assert len(queue) == 0
