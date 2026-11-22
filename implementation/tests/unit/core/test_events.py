"""Catálogo de eventos del ciclo de vida y de estado (T-0.6, bus-eventos.md)."""
import dataclasses
import inspect

import pytest

from jarvis_assistant.core import events
from jarvis_assistant.core.events import (
    Activity,
    AssistantActivityChanged,
    AudioLevel,
    CommandReceived,
    Event,
    ListeningResumed,
    RestEntered,
    SessionClosed,
    SessionOpened,
    TextSubmitted,
    UserTyping,
)

EVENT_CLASSES = [
    cls
    for _, cls in inspect.getmembers(events, inspect.isclass)
    if issubclass(cls, Event) and cls is not Event
]


def test_el_catalogo_tiene_los_eventos_del_ciclo_de_vida_y_de_estado():
    assert {cls.__name__ for cls in EVENT_CLASSES} >= {
        "SessionOpened", "ListeningResumed", "RestEntered", "SessionClosed",
        "AssistantActivityChanged", "AudioLevel", "CommandReceived", "TextSubmitted",
        "UserTyping",
    }  # fmt: skip


@pytest.mark.parametrize("cls", EVENT_CLASSES, ids=lambda cls: cls.__name__)
def test_todos_los_eventos_son_dataclasses_inmutables(cls):
    assert dataclasses.is_dataclass(cls)
    assert cls.__dataclass_params__.frozen


def test_todas_las_dataclasses_del_modulo_son_eventos():
    for _, cls in inspect.getmembers(events, inspect.isclass):
        if cls.__module__ == events.__name__ and dataclasses.is_dataclass(cls):
            assert issubclass(cls, Event), cls.__name__


def test_campos_de_los_eventos():
    def names(cls):
        return [f.name for f in dataclasses.fields(cls)]

    assert names(SessionOpened) == ["session_id", "name", "profile_id"]
    assert names(ListeningResumed) == ["silent"]
    assert names(RestEntered) == []
    assert names(SessionClosed) == []
    assert names(AssistantActivityChanged) == ["state", "activity"]
    assert names(CommandReceived) == ["text", "recognized"]
    assert names(TextSubmitted) == ["text"]
    assert names(UserTyping) == []
    assert names(AudioLevel) == ["level", "source"]


def test_un_evento_no_se_puede_modificar():
    event = SessionOpened(session_id=3, name="14 de noviembre")
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.name = "otro"


def test_listening_resumed_no_es_silencioso_por_defecto():
    assert ListeningResumed().silent is False


def test_las_actividades_son_las_seis_de_la_especificacion():
    assert [activity.value for activity in Activity] == [
        "dormido", "reposo", "escuchando", "procesando", "hablando", "esperando",
    ]  # fmt: skip


@pytest.mark.parametrize("level", [-0.1, 1.1])
def test_el_nivel_de_audio_esta_entre_0_y_1(level):
    with pytest.raises(ValueError):
        AudioLevel(level=level, source="assistant")


def test_el_origen_del_nivel_de_audio_es_assistant_o_none():
    for source in ("assistant", "none"):
        AudioLevel(level=0.5, source=source)
    for source in ("mic", "altavoz"):
        with pytest.raises(ValueError):
            AudioLevel(level=0.5, source=source)


def test_no_quedan_eventos_de_la_entrada_por_voz():
    assert not hasattr(events, "MicStatusChanged")
    assert not hasattr(events, "TranscriptReady")


def test_eventos_de_dialogo_tareas_y_panel():
    from datetime import datetime

    def names(cls):
        return [f.name for f in dataclasses.fields(cls)]

    assert names(events.DialogueOpened) == [
        "question", "expected_type", "hints", "timeout_seconds", "subject",
    ]
    assert names(events.DialogueClosed) == ["outcome"]
    assert names(events.TaskUpdated) == [
        "task_id", "parent_id", "module", "description", "status", "detail", "at",
    ]
    assert names(events.PanelActivated) == ["panel"]
    with pytest.raises(ValueError):  # solo pendiente, error y completado
        events.TaskUpdated(1, None, "comandos", "ls", "en curso", None, datetime(2026, 11, 14))
