"""Bus de eventos: publicación/suscripción en el hilo del núcleo (T-0.6, bus-eventos.md)."""
import asyncio
import logging
import threading
from dataclasses import dataclass

import pytest

from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.events import Event


@dataclass(frozen=True)
class Ping(Event):
    value: int = 0


@dataclass(frozen=True)
class Pong(Event):
    pass


@dataclass(frozen=True)
class SubPing(Ping):
    pass


def test_entrega_el_evento_a_los_suscriptores_de_su_tipo():
    bus = EventBus()
    received = []
    bus.subscribe(Ping, received.append)
    bus.subscribe(Pong, received.append)
    bus.publish(Ping(7))
    assert received == [Ping(7)]


def test_los_manejadores_se_ejecutan_en_orden_de_suscripcion():
    bus = EventBus()
    order = []
    for name in "abc":
        bus.subscribe(Ping, lambda _event, name=name: order.append(name))
    bus.publish(Ping())
    assert order == ["a", "b", "c"]


def test_la_suscripcion_es_por_tipo_exacto():
    bus = EventBus()
    received = []
    bus.subscribe(Ping, received.append)
    bus.publish(SubPing())
    assert received == []


def test_publicar_sin_suscriptores_no_hace_nada():
    EventBus().publish(Ping())


def test_la_baja_deja_de_entregar_y_es_idempotente():
    bus = EventBus()
    received = []
    unsubscribe = bus.subscribe(Ping, received.append)
    unsubscribe()
    unsubscribe()
    bus.publish(Ping())
    assert received == []


def test_un_manejador_que_falla_se_registra_y_no_impide_la_entrega_a_los_demas(caplog):
    bus = EventBus()
    received = []

    def broken(_event):
        raise RuntimeError("roto")

    bus.subscribe(Ping, broken)
    bus.subscribe(Ping, received.append)
    with caplog.at_level(logging.ERROR, logger="jarvis_assistant.core.event_bus"):
        bus.publish(Ping(1))
    assert received == [Ping(1)]
    (record,) = caplog.records
    assert "Ping" in record.getMessage()
    assert record.exc_info is not None


def test_darse_de_baja_durante_la_entrega_no_altera_la_entrega_en_curso():
    bus = EventBus()
    received = []
    unsubscribe_second = None

    def first(_event):
        unsubscribe_second()

    bus.subscribe(Ping, first)
    unsubscribe_second = bus.subscribe(Ping, received.append)
    bus.publish(Ping(1))
    bus.publish(Ping(2))
    assert received == [Ping(1)]


def test_el_bus_no_guarda_eventos():
    bus = EventBus()
    bus.publish(Ping(1))
    received = []
    bus.subscribe(Ping, received.append)
    assert received == []


def test_solo_se_publican_eventos():
    with pytest.raises(TypeError):
        EventBus().publish("ping")


async def test_publicar_desde_otro_hilo_entrega_en_el_hilo_del_nucleo():
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    delivered = asyncio.Event()
    threads = []

    def handler(_event):
        threads.append(threading.current_thread())
        delivered.set()

    bus.subscribe(Ping, handler)
    worker = threading.Thread(target=bus.publish_threadsafe, args=(Ping(3),))
    worker.start()
    worker.join()
    assert threads == []  # todavía no se ha entregado: espera al bucle del núcleo
    await asyncio.wait_for(delivered.wait(), 1)
    assert threads == [threading.current_thread()]


async def test_publish_threadsafe_conserva_el_orden_de_publicacion():
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    received = []
    bus.subscribe(Ping, received.append)

    def publish_all():
        for value in range(5):
            bus.publish_threadsafe(Ping(value))

    worker = threading.Thread(target=publish_all)
    worker.start()
    worker.join()
    await asyncio.sleep(0.01)
    assert received == [Ping(value) for value in range(5)]


def test_publish_threadsafe_sin_bucle_es_un_error_de_composicion():
    with pytest.raises(RuntimeError):
        EventBus().publish_threadsafe(Ping())


def test_publish_threadsafe_con_el_bucle_cerrado_se_descarta(caplog):
    loop = asyncio.new_event_loop()
    bus = EventBus()
    bus.bind_loop(loop)
    loop.close()
    bus.publish_threadsafe(Ping())  # el proceso está saliendo: no debe lanzar
