"""Reloj real y reloj falso con temporizadores controlables (T-0.3)."""
import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from fakes.clock import FakeClock
from jarvis_assistant.core.clock import Clock, SystemClock

START = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)


# --- Reloj falso -----------------------------------------------------------------------------


def test_el_reloj_falso_cumple_el_protocolo():
    assert isinstance(FakeClock(), Clock)


def test_empieza_en_el_instante_indicado():
    assert FakeClock(START).now() == START


def test_rechaza_un_inicio_sin_zona_horaria():
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 11, 14))


def test_el_tiempo_solo_avanza_cuando_se_pide():
    clock = FakeClock(START)
    before = clock.monotonic()
    clock.advance(2.5)
    assert clock.now() == START + timedelta(seconds=2.5)
    assert clock.monotonic() == pytest.approx(before + 2.5)


def test_no_retrocede():
    with pytest.raises(ValueError):
        FakeClock().advance(-1)


def test_un_temporizador_no_dispara_antes_de_tiempo():
    clock = FakeClock()
    fired = []
    clock.call_later(10, lambda: fired.append("a"))
    clock.advance(9.999)
    assert fired == []
    clock.advance(0.001)
    assert fired == ["a"]


def test_los_temporizadores_disparan_en_orden_de_vencimiento_y_de_creacion():
    clock = FakeClock()
    fired = []
    clock.call_later(3, lambda: fired.append("tres"))
    clock.call_later(1, lambda: fired.append("uno"))
    clock.call_later(3, lambda: fired.append("tres bis"))
    clock.advance(5)
    assert fired == ["uno", "tres", "tres bis"]


def test_durante_el_disparo_el_reloj_marca_el_vencimiento():
    clock = FakeClock(START)
    seen = []
    clock.call_later(4, lambda: seen.append(clock.now()))
    clock.advance(30)
    assert seen == [START + timedelta(seconds=4)]
    assert clock.now() == START + timedelta(seconds=30)


def test_un_temporizador_cancelado_no_dispara():
    clock = FakeClock()
    fired = []
    handle = clock.call_later(1, lambda: fired.append("a"))
    handle.cancel()
    handle.cancel()
    clock.advance(5)
    assert fired == []


def test_un_temporizador_puede_programar_otro_dentro_del_mismo_avance():
    clock = FakeClock()
    fired = []

    def first():
        fired.append("primero")
        clock.call_later(1, lambda: fired.append("segundo"))

    clock.call_later(1, first)
    clock.advance(2)
    assert fired == ["primero", "segundo"]


def test_pending_informa_de_los_temporizadores_vivos():
    clock = FakeClock()
    clock.call_later(5, lambda: None)
    cancelled = clock.call_later(2, lambda: None)
    cancelled.cancel()
    assert clock.pending == [5.0]
    clock.advance(5)
    assert clock.pending == []


def test_rechaza_un_retardo_negativo():
    with pytest.raises(ValueError):
        FakeClock().call_later(-0.1, lambda: None)


async def test_sleep_termina_al_avanzar_el_reloj():
    clock = FakeClock()
    task = asyncio.ensure_future(clock.sleep(30))
    await asyncio.sleep(0)
    clock.advance(29)
    await asyncio.sleep(0)
    assert not task.done()
    clock.advance(1)
    await task


async def test_cancelar_sleep_retira_su_temporizador():
    clock = FakeClock()
    task = asyncio.ensure_future(clock.sleep(30))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert clock.pending == []


# --- Reloj real ------------------------------------------------------------------------------


def test_el_reloj_real_cumple_el_protocolo():
    assert isinstance(SystemClock(), Clock)


def test_el_reloj_real_da_la_hora_en_utc():
    before = datetime.now(UTC)
    now = SystemClock().now()
    assert now.tzinfo is UTC
    assert before <= now <= datetime.now(UTC)


def test_el_reloj_real_es_monotono():
    clock = SystemClock()
    assert clock.monotonic() <= clock.monotonic()


async def test_el_reloj_real_programa_en_el_bucle_de_asyncio():
    clock = SystemClock()
    fired = asyncio.Event()
    clock.call_later(0, fired.set)
    await asyncio.wait_for(fired.wait(), 1)


async def test_un_temporizador_real_cancelado_no_dispara():
    clock = SystemClock()
    fired = []
    clock.call_later(0, lambda: fired.append(1)).cancel()
    await clock.sleep(0)
    await asyncio.sleep(0)
    assert fired == []
