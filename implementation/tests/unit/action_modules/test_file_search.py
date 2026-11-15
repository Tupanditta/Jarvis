"""Módulo Búsqueda (busqueda.md) con `FakePlatform` y un sistema de archivos temporal."""
from pathlib import Path

import pytest

from fakes.context import ContextRig
from jarvis_assistant.action_modules.file_manager import (
    FileSearch,
    Found,
    limited_search,
    rank,
)
from jarvis_assistant.config import Config, SearchSettings, Settings
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.os_adapters.base import SearchKind, SearchOutcome


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path)
    yield rig
    rig.close()


@pytest.fixture
def module():
    return FileSearch()


def make(root: Path, *relative: str) -> list[Path]:
    paths = []
    for name in relative:
        path = root / name
        if name.endswith("/"):
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")
        paths.append(path)
    return paths


def results(rig):
    return rig.last(events.SearchResultsReady)


# --- Búsqueda indexada -----------------------------------------------------------------------


async def test_busqueda_indexada_filtra_por_tipo(rig, module):
    rig.platform.search_outcome = SearchOutcome((), 0)
    for kind_name, kind in (
        ("archivos", SearchKind.FILE), ("carpetas", SearchKind.FOLDER), ("ambos", SearchKind.ANY),
    ):  # fmt: skip
        await module.execute("buscar", {"consulta": "informe", "tipo": kind_name}, rig.ctx)
        assert rig.platform.calls[-1] == ("indexed_search", ("informe", kind, 50))
        assert results(rig).kind == kind_name


async def test_sin_resultados_es_una_tarea_completada(rig, module):
    rig.platform.search_outcome = SearchOutcome((), 0)
    result = await module.execute("buscar", {"consulta": "nada", "tipo": "ambos"}, rig.ctx)
    assert (result.status, result.speech) == (
        "completado", Phrase("busqueda.ninguno", {"consulta": "nada"}),
    )  # fmt: skip
    assert results(rig).results == () and not results(rig).limited
    assert rig.said == []


async def test_un_resultado_dice_su_nombre_y_su_carpeta(rig, module):
    (path,) = make(rig.home, "Facturas/enero.pdf")
    rig.platform.search_outcome = SearchOutcome((path,), 1)
    result = await module.execute("buscar", {"consulta": "enero", "tipo": "archivos"}, rig.ctx)
    assert result.speech == Phrase("busqueda.uno", {"nombre": "enero.pdf", "carpeta": "Facturas"})
    (shown,) = results(rig).results
    assert (shown.index, shown.name, shown.is_dir, shown.folder, shown.path) == (
        1, "enero.pdf", False, str(path.parent), str(path),
    )  # fmt: skip


async def test_varios_resultados_orden_de_presentacion_y_limite(rig, module):
    paths = make(
        rig.home,
        "a/muy/hondo/informe.txt", "informe/", "b/informe final.txt", "c/mi informe.txt",
        *[f"z/otro informe {index}.txt" for index in range(12)],
    )  # fmt: skip
    rig.platform.search_outcome = SearchOutcome(tuple(reversed(paths)), 40)
    result = await module.execute("buscar", {"consulta": "Informe", "tipo": "ambos"}, rig.ctx)
    shown = results(rig)
    assert [item.index for item in shown.results] == list(range(1, 11))  # los 10 primeros
    assert shown.total == 40
    names = [item.name for item in shown.results]
    # Nombre igual a la consulta (la ruta más corta antes), el que empieza por ella, el resto.
    assert names[:4] == ["informe", "informe.txt", "informe final.txt", "mi informe.txt"]
    assert shown.results[0].is_dir
    assert result.speech == Phrase(
        "busqueda.varios", {"n": 40, "nombre": "informe", "carpeta": rig.home.name}
    )


def test_orden_a_igualdad_la_ruta_mas_corta():
    found = [Found(Path("C:/a/b/c/notas.txt"), False), Found(Path("C:/a/notas.txt"), False)]
    assert [item.path for item in rank(found, "notas")] == [found[1].path, found[0].path]


async def test_el_numero_de_resultados_mostrados_es_configurable(tmp_path, module):
    config = Config(settings=Settings(search=SearchSettings(max_results=2)))
    rig = ContextRig(tmp_path, config=config)
    paths = make(rig.home, "a1.txt", "a2.txt", "a3.txt")
    rig.platform.search_outcome = SearchOutcome(tuple(paths), 3)
    await module.execute("buscar", {"consulta": "a", "tipo": "ambos"}, rig.ctx)
    assert len(results(rig).results) == 2 and results(rig).total == 3
    rig.close()


# --- Búsqueda limitada -----------------------------------------------------------------------


def search(roots, query, kind=SearchKind.ANY, **kwargs):
    kwargs.setdefault("monotonic", lambda: 0.0)
    return limited_search(roots, query, kind, **kwargs)


def test_limitada_coincide_el_nombre_que_contiene_la_consulta(tmp_path):
    make(tmp_path, "Prácticas de Redes/", "practicas.txt", "otra cosa.txt")
    found = search([tmp_path], "PRACTICAS")
    assert sorted(item.path.name for item in found) == ["Prácticas de Redes", "practicas.txt"]
    assert [item.path.name for item in search([tmp_path], "practicas", SearchKind.FILE)] == [
        "practicas.txt"
    ]
    assert [item.is_dir for item in search([tmp_path], "practicas", SearchKind.FOLDER)] == [True]


def test_limitada_baja_hasta_seis_niveles(tmp_path):
    make(tmp_path, "1/2/3/4/5/dato.txt", "1/2/3/4/5/6/dato hondo.txt")
    assert [item.path.name for item in search([tmp_path], "dato")] == ["dato.txt"]


def test_limitada_omite_carpetas_ocultas_y_de_dependencias(tmp_path):
    make(
        tmp_path, "src/modulo.py", "node_modules/pkg/modulo.js", ".git/modulo", ".venv/modulo.py",
        "__pycache__/modulo.pyc", ".oculta/modulo.txt",
    )  # fmt: skip
    assert [item.path.name for item in search([tmp_path], "modulo")] == ["modulo.py"]


def test_limitada_se_corta_a_los_50_resultados(tmp_path):
    make(tmp_path, *[f"nota {index}.txt" for index in range(60)])
    assert len(search([tmp_path], "nota")) == 50


def test_limitada_se_corta_por_tiempo(tmp_path):
    make(tmp_path, "a/nota a.txt", "b/nota b.txt", "nota raiz.txt")
    ticks = iter([0.0, 0.0, 6.0, 6.0, 6.0])  # inicio, primera carpeta y, después, pasado el plazo
    found = search([tmp_path], "nota", timeout=5.0, monotonic=lambda: next(ticks))
    assert [item.path.name for item in found] == ["nota raiz.txt"]


def test_limitada_no_repite_una_raiz_contenida_en_otra(tmp_path):
    make(tmp_path, "docs/nota.txt")
    assert len(search([tmp_path, tmp_path / "docs"], "nota")) == 1


def test_limitada_sin_consulta_o_con_una_raiz_ilegible(tmp_path):
    assert search([tmp_path], "   ") == []
    assert search([tmp_path / "no existe"], "nota") == []


async def test_sin_herramienta_indexada_la_busqueda_es_limitada(rig, module):
    make(rig.home, "apuntes/redes.txt")
    make(rig.places["documentos"], "redes/")
    first = await module.execute("buscar", {"consulta": "redes", "tipo": "ambos"}, rig.ctx)
    shown = results(rig)
    assert shown.limited and shown.total == 2
    assert sorted(item.name for item in shown.results) == ["redes", "redes.txt"]
    # El resumen, el aviso de búsqueda limitada y, la primera vez en la sesión, el consejo.
    assert [phrase.id for phrase in rig.said] == ["busqueda.varios", "busqueda.limitada"]
    assert first.speech == Phrase("busqueda.instalar")
    rig.said.clear()
    second = await module.execute("buscar", {"consulta": "redes", "tipo": "ambos"}, rig.ctx)
    assert [phrase.id for phrase in rig.said] == ["busqueda.varios"]
    assert second.speech == Phrase("busqueda.limitada")
    await module.on_session_closed(rig.ctx)
    third = await module.execute("buscar", {"consulta": "redes", "tipo": "ambos"}, rig.ctx)
    assert third.speech == Phrase("busqueda.instalar")  # sesión nueva: se vuelve a aconsejar


# --- Abrir un resultado (RN-50) --------------------------------------------------------------


@pytest.fixture
async def searched(rig, module):
    paths = make(rig.home, "docs/informe.txt", "docs/informes/")
    rig.platform.search_outcome = SearchOutcome(tuple(paths), 2)
    await module.execute("buscar", {"consulta": "informe", "tipo": "ambos"}, rig.ctx)
    rig.platform.calls.clear()
    return paths


async def test_abrir_un_archivo_con_su_aplicacion_y_una_carpeta_en_el_gestor(rig, module, searched):
    file_path, folder = searched
    opened = await module.execute("abrir_resultado", {"n": 1}, rig.ctx)
    assert opened.speech == Phrase("apertura.abriendo", {"nombre": "informe.txt"})
    await module.execute("abrir_resultado", {"n": 2}, rig.ctx)
    assert rig.platform.calls == [("open_with_default", (file_path,)), ("open_folder", (folder,))]


async def test_abrir_la_ubicacion_abre_la_carpeta_que_lo_contiene(rig, module, searched):
    result = await module.execute("abrir_ubicacion", {"n": 1}, rig.ctx)
    assert result.speech == Phrase("apertura.abriendo", {"nombre": "docs"})
    assert rig.platform.calls == [("open_folder", (searched[0].parent,))]


@pytest.mark.parametrize("n", [0, 3, 99])
async def test_indice_fuera_de_rango(rig, module, searched, n):
    for action in ("abrir_resultado", "abrir_ubicacion"):
        result = await module.execute(action, {"n": n}, rig.ctx)
        assert (result.status, result.speech) == (
            "error", Phrase("general.indice_invalido", {"n": n}),
        )  # fmt: skip
    assert rig.platform.calls == []


async def test_sin_busqueda_previa(rig, module):
    result = await module.execute("abrir_resultado", {"n": 1}, rig.ctx)
    assert result.speech == Phrase("general.indice_invalido", {"n": 1})


async def test_el_archivo_ya_no_existe(rig, module, searched):
    searched[0].unlink()
    result = await module.execute("abrir_resultado", {"n": 1}, rig.ctx)
    assert (result.status, result.speech) == ("error", Phrase("busqueda.no_existe"))
    assert rig.platform.calls == []


async def test_fallo_al_abrir(rig, module, searched):
    rig.platform.launch_error = OSError("sin aplicación")
    result = await module.execute("abrir_resultado", {"n": 1}, rig.ctx)
    assert result.speech == Phrase("apertura.fallo", {"nombre": "informe.txt"})


async def test_los_resultados_se_olvidan_al_cerrar_la_sesion(rig, module, searched):
    await module.on_session_closed(rig.ctx)
    result = await module.execute("abrir_resultado", {"n": 1}, rig.ctx)
    assert result.status == "error"


def test_solo_buscar_se_puede_usar_en_protocolos(module):
    usable = {spec.action for spec in module.intents() if spec.in_protocols}
    assert usable == {"buscar"}
    assert {spec.panel for spec in module.intents()} == {"busqueda"}
