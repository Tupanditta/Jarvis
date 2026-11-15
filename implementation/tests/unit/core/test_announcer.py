"""Cola de voz: una respuesta cada vez, en orden de llegada (`core/announcer.py`)."""
import asyncio

import pytest

from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.core.announcer import Announcement, Announcer


class Voice:
    """Doble de la voz: cada frase suena hasta que la prueba la deja terminar."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.finished: list[str] = []
        self.stops = 0
        self.fail_on: str | None = None
        self._current: asyncio.Future[bool] | None = None

    async def say(self, phrase: Phrase) -> bool:
        if phrase.id == self.fail_on:
            raise RuntimeError("la voz ha fallado")
        self.started.append(phrase.id)
        self._current = asyncio.get_running_loop().create_future()
        interrupted = await self._current
        self.finished.append(phrase.id)
        return interrupted

    def stop(self) -> None:
        self.stops += 1
        if self._current is not None and not self._current.done():
            self._current.set_result(True)

    async def end(self) -> None:
        """La frase en curso termina de sonar."""
        assert self._current is not None
        self._current.set_result(False)
        await settle()


async def settle() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


def answer(*ids: str, **callbacks) -> Announcement:
    return Announcement(tuple(Phrase(i) for i in ids), **callbacks)


@pytest.fixture
def voice() -> Voice:
    return Voice()


async def test_las_respuestas_se_dicen_de_una_en_una_en_orden_de_llegada(voice):
    idle = []
    announcer = Announcer(voice.say, voice.stop, on_idle=lambda: idle.append(True))
    announcer.submit(answer("a"))
    announcer.submit(answer("b"))
    await settle()
    assert voice.started == ["a"] and announcer.active  # «b» no se solapa con «a»
    await voice.end()
    assert voice.started == ["a", "b"] and idle == []
    await voice.end()
    assert not announcer.active and idle == [True]


async def test_las_frases_de_una_respuesta_van_seguidas(voice):
    announcer = Announcer(voice.say, voice.stop)
    announcer.submit(answer("a1", "a2"))
    announcer.submit(answer("b"))
    await settle()
    await voice.end()
    await voice.end()
    await voice.end()
    assert voice.finished == ["a1", "a2", "b"]


async def test_una_respuesta_cortada_no_dice_sus_frases_restantes_y_las_demas_siguen(voice):
    announcer = Announcer(voice.say, voice.stop)
    announcer.submit(answer("a1", "a2"))
    announcer.submit(answer("b"))
    await settle()
    voice.stop()  # se corta solo la frase que suena
    await settle()
    assert voice.started == ["a1", "b"]


async def test_callar_corta_la_respuesta_en_curso_y_descarta_las_que_esperaban(voice):
    announcer = Announcer(voice.say, voice.stop)
    announcer.submit(answer("a"))
    announcer.submit(answer("b"))
    await settle()
    assert announcer.clear() is True
    await settle()
    assert voice.started == ["a"] and not announcer.active
    assert announcer.clear() is False  # no había nada


async def test_lo_que_se_pide_despues_de_callar_si_se_dice(voice):
    announcer = Announcer(voice.say, voice.stop)
    announcer.submit(answer("a"))
    await settle()
    announcer.clear()
    announcer.submit(answer("cancelado"))
    await settle()
    assert voice.started == ["a", "cancelado"]


async def test_avisa_al_empezar_y_al_terminar_cada_respuesta(voice):
    log: list[str] = []
    announcer = Announcer(voice.say, voice.stop)
    announcer.submit(
        answer("a", on_start=lambda: log.append("empieza"),
               on_delivered=lambda: log.append("entregada"))
    )  # fmt: skip
    await settle()
    assert log == ["empieza"]
    await voice.end()
    assert log == ["empieza", "entregada"]


async def test_una_respuesta_que_falla_no_detiene_las_siguientes(voice, caplog):
    voice.fail_on = "rota"
    announcer = Announcer(voice.say, voice.stop)
    announcer.submit(answer("rota"))
    announcer.submit(answer("b"))
    await settle()
    assert voice.started == ["b"]
    assert "No se ha podido decir una respuesta" in caplog.text
