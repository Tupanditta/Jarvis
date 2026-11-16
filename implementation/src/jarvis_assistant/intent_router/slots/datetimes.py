"""Fechas y horas escritas: gramática cerrada (enrutador-intenciones.md, sección 5).

Analizador por palabras, sin expresiones regulares de lenguaje natural (RES-25). Trabaja sobre
palabras normalizadas (minúsculas, sin tildes). Formas admitidas:

- Relativa: «en 10 minutos», «dentro de dos horas», «en media hora».
- Día y hora: «hoy a las 18», «mañana a las 9 y media», «pasado mañana a las 10 y cuarto»,
  «esta tarde a las 5», «esta noche a las 10».
- Día de la semana: «el lunes a las 10», «el viernes» (la próxima aparición; si es hoy, la
  semana siguiente).
- Fecha: «el 5 de diciembre a las 12», «el 5 de diciembre de 2027», «el día 20 a las 8» (este
  mes o, si ya ha pasado, el siguiente).
- Solo hora: «a las 7», «a las 19 30», «a las 7 de la tarde» (hoy si aún no ha pasado; si no,
  mañana).

Sin hora, las `default_hour`:00. El resultado lleva la zona horaria local; no se comprueba
aquí que sea futuro.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from jarvis_assistant.intent_router.slots import durations, numbers

WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5,
    "domingo": 6,
}  # fmt: skip

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}  # fmt: skip

# «de la …» tras la hora: fija mañana o tarde.
_PERIODS = {"mañana": "mañana", "madrugada": "mañana", "tarde": "tarde", "noche": "noche"}

# «esta tarde a las 5»: el día es hoy y la hora, de la tarde.
_THIS = {"mañana": "mañana", "tarde": "tarde", "noche": "noche"}

_AFTERNOON_FROM, _AFTERNOON_TO = 1, 7  # horas que, sin indicación, pueden ser de la tarde


@dataclass(frozen=True)
class _Day:
    """Día de la expresión, sin hora."""

    day: date
    period: str | None = None  # «esta tarde»
    needs_time: bool = False  # «esta tarde» sin hora no es una fecha


@dataclass(frozen=True)
class _Time:
    hour: int
    minute: int
    period: str | None


def parse(
    words: Sequence[str], now: datetime, default_hour: int = 9, tz: tzinfo | None = None
) -> datetime | None:
    """La fecha que dicen todas las palabras, o None si no es una fecha de la gramática.

    `now`: el momento actual, con zona horaria. `tz`: zona horaria local; None, la del sistema.
    """
    words = tuple(words)
    if not words:
        return None
    local_now = now.astimezone(tz)
    relative = _relative(words)
    if relative is not None:
        return now + relative
    if words[0] == "a":  # solo hora
        moment = _time(words)
        if moment is None:
            return None
        return _only_time(moment, local_now, tz)
    for size in range(len(words), 0, -1):  # el día más largo que encaje
        day = _day(words[:size], local_now)
        if day is None:
            continue
        rest = words[size:]
        if not rest:
            if day.needs_time:
                return None
            return _localize(datetime.combine(day.day, time(default_hour)), tz)
        moment = _time(rest)
        if moment is None:
            return None
        return _on_day(day, moment, local_now, tz)
    return None


def find_suffix(
    words: Sequence[str], now: datetime, default_hour: int = 9, tz: tzinfo | None = None
) -> tuple[int, datetime] | None:
    """La expresión de fecha más larga al final de `words`: su primera palabra y la fecha.

    «llamar a ana mañana a las 9» → (3, mañana a las 9:00). None si el texto no acaba en una
    fecha.
    """
    words = tuple(words)
    for start in range(len(words)):
        found = parse(words[start:], now, default_hour, tz)
        if found is not None:
            return start, found
    return None


# --- Partes ----------------------------------------------------------------------------------


def _relative(words: tuple[str, ...]) -> timedelta | None:
    if words[0] == "en":
        return durations.parse_words(words[1:])
    if words[:2] == ("dentro", "de"):
        return durations.parse_words(words[2:])
    return None


def _day(words: tuple[str, ...], now: datetime) -> _Day | None:
    today = now.date()
    match words:
        case ("hoy",):
            return _Day(today)
        case ("mañana",):
            return _Day(today + timedelta(days=1))
        case ("pasado", "mañana"):
            return _Day(today + timedelta(days=2))
        case ("esta", part) if part in _THIS:
            return _Day(today, _THIS[part], needs_time=True)
        case ("el", weekday) if weekday in WEEKDAYS:
            ahead = (WEEKDAYS[weekday] - today.weekday()) % 7 or 7
            return _Day(today + timedelta(days=ahead))
    if not words or words[0] != "el":
        return None
    return _calendar_day(words[1:], today)


def _calendar_day(words: tuple[str, ...], today: date) -> _Day | None:
    """«día 20», «5 de diciembre», «día 5 de diciembre de 2027» (sin el «el»)."""
    explicit_day = bool(words) and words[0] == "dia"
    if explicit_day:
        words = words[1:]
    number = _number(words)
    if number is None:
        return None
    day_of_month, used = number
    rest = words[used:]
    if not rest:
        if not explicit_day:
            return None  # «el 5» a secas no es una fecha
        return _next_day_of_month(day_of_month, today)
    if len(rest) < 2 or rest[0] != "de" or rest[1] not in MONTHS:
        return None
    month = MONTHS[rest[1]]
    rest = rest[2:]
    if not rest:
        found = _safe_date(today.year, month, day_of_month)
        if found is not None and found < today:
            found = _safe_date(today.year + 1, month, day_of_month)
        return None if found is None else _Day(found)
    if len(rest) == 2 and rest[0] == "de" and rest[1].isascii() and rest[1].isdigit():
        found = _safe_date(int(rest[1]), month, day_of_month)
        return None if found is None else _Day(found)
    return None


def _next_day_of_month(day_of_month: int, today: date) -> _Day | None:
    """El día `day_of_month` de este mes o, si ya ha pasado, del siguiente."""
    found = _safe_date(today.year, today.month, day_of_month)
    if found is not None and found >= today:
        return _Day(found)
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    found = _safe_date(year, month, day_of_month)
    return None if found is None else _Day(found)


def _time(words: tuple[str, ...]) -> _Time | None:
    """«a las 9», «a la una», «a las 9 y media», «a las 19 30», «a las 7 de la tarde»."""
    if len(words) < 3 or words[0] != "a" or words[1] not in ("la", "las"):
        return None
    rest = words[2:]
    period = None
    if len(rest) >= 4 and rest[-3:-1] == ("de", "la") and rest[-1] in _PERIODS:
        period = _PERIODS[rest[-1]]
        rest = rest[:-3]
    if not rest:
        return None
    reading = _clock_reading(rest[0])
    if reading is not None:  # «9:30»: la hora y los minutos en una palabra
        if len(rest) > 1:
            return None
        hour, minute = reading
    else:
        number = _number(rest)
        if number is None:
            return None
        hour, used = number
        minute = 0
        if rest[used:]:
            minutes = _minutes(rest[used:])
            if minutes is None:
                return None
            minute, hour = minutes[0], hour + minutes[1]
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return _Time(hour, minute, period)


def _clock_reading(word: str) -> tuple[int, int] | None:
    """«9:30» o «19:05» en una sola palabra."""
    head, sep, tail = word.partition(":")
    if not sep or not (head.isascii() and head.isdigit() and tail.isascii() and tail.isdigit()):
        return None
    return int(head), int(tail)


def _minutes(words: tuple[str, ...]) -> tuple[int, int] | None:
    """Minutos tras la hora y cuánto cambia la hora («menos cuarto» resta una)."""
    match words:
        case ("y", "media"):
            return 30, 0
        case ("y", "cuarto"):
            return 15, 0
        case ("menos", "cuarto"):
            return 45, -1
        case ("en", "punto"):
            return 0, 0
    if words[0] == "y":
        words = words[1:]
    number = _number(words)
    if number is None or number[1] != len(words) or not 0 <= number[0] <= 59:
        return None
    return number[0], 0


def _number(words: tuple[str, ...]) -> tuple[int, int] | None:
    """El número al principio de `words` y cuántas palabras ocupa («treinta y uno»: tres)."""
    for size in (3, 1):
        if len(words) >= size:
            value = numbers.parse(" ".join(words[:size]))
            if value is not None and words[0] not in ("el", "la", "numero"):
                return value, size
    return None


# --- Resolución ------------------------------------------------------------------------------


def _hour_of(moment: _Time, period: str | None) -> int:
    hour = moment.hour
    if period in ("tarde", "noche") and hour < 12:
        hour += 12
    return hour


def _only_time(moment: _Time, now: datetime, tz: tzinfo | None) -> datetime | None:
    """Hoy si aún no ha pasado; si no, mañana. Sin indicación, una hora de 1 a 7 ya pasada
    por la mañana es de la tarde."""
    today = now.date()
    hour = _hour_of(moment, moment.period)
    candidate = _localize(datetime.combine(today, time(hour, moment.minute)), tz)
    if candidate <= now and moment.period is None and _AFTERNOON_FROM <= hour <= _AFTERNOON_TO:
        candidate = _localize(datetime.combine(today, time(hour + 12, moment.minute)), tz)
    if candidate <= now:
        tomorrow = today + timedelta(days=1)
        candidate = _localize(datetime.combine(tomorrow, time(hour, moment.minute)), tz)
    return candidate


def _on_day(day: _Day, moment: _Time, now: datetime, tz: tzinfo | None) -> datetime:
    period = moment.period or day.period
    hour = _hour_of(moment, period)
    candidate = _localize(datetime.combine(day.day, time(hour, moment.minute)), tz)
    if (
        period is None
        and day.day == now.date()
        and candidate <= now
        and _AFTERNOON_FROM <= hour <= _AFTERNOON_TO
    ):
        candidate = _localize(datetime.combine(day.day, time(hour + 12, moment.minute)), tz)
    return candidate


def _localize(naive: datetime, tz: tzinfo | None) -> datetime:
    """Hora local → fecha con zona horaria. Sin `tz`, la del sistema (con su horario de
    verano en esa fecha)."""
    return naive.astimezone() if tz is None else naive.replace(tzinfo=tz)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
