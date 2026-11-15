"""Separador de órdenes `--` (`intent_router/batch.py`)."""
import pytest

from jarvis_assistant.intent_router.batch import split_orders


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("lista", ["lista"]),
        ("lista -- abre github", ["lista", "abre github"]),
        ("lista--abre github", ["lista", "abre github"]),
        ("lista-- abre github", ["lista", "abre github"]),
        ("  lista   --   abre github  ", ["lista", "abre github"]),
        ("lista -- -- abre github --", ["lista", "abre github"]),
        ("-- lista", ["lista"]),
        ("uno -- dos -- tres", ["uno", "dos", "tres"]),
        ("lista --- abre github", ["lista", "abre github"]),
        ("", []),
        ("   ", []),
        ("--", []),
    ],
)
def test_separa_las_ordenes_en_su_orden(text, expected):
    assert split_orders(text) == expected


@pytest.mark.parametrize(
    "text", ["ejecuta git log --oneline", "ejecuta pip install --upgrade pip", "ve a mi-carpeta"]
)
def test_una_opcion_de_un_programa_o_un_guion_simple_no_separan(text):
    assert split_orders(text) == [text]


def test_una_opcion_y_un_separador_en_el_mismo_mensaje():
    assert split_orders("ejecuta git log --oneline -- lista") == [
        "ejecuta git log --oneline", "lista",
    ]  # fmt: skip
