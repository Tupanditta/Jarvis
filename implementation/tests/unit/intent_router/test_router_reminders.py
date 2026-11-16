"""Juego de frases de prueba de Recordatorio (catalogo-intenciones.md, secciones 3, 4 y 6) y
las entidades `DURATION` y `DATETIME` en el enrutador, con reloj fijo.

Ahora es el lunes 2 de marzo de 2026 a las 10:00, hora local UTC+1.
"""
from datetime import datetime, timedelta, timezone

import pytest

from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.action_api import ExpectedType, Phrase, ReminderAction
from jarvis_assistant.core.state_machine import (
    Answer,
    AssistantState,
    Control,
    ControlKind,
    DialogueContext,
    IntentMatched,
)
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router.router import IntentRouter
from jarvis_assistant.main import ACTION_MODULES

S = AssistantState
TZ = timezone(timedelta(hours=1))
NOW = datetime(2026, 3, 2, 10, 0, tzinfo=TZ)


def at(day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(2026, 3, day, hour, minute, tzinfo=TZ)


@pytest.fixture
def router(tmp_path):
    router = IntentRouter(
        RouterSettings(), workdir=Workdir(tmp_path), now=lambda: NOW, local_tz=TZ
    )
    for create in ACTION_MODULES:
        router.register(create())
    return router


def intent_of(router, text):
    entry = router.route(text, S.LISTENING_COMMAND)
    assert isinstance(entry, IntentMatched), f"«{text}» → {entry!r}"
    return entry.intent


@pytest.mark.parametrize(
    ("text", "key", "params"),
    [
        # Crear: el patrón separa el prefijo; la fecha la separa el módulo.
        ("recuérdame comprar pan", "recordatorio.crear", {"texto": "comprar pan"}),
        ("recuérdame que llame a Ana", "recordatorio.crear", {"texto": "llame a Ana"}),
        ("Recuérdame que tengo que llamar a Ana mañana a las nueve", "recordatorio.crear",
         {"texto": "tengo que llamar a Ana mañana a las nueve"}),
        ("recuerdame regar las plantas", "recordatorio.crear", {"texto": "regar las plantas"}),
        ("crea un recordatorio regar", "recordatorio.crear", {"texto": "regar"}),
        ("crea un recordatorio para regar", "recordatorio.crear", {"texto": "regar"}),
        # Mostrar
        ("recordatorios", "recordatorio.mostrar", {}),
        ("muestra los recordatorios", "recordatorio.mostrar", {}),
        ("¿Qué recordatorios tengo?", "recordatorio.mostrar", {}),
        # Leer
        ("lee el recordatorio uno", "recordatorio.leer", {"n": 1}),
        ("recordatorio 2", "recordatorio.leer", {"n": 2}),
        ("lee el tercero", "recordatorio.leer", {"n": 3}),
        # Confirmar
        ("confirmar recordatorios dos", "recordatorio.confirmar", {"n": 2}),
        ("confirmar recordatorio 1", "recordatorio.confirmar", {"n": 1}),
        ("confirmar recordatorios", "recordatorio.confirmar", {}),
        # Posponer
        ("posponer", "recordatorio.posponer", {}),
        ("pospón", "recordatorio.posponer", {}),
        ("más tarde", "recordatorio.posponer", {}),
        ("posponer media hora", "recordatorio.posponer", {"duracion": timedelta(minutes=30)}),
        ("pospón diez minutos", "recordatorio.posponer", {"duracion": timedelta(minutes=10)}),
        ("pospón el recordatorio 2", "recordatorio.posponer", {"n": 2}),
        ("pospón el recordatorio dos durante una hora", "recordatorio.posponer",
         {"n": 2, "duracion": timedelta(hours=1)}),
        # Posponer la fecha límite
        ("pospón la fecha límite del recordatorio uno hasta el viernes a las diez",
         "recordatorio.posponer_limite", {"n": 1, "fecha": at(6, 10)}),
        ("cambia la fecha límite del recordatorio 2 hasta mañana",
         "recordatorio.posponer_limite", {"n": 2, "fecha": at(3, 9)}),
        # Eliminar
        ("elimina el recordatorio tres", "recordatorio.eliminar", {"n": 3}),
        ("borra el recordatorio 1", "recordatorio.eliminar", {"n": 1}),
    ],
)  # fmt: skip
def test_frases_de_recordatorio(router, text, key, params):
    intent = intent_of(router, text)
    assert (intent.key, dict(intent.params), intent.error) == (key, params, None)


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("posponer cinco kilos", Phrase("entidad.duracion")),
        ("pospón la fecha límite del recordatorio 1 hasta patata", Phrase("entidad.fecha")),
        ("pospón la fecha límite del recordatorio 1 hasta hoy a las 8",
         Phrase("entidad.fecha_pasada")),
        ("lee el recordatorio patata", Phrase("entidad.numero")),
    ],
)  # fmt: skip
def test_entidades_que_no_se_resuelven(router, text, error):
    assert intent_of(router, text).error == error


def test_la_fecha_se_resuelve_con_el_reloj_del_nucleo(tmp_path):
    moments = [NOW]
    router = IntentRouter(
        RouterSettings(), workdir=Workdir(tmp_path), now=lambda: moments[-1], local_tz=TZ
    )
    for create in ACTION_MODULES:
        router.register(create())
    text = "pospón la fecha límite del recordatorio 1 hasta hoy a las 11"
    assert intent_of(router, text).params["fecha"] == at(2, 11)
    moments.append(at(2, 12))
    assert intent_of(router, text).error == Phrase("entidad.fecha_pasada")


# --- Respuestas -------------------------------------------------------------------------------


def dialogue(expected: ExpectedType) -> DialogueContext:
    return DialogueContext(Phrase("recordatorio.cuando"), expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("mañana a las nueve", at(3, 9)), ("en dos horas", NOW + timedelta(hours=2)),
     ("Hoy a las 8.", at(2, 8))],  # una fecha pasada se acepta: el módulo dice por qué no vale
)  # fmt: skip
def test_respuesta_de_fecha(router, text, expected):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.DATETIME))
    assert entry == Answer(expected)


@pytest.mark.parametrize("text", ["patata", "abre GitHub", "el 5"])
def test_respuesta_que_no_es_una_fecha(router, text):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.DATETIME))
    assert entry == Answer(valid=False)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("no", False), ("No.", False), ("nada más", False), ("listo", False),
        ("ya está", False),
        ("otro aviso el viernes a las diez", ReminderAction("aviso", at(6, 10))),
        ("Otro aviso mañana", ReminderAction("aviso", at(3, 9))),
        ("fecha límite el sábado a las doce", ReminderAction("limite", at(7, 12))),
        ("fecha limite en 3 días", ReminderAction("limite", NOW + timedelta(days=3))),
    ],
)  # fmt: skip
def test_respuesta_de_mas_avisos(router, text, value):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.REMINDER_ACTION))
    assert entry == Answer(value)


@pytest.mark.parametrize(
    "text", ["otro aviso", "fecha límite patata", "sí", "el viernes", "abre GitHub"]
)
def test_respuesta_de_mas_avisos_no_valida(router, text):
    entry = router.route(text, S.AWAITING_PARAMETER, dialogue(ExpectedType.REMINDER_ACTION))
    assert entry == Answer(valid=False)


def test_cancelar_sigue_siendo_una_frase_de_control(router):
    entry = router.route("cancelar", S.AWAITING_PARAMETER, dialogue(ExpectedType.REMINDER_ACTION))
    assert entry == Control(ControlKind.CANCELAR)
