"""Vocabulario, filtro y transcriptor con un modelo falso (transcriptor.md)."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import numpy as np
import pytest

from jarvis_assistant.config import SttSettings
from jarvis_assistant.transcriber.filters import echoes_vocabulary, filter_transcript, is_spurious
from jarvis_assistant.transcriber.vocabulary import (
    FIXED_TERMS,
    build_terms,
    render_prompt,
    workdir_entries,
)
from jarvis_assistant.transcriber.whisper_transcriber import WhisperTranscriber, default_threads

# --- Vocabulario -----------------------------------------------------------------------------


def test_orden_de_prioridad_sin_repetidos_ni_vacios():
    terms = build_terms(
        dialogue=["sí", "no"],
        workdir=["src", "notas.txt"],
        protocols=["modo trabajo"],
        places=["escritorio"],
        catalog=["GitHub", "src"],
        binaries=["git", " "],
        discovered=["Paint", "github"],
    )
    assert terms == (
        *FIXED_TERMS, "sí", "no", "src", "notas.txt", "modo trabajo", "escritorio", "GitHub",
        "git", "Paint",
    )


def test_las_frases_fijas_van_siempre_primero():
    assert build_terms() == ("Jarvis", "Gracias Jarvis", "Buenas noches Jarvis")


def test_el_recorte_pierde_primero_lo_de_menor_prioridad():
    terms = ("Jarvis", "proyectos", "documentos", "descargas")
    assert render_prompt(terms, 600) == "Jarvis, proyectos, documentos, descargas"
    assert render_prompt(terms, 30) == "Jarvis, proyectos, documentos"
    assert render_prompt(terms, 29) == "Jarvis, proyectos, documentos"
    assert render_prompt(terms, 28) == "Jarvis, proyectos"
    assert render_prompt(terms, 3) == ""


def test_misma_entrada_mismo_texto():
    terms = build_terms(workdir=["b", "a"])
    assert render_prompt(terms, 600) == render_prompt(build_terms(workdir=["b", "a"]), 600)


def test_entradas_del_directorio_carpetas_primero_sin_ocultos_y_con_limite(tmp_path):
    for name in ("zeta", "Alfa", ".git"):
        (tmp_path / name).mkdir()
    for name in ("beta.txt", "Apuntes.md", ".env"):
        (tmp_path / name).write_text("")
    assert workdir_entries(tmp_path, 30) == ["Alfa", "zeta", "Apuntes.md", "beta.txt"]
    assert workdir_entries(tmp_path, 3) == ["Alfa", "zeta", "Apuntes.md"]
    assert workdir_entries(tmp_path / "no-existe", 30) == []


# --- Filtro ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Subtítulos realizados por la comunidad de Amara.org",
        "¡Gracias por ver el vídeo!",
        "Suscríbete al canal.",
    ],
)
def test_frases_espurias(text):
    assert is_spurious(text)
    assert filter_transcript(text) == ""


def test_eco_de_la_indicacion_de_vocabulario():
    terms = ("Jarvis", "Gracias Jarvis", "Buenas noches Jarvis", "proyectos", "documentos")
    assert echoes_vocabulary("Jarvis, Gracias Jarvis, Buenas noches Jarvis.", terms)
    assert echoes_vocabulary("eh buenas noches jarvis proyectos documentos", terms)
    assert not echoes_vocabulary("Buenas noches, Jarvis.", terms)
    assert not echoes_vocabulary("ve a proyectos", terms)
    assert not echoes_vocabulary("documentos proyectos jarvis", terms)
    assert filter_transcript("Jarvis, gracias Jarvis, buenas noches Jarvis", terms) == ""


def test_el_texto_normal_se_conserva_recortado():
    assert filter_transcript("  Gracias,   Jarvis. ", FIXED_TERMS) == "Gracias, Jarvis."
    assert filter_transcript("   ") == ""


# --- Transcriptor ----------------------------------------------------------------------------


class FakeWhisper:
    def __init__(self, segments):
        self.segments = segments
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        return iter(self.segments), None


def segment(text, no_speech=0.0):
    return SimpleNamespace(text=text, no_speech_prob=no_speech)


@pytest.fixture
def executor():
    pool = ThreadPoolExecutor(max_workers=1)
    yield pool
    pool.shutdown(wait=True)


def make(tmp_path, executor, segments, settings=None, created=None):
    model = FakeWhisper(segments)
    created = created if created is not None else []

    def factory(model_dir, threads):
        created.append((model_dir, threads))
        return model

    transcriber = WhisperTranscriber(
        tmp_path, settings or SttSettings(cpu_threads=2), model_factory=factory,
        executor=executor,
    )
    return transcriber, model, created


async def test_transcribe_en_espanol_con_los_parametros_de_la_especificacion(tmp_path, executor):
    transcriber, model, created = make(tmp_path, executor, [segment(" Gracias, Jarvis.")])
    transcriber.set_vocabulary(["Jarvis", "proyectos"])
    pcm = np.full(16000, 16384, dtype=np.int16)
    assert await transcriber.transcribe(pcm) == "Gracias, Jarvis."
    assert created == [(str(tmp_path / "faster-whisper-small"), 2)]
    audio, kwargs = model.calls[0]
    assert audio.dtype == np.float32 and audio[0] == pytest.approx(0.5)
    assert kwargs == {
        "language": "es", "beam_size": 3, "condition_on_previous_text": False,
        "vad_filter": False, "temperature": 0, "initial_prompt": "Jarvis, proyectos",
    }


async def test_los_segmentos_restringidos_usan_busqueda_voraz(tmp_path, executor):
    transcriber, model, _ = make(tmp_path, executor, [segment("Buenas noches, Jarvis.")])
    await transcriber.transcribe(np.zeros(8000, dtype=np.int16), restricted=True)
    assert model.calls[0][1]["beam_size"] == 1
    assert model.calls[0][1]["initial_prompt"] is None


async def test_sin_voz_o_espurio_devuelve_texto_vacio(tmp_path, executor):
    transcriber, _, _ = make(tmp_path, executor, [segment("Hola", no_speech=0.7)])
    assert await transcriber.transcribe(np.zeros(8000, dtype=np.int16)) == ""
    transcriber, _, _ = make(tmp_path, executor, [segment("Gracias por ver el vídeo.")])
    assert await transcriber.transcribe(np.zeros(8000, dtype=np.int16)) == ""


async def test_la_carga_es_unica_y_la_orden_espera_a_que_termine(tmp_path, executor):
    transcriber, _, created = make(tmp_path, executor, [segment("lista")])
    assert not transcriber.loaded
    await transcriber.load()
    await transcriber.load()
    assert transcriber.loaded and len(created) == 1
    transcriber.unload()
    assert not transcriber.loaded
    assert await transcriber.transcribe(np.zeros(8000, dtype=np.int16)) == "lista"
    assert len(created) == 2


async def test_el_texto_solo_se_registra_en_debug(tmp_path, executor, caplog):
    import logging

    caplog.set_level(logging.INFO)
    transcriber, _, _ = make(tmp_path, executor, [segment("texto secreto")])
    await transcriber.transcribe(np.zeros(8000, dtype=np.int16))
    assert "texto secreto" not in caplog.text
    assert "Transcripción de" in caplog.text


def test_hilos_por_defecto():
    assert [default_threads(n) for n in (None, 1, 2, 4, 8, 16)] == [1, 1, 1, 3, 4, 4]
