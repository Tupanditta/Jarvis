"""Normalización del texto transcrito (enrutador-intenciones.md, sección 2)."""
import pytest

from jarvis_assistant.intent_router.normalizer import normalize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Gracias, Jarvis.", "gracias jarvis"),
        ("¿Dónde estoy?", "donde estoy"),
        ("  Buenas   noches\tJarvis ", "buenas noches jarvis"),
        ("Olvídalo", "olvidalo"),
        ("pingüino", "pinguino"),
        ("Mañana por la mañana", "mañana por la mañana"),
        ("AÑO", "año"),
        ("", ""),
        ("¡¿...?!", ""),
    ],
)
def test_minusculas_tildes_signos_y_espacios(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("crea notas.txt", "crea notas.txt"),
        ("abre C:\\Users\\jane", "abre c:\\users\\jane"),
        ("ve a src/core", "ve a src/core"),
        ("archivo mi_nota-final", "archivo mi_nota-final"),
        ("notas.txt.", "notas.txt"),
        ("- lista -", "lista"),
    ],
)
def test_los_signos_de_ruta_se_conservan_solo_dentro_de_una_palabra(text, expected):
    assert normalize(text) == expected


def test_los_alias_sustituyen_palabras_y_secuencias():
    aliases = {"ce de": "cd", "guit": "git", "ele ese": "ls"}
    assert normalize("Ce de proyectos", aliases) == "cd proyectos"
    assert normalize("ejecuta guit status", aliases) == "ejecuta git status"
    assert normalize("ele ese", aliases) == "ls"


def test_un_alias_no_sustituye_parte_de_una_palabra():
    assert normalize("guitarra", {"guit": "git"}) == "guitarra"


def test_gana_el_alias_mas_largo():
    aliases = {"ce": "c", "ce de": "cd"}
    assert normalize("ce de aquí", aliases) == "cd aqui"


def test_las_claves_de_los_alias_se_normalizan():
    assert normalize("guión bajo", {"Guión Bajo": "_"}) == "_"
