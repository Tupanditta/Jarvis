"""Fechas, horas y duraciones escritas (T-5.1; enrutador-intenciones.md, secciones 4 y 5) y su
forma hablada (catalogo-intenciones.md, sección 5).

El momento actual es fijo: lunes 2 de marzo de 2026 a las 10:00, hora local UTC+1.
"""
from datetime import UTC, datetime, timedelta, timezone

import pytest

from jarvis_assistant.intent_router.normalizer import normalize
from jarvis_assistant.intent_router.slots import datetimes, durations
from jarvis_assistant.speaker import formats

TZ = timezone(timedelta(hours=1))
NOW = datetime(2026, 3, 2, 10, 0, tzinfo=TZ)  # lunes


def at(day: int, hour: int = 9, minute: int = 0, month: int = 3, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=TZ)


def parse(text: str, now: datetime = NOW) -> datetime | None:
    return datetimes.parse(normalize(text).split(), now, 9, TZ)


# --- Fechas ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Relativa
        ("en 10 minutos", NOW + timedelta(minutes=10)),
        ("dentro de dos horas", NOW + timedelta(hours=2)),
        ("en media hora", NOW + timedelta(minutes=30)),
        ("en 3 días", NOW + timedelta(days=3)),
        ("en una hora y media", NOW + timedelta(minutes=90)),
        ("en un cuarto de hora", NOW + timedelta(minutes=15)),
        # Día y hora
        ("hoy a las 18", at(2, 18)),
        ("mañana a las 9 y media", at(3, 9, 30)),
        ("mañana a las nueve", at(3, 9)),
        ("Mañana a las 10 menos cuarto", at(3, 9, 45)),
        ("pasado mañana a las 10 y cuarto", at(4, 10, 15)),
        ("esta tarde a las 5", at(2, 17)),
        ("esta noche a las 10", at(2, 22)),
        ("mañana a las 7 de la tarde", at(3, 19)),
        ("mañana a las 3", at(3, 3)),  # la tarde solo se supone hoy
        ("hoy a las 3", at(2, 15)),  # las 3 de la mañana ya han pasado
        ("mañana", at(3, 9)),
        ("hoy a las 19:05", at(2, 19, 5)),
        ("mañana a las 9 en punto", at(3, 9)),
        ("mañana a las 9 y 20", at(3, 9, 20)),
        # Día de la semana
        ("el viernes", at(6, 9)),
        ("el miércoles a las 12", at(4, 12)),
        ("el lunes a las 10", at(9, 10)),  # hoy es lunes: la semana siguiente
        ("el sábado a las doce", at(7, 12)),
        # Fecha
        ("el 5 de diciembre a las 12", at(5, 12, month=12)),
        ("el 5 de diciembre de 2027", at(5, 9, month=12, year=2027)),
        ("el día 20 a las 8", at(20, 8)),
        ("el día 1", at(1, 9, month=4)),  # el 1 de este mes ya ha pasado
        ("el 1 de enero", at(1, 9, month=1, year=2027)),
        ("el día treinta y uno", at(31, 9)),
        # Solo hora
        ("a las 7", at(2, 19)),
        ("a las 19 30", at(2, 19, 30)),
        ("a las 9:30", at(3, 9, 30)),  # ya ha pasado: mañana
        ("a las 8", at(3, 8)),
        ("a las 11", at(2, 11)),
        ("a las 7 de la tarde", at(2, 19)),
        ("a la una", at(2, 13)),
        ("a las 10 de la noche", at(2, 22)),
        ("a las 6 de la mañana", at(3, 6)),
    ],
)
def test_gramatica_de_fechas(text, expected):
    assert parse(text) == expected


@pytest.mark.parametrize(
    "text",
    ["a las 25", "a las 9 y 75", "el 31 de febrero", "patata", "el 5", "esta tarde", "a las",
     "en", "en patata", "mañana a las", "el día 40", "el lunes 10", "hoy a las nueve kilos", ""],
)  # fmt: skip
def test_lo_que_no_es_una_fecha(text):
    assert parse(text) is None


def test_sin_zona_se_usa_la_del_sistema():
    found = datetimes.parse(["mañana"], NOW)
    assert found is not None and found.tzinfo is not None
    assert (found.hour, found.minute) == (9, 0)


def test_la_hora_por_defecto_se_configura():
    assert datetimes.parse(["mañana"], NOW, 8, TZ) == at(3, 8)


@pytest.mark.parametrize(
    ("text", "start", "expected"),
    [
        ("llamar a ana mañana a las 9", 3, at(3, 9)),
        ("llamar a ana a las 9", 3, at(3, 9)),
        ("mañana a las 9", 0, at(3, 9)),
        ("ver el partido el viernes", 3, at(6, 9)),
        ("regar las plantas a las 7 de la tarde", 3, at(2, 19)),
        ("sacar la basura en media hora", 3, NOW + timedelta(minutes=30)),
    ],
)
def test_la_fecha_mas_larga_al_final_del_texto(text, start, expected):
    assert datetimes.find_suffix(normalize(text).split(), NOW, 9, TZ) == (start, expected)


@pytest.mark.parametrize("text", ["comprar pan", "llamar a ana el 5", ""])
def test_un_texto_sin_fecha_al_final(text):
    assert datetimes.find_suffix(normalize(text).split(), NOW, 9, TZ) is None


# --- Duraciones ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("10 minutos", 10), ("un minuto", 1), ("dos horas", 120), ("media hora", 30),
        ("un cuarto de hora", 15), ("cuarto de hora", 15), ("una hora y media", 90),
        ("dos horas y media", 150), ("dos horas y diez minutos", 130),
        ("treinta y cinco minutos", 35), ("3 días", 3 * 24 * 60), ("Una Hora", 60),
    ],
)  # fmt: skip
def test_duraciones(text, minutes):
    assert durations.parse(normalize(text)) == timedelta(minutes=minutes)


def test_segundos():
    assert durations.parse("45 segundos") == timedelta(seconds=45)


@pytest.mark.parametrize("text", ["patata", "minutos", "cero minutos", "cinco kilos", "", "y"])
def test_lo_que_no_es_una_duracion(text):
    assert durations.parse(normalize(text)) is None


# --- Forma hablada ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("when", "said"),
    [
        (at(2, 18), "hoy a las 6 de la tarde"),
        (at(3, 9), "mañana a las 9"),
        (at(4, 10, 15), "pasado mañana a las 10 y cuarto"),
        (at(6, 13, 30), "el viernes a la 1 y media de la tarde"),
        (at(5, 12, month=12), "el 5 de diciembre a las 12"),
        (at(1, 0, year=2027, month=1), "el 1 de enero de 2027 a las 12 de la noche"),
        (at(1, 9), "ayer a las 9"),
        (at(3, 5, 5), "mañana a las 5 y 5 de la madrugada"),
        (at(2, 22), "hoy a las 10 de la noche"),
        (datetime(2026, 3, 3, 8, 0, tzinfo=UTC), "mañana a las 9"),  # en hora local
    ],
)
def test_fechas_dichas(when, said):
    assert formats.moment(when, NOW, TZ) == said


@pytest.mark.parametrize(
    ("delta", "said"),
    [
        (timedelta(minutes=10), "10 minutos"),
        (timedelta(minutes=1), "un minuto"),
        (timedelta(minutes=30), "media hora"),
        (timedelta(minutes=15), "un cuarto de hora"),
        (timedelta(minutes=90), "una hora y media"),
        (timedelta(minutes=150), "2 horas y media"),
        (timedelta(hours=2, minutes=5), "2 horas y 5 minutos"),
        (timedelta(days=1, hours=2), "un día y 2 horas"),
        (timedelta(days=1, hours=1, minutes=1), "un día, una hora y un minuto"),
        (timedelta(seconds=45), "45 segundos"),
    ],
)
def test_duraciones_dichas(delta, said):
    assert formats.duration(delta) == said
