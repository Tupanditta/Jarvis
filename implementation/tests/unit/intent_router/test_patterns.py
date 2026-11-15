"""Compilación y coincidencia de patrones (enrutador-intenciones.md, sección 3)."""
import pytest

from jarvis_assistant.intent_router.patterns import (
    PatternError,
    compile_pattern,
    match,
    similarity,
)


def words(text: str) -> list[str]:
    return text.split()


def test_un_patron_alterna_texto_fijo_y_huecos():
    pattern = compile_pattern("Crea el archivo {nombre} en {ruta}")
    assert pattern.parts == (("crea", "el", "archivo"), "nombre", ("en",), "ruta")
    assert pattern.holes == ("nombre", "ruta")
    assert pattern.fixed_words == 4
    assert pattern.key == "crea el archivo {} en {}"


def test_el_texto_fijo_se_normaliza():
    assert compile_pattern("¿Dónde estoy?").parts == (("donde", "estoy"),)


@pytest.mark.parametrize(
    "source",
    ["{ruta} primero", "abre {a} {b}", "", "abre {a} y {a}", "abre {ruta", "abre {dos palabras}"],
)
def test_reglas_de_escritura(source):
    with pytest.raises(PatternError):
        compile_pattern(source)


def test_patron_sin_huecos_compara_la_frase_completa():
    pattern = compile_pattern("dónde estoy")
    assert match(pattern, words("donde estoy"), 80).score == 100
    assert match(pattern, words("donde estoi"), 80) is not None  # una errata
    assert match(pattern, words("donde estoy ahora mismo"), 80) is None


def test_un_segmento_de_tres_caracteres_o_menos_exige_coincidencia_exacta():
    assert similarity(("cd",), ("cd",)) == 100
    assert similarity(("cd",), ("ce",)) == 0
    pattern = compile_pattern("cd {ruta}")
    assert match(pattern, words("cd proyectos"), 80).spans == {"ruta": (1, 2)}
    assert match(pattern, words("ce proyectos"), 80) is None


def test_el_hueco_recibe_las_palabras_que_quedan():
    pattern = compile_pattern("abre la carpeta {ruta}")
    found = match(pattern, words("abre la carpeta proyectos barra jarvis"), 80)
    assert found.spans == {"ruta": (3, 6)}
    assert found.score == 100


def test_una_errata_en_el_texto_fijo_baja_la_puntuacion_sin_perder_la_orden():
    found = match(compile_pattern("abre la carpeta {ruta}"), words("avre la carpeta descargas"), 80)
    assert found is not None and 80 <= found.score < 100


def test_el_contenido_del_hueco_no_influye_en_la_puntuacion():
    pattern = compile_pattern("abre {objetivo}")
    assert match(pattern, words("abre visual studio code"), 80).score == 100


def test_un_hueco_vacio_no_coincide():
    assert match(compile_pattern("abre {objetivo}"), words("abre"), 80) is None
    assert match(compile_pattern("crea {a} en {b}"), words("crea en casa"), 80) is None
    assert match(compile_pattern("crea {a} en {b}"), words("crea notas en"), 80) is None


def test_con_la_palabra_separadora_repetida_gana_la_ultima_aparicion():
    pattern = compile_pattern("crea el archivo {nombre} en {ruta}")
    found = match(pattern, words("crea el archivo notas en casa en documentos"), 80)
    assert found.spans == {"nombre": (3, 6), "ruta": (7, 8)}


def test_varios_separadores():
    pattern = compile_pattern("crea la estructura {estructura} llamada {nombre} en {ruta}")
    found = match(
        pattern, words("crea la estructura proyecto python llamada analizador en documentos"), 80
    )
    assert found.spans == {"estructura": (3, 5), "nombre": (6, 7), "ruta": (8, 9)}


def test_la_puntuacion_es_la_menor_similitud_de_los_segmentos_fijos():
    pattern = compile_pattern("pospón el recordatorio {n} durante {duracion}")
    exact = match(pattern, words("pospon el recordatorio dos durante una hora"), 80)
    typo = match(pattern, words("pospon el recordatorio dos durate una hora"), 80)
    assert exact.score == 100
    assert typo.score < 100 and typo.spans == exact.spans


def test_un_patron_que_termina_en_texto_fijo_debe_cerrar_la_frase():
    pattern = compile_pattern("pon {cosa} delante")
    assert match(pattern, words("pon github delante"), 80).spans == {"cosa": (1, 2)}
    assert match(pattern, words("pon github delante ahora"), 80) is None


def test_texto_mas_corto_que_el_patron():
    assert match(compile_pattern("abre la carpeta {ruta}"), words("abre la"), 80) is None
