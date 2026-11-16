"""Fechas y duraciones dichas de forma natural (catalogo-intenciones.md, sección 5).

«mañana a las 9», «el viernes a las 6 y media de la tarde», «el 5 de diciembre a las 12»,
«media hora», «1 hora y 10 minutos». Las cifras las lee el sintetizador.
"""
from datetime import datetime, timedelta, tzinfo

WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
    "octubre", "noviembre", "diciembre",
)  # fmt: skip

_WEEK = 7


def moment(when: datetime, now: datetime, tz: tzinfo | None = None) -> str:
    """Día y hora de `when` respecto a `now`, en hora local (`tz`; None, la del sistema)."""
    local = when.astimezone(tz)
    return f"{day(when, now, tz)} {clock_time(local.hour, local.minute)}"


def day(when: datetime, now: datetime, tz: tzinfo | None = None) -> str:
    """«hoy», «ayer», «mañana», «pasado mañana», «el lunes» (esta semana) o «el 5 de
    diciembre»."""
    target = when.astimezone(tz).date()
    today = now.astimezone(tz).date()
    ahead = (target - today).days
    if ahead == 0:
        return "hoy"
    if ahead == -1:
        return "ayer"  # la fecha límite de un recordatorio vencido
    if ahead == 1:
        return "mañana"
    if ahead == 2:
        return "pasado mañana"
    if 2 < ahead < _WEEK:
        return f"el {WEEKDAYS[target.weekday()]}"
    text = f"el {target.day} de {MONTHS[target.month - 1]}"
    return text if target.year == today.year else f"{text} de {target.year}"


def clock_time(hour: int, minute: int) -> str:
    """«a las 9», «a la 1 y media de la tarde», «a las 12 de la noche»."""
    if hour == 0:
        shown, part = 12, " de la noche"
    elif hour <= 6:
        shown, part = hour, " de la madrugada"
    elif hour <= 12:
        shown, part = hour, ""
    elif hour <= 20:
        shown, part = hour - 12, " de la tarde"
    else:
        shown, part = hour - 12, " de la noche"
    article = "a la" if shown == 1 else "a las"
    return f"{article} {shown}{_minutes(minute)}{part}"


def _minutes(minute: int) -> str:
    if minute == 0:
        return ""
    if minute == 15:
        return " y cuarto"
    if minute == 30:
        return " y media"
    return f" y {minute}"


_UNITS = (
    (86400, "un día", "días"),
    (3600, "una hora", "horas"),
    (60, "un minuto", "minutos"),
    (1, "un segundo", "segundos"),
)


def duration(delta: timedelta) -> str:
    """«10 minutos», «media hora», «una hora y media», «2 horas y 5 minutos»."""
    seconds = max(0, round(delta.total_seconds()))
    if seconds == 1800:
        return "media hora"
    if seconds == 900:
        return "un cuarto de hora"
    if seconds >= 3600 and seconds % 3600 == 1800:
        hours = seconds // 3600
        return f"{_amount(hours, 'una hora', 'horas')} y media"
    parts = []
    for size, one, many in _UNITS:
        amount, seconds = divmod(seconds, size)
        if amount:
            parts.append(_amount(amount, one, many))
    if not parts:
        return "0 segundos"
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} y {parts[-1]}"


def _amount(amount: int, one: str, many: str) -> str:
    return one if amount == 1 else f"{amount} {many}"
