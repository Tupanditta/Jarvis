"""Módulo Creación (creacion-archivos.md; CU-09), con un sistema de archivos temporal y
respuestas de diálogo simuladas."""
import ast
import inspect
import os
from pathlib import Path

import pytest

from fakes.context import CANCEL, ContextRig
from jarvis_assistant.action_modules import file_manager
from jarvis_assistant.action_modules.file_manager import FileCreation
from jarvis_assistant.config import Config, DialogueSettings, Settings, StructureDef
from jarvis_assistant.core.action_api import ExpectedType, Phrase

PYTHON = StructureDef("proyecto python", ("src", "tests", "docs/api"))


@pytest.fixture
def rig(tmp_path):
    rig = ContextRig(tmp_path, config=Config(structures=(PYTHON,)))
    yield rig
    rig.close()


@pytest.fixture
def module():
    return FileCreation()


async def run(rig, module, action: str, **params):
    return await module.execute(action, params, rig.ctx)


def created(kind: str, name: str, folder: str) -> Phrase:
    return Phrase("creacion.creado", {"tipo": kind, "nombre": name, "carpeta": folder})


def snapshot(root: Path) -> dict[str, tuple[bytes | None, int]]:
    """Contenido y fecha de todo lo que hay bajo `root`."""
    found = {}
    for path in sorted(root.rglob("*")):
        content = path.read_bytes() if path.is_file() else None
        found[str(path.relative_to(root))] = (content, path.stat().st_mtime_ns)
    return found


# --- Creación sin colisión -------------------------------------------------------------------


async def test_crea_un_archivo_vacio_en_el_directorio_de_trabajo(rig, module):
    result = await run(rig, module, "crear_archivo", nombre="notas.txt")
    target = rig.home / "notas.txt"
    assert target.is_file() and target.read_bytes() == b""
    assert (result.status, result.speech) == (
        "completado", created("el archivo", "notas.txt", "usuario"),
    )  # fmt: skip
    assert result.description == "crear notas.txt"
    assert rig.asked == []


async def test_crea_un_archivo_en_una_ubicacion(rig, module):
    documents = rig.places["documentos"]
    result = await run(rig, module, "crear_archivo", nombre="notas.txt", ruta=documents)
    assert (documents / "notas.txt").is_file()
    assert result.speech == created("el archivo", "notas.txt", documents.name)


async def test_una_ruta_relativa_se_resuelve_respecto_al_directorio_de_trabajo(rig, module):
    (rig.home / "apuntes").mkdir()
    await run(rig, module, "crear_carpeta", nombre="redes", ruta=Path("apuntes"))
    assert (rig.home / "apuntes" / "redes").is_dir()


async def test_crea_una_carpeta(rig, module):
    result = await run(rig, module, "crear_carpeta", nombre="apuntes")
    assert (rig.home / "apuntes").is_dir()
    assert result.speech == created("la carpeta", "apuntes", "usuario")


async def test_crea_un_arbol(rig, module):
    tree = Path("backend") / "src" / "modelos"
    result = await run(rig, module, "crear_arbol", arbol=tree)
    assert (rig.home / tree).is_dir()
    assert result.speech == created("las carpetas", "backend/src/modelos", "usuario")


async def test_un_arbol_reutiliza_las_carpetas_intermedias_existentes(rig, module):
    (rig.home / "backend" / "src").mkdir(parents=True)
    (rig.home / "backend" / "src" / "main.py").write_text("print(1)")
    before = snapshot(rig.home / "backend")
    result = await run(rig, module, "crear_arbol", arbol=Path("backend/src/modelos"))
    assert result.status == "completado"
    assert (rig.home / "backend/src/modelos").is_dir()
    after = snapshot(rig.home / "backend")
    assert set(after) == set(before) | {os.path.join("src", "modelos")}
    main = os.path.join("src", "main.py")
    assert after[main] == before[main]  # ni el contenido ni la fecha del archivo cambian


async def test_una_carpeta_con_barra_se_trata_como_un_arbol(rig, module):
    result = await run(rig, module, "crear_carpeta", nombre="backend barra src")
    assert (rig.home / "backend" / "src").is_dir()
    assert result.speech == created("las carpetas", "backend/src", "usuario")


async def test_crea_una_estructura(rig, module):
    result = await run(
        rig, module, "crear_estructura", estructura="proyecto python", nombre="analizador"
    )
    root = rig.home / "analizador"
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) == [
        "docs", "docs/api", "src", "tests",
    ]  # fmt: skip
    assert result.speech == created("la estructura", "analizador", "usuario")


async def test_una_estructura_desconocida_es_un_error(rig, module):
    result = await run(rig, module, "crear_estructura", estructura="otra", nombre="x")
    assert (result.status, result.speech) == (
        "error", Phrase("entidad.no_encontrado", {"nombre": "otra"}),
    )  # fmt: skip


async def test_el_catalogo_de_estructuras_es_el_de_la_configuracion_vigente(rig, module):
    (provider,) = module.catalogs()["estructuras"]
    assert provider() == []
    await module.on_session_opened(rig.ctx)
    assert provider() == ["proyecto python"]


# --- Ubicación -------------------------------------------------------------------------------


async def test_ubicacion_inexistente(rig, module):
    result = await run(rig, module, "crear_archivo", nombre="a.txt", ruta=rig.home / "fotos")
    assert (result.status, result.speech) == (
        "error", Phrase("ruta.no_existe", {"nombre": "fotos"}),
    )  # fmt: skip
    assert not (rig.home / "fotos").exists()


async def test_una_ubicacion_que_es_un_archivo(rig, module):
    (rig.home / "notas.txt").write_text("x")
    result = await run(rig, module, "crear_carpeta", nombre="a", ruta=rig.home / "notas.txt")
    assert result.speech == Phrase("ruta.no_es_carpeta", {"nombre": "notas.txt"})


async def test_sin_permiso_de_escritura_es_un_error(rig, module, monkeypatch):
    def denied(*_args, **_kwargs):
        raise PermissionError("denegado")

    monkeypatch.setattr(Path, "mkdir", denied)
    result = await run(rig, module, "crear_carpeta", nombre="apuntes")
    assert (result.status, result.speech) == (
        "error", Phrase("creacion.fallo", {"nombre": "apuntes"}),
    )  # fmt: skip


# --- Colisión --------------------------------------------------------------------------------


async def test_colision_resuelta_con_otro_nombre(rig, module):
    (rig.home / "notas.txt").write_text("importante")
    before = snapshot(rig.home)
    rig.answers = ["notas dos.txt"]
    result = await run(rig, module, "crear_archivo", nombre="notas.txt")
    (asked,) = rig.asked
    assert asked.question == Phrase("creacion.colision", {"nombre": "notas.txt"})
    assert asked.expected_type is ExpectedType.NEW_FILENAME
    assert asked.metadata == {"destino": rig.home / "notas.txt", "ubicacion": rig.home}
    assert asked.subject == {"nombre": "notas.txt", "carpeta": "usuario"}
    assert (rig.home / "notas dos.txt").is_file()
    assert result.speech == created("el archivo", "notas dos.txt", "usuario")
    assert result.description == "crear notas dos.txt"
    after = snapshot(rig.home)
    assert after["notas.txt"] == before["notas.txt"]  # ni el contenido ni la fecha cambian


async def test_segunda_colision_vuelve_a_preguntar(rig, module):
    for name in ("a", "b"):
        (rig.home / name).mkdir()
    rig.answers = ["b", "c"]
    result = await run(rig, module, "crear_carpeta", nombre="a")
    assert [asked.question.params["nombre"] for asked in rig.asked] == ["a", "b"]
    assert (rig.home / "c").is_dir() and result.status == "completado"


async def test_tercera_colision_cancela(rig, module):
    for name in ("a", "b", "c"):
        (rig.home / name).mkdir()
    before = snapshot(rig.home)
    rig.answers = ["b", "c"]
    result = await run(rig, module, "crear_carpeta", nombre="a")
    assert len(rig.asked) == 2
    assert (result.status, result.speech, result.detail) == (
        "error", Phrase("general.operacion_cancelada"), "cancelada",
    )  # fmt: skip
    assert snapshot(rig.home) == before


async def test_el_limite_de_colisiones_es_configurable(tmp_path, module):
    config = Config(settings=Settings(dialogue=DialogueSettings(max_collisions=1)))
    rig = ContextRig(tmp_path, config=config)
    try:
        (rig.home / "a").mkdir()
        result = await run(rig, module, "crear_carpeta", nombre="a")
        assert rig.asked == [] and result.detail == "cancelada"
    finally:
        rig.close()


async def test_cancelacion_explicita_o_tiempo_agotado_no_crea_nada(rig, module):
    (rig.home / "notas.txt").write_text("x")
    before = snapshot(rig.home)
    rig.answers = [CANCEL]
    result = await run(rig, module, "crear_archivo", nombre="notas.txt")
    # «Operación cancelada.» ya lo ha dicho el orquestador.
    assert (result.status, result.speech, result.detail) == ("error", None, "cancelada")
    assert snapshot(rig.home) == before


async def test_en_un_arbol_hay_colision_si_existe_la_carpeta_mas_profunda(rig, module):
    (rig.home / "backend/src/modelos").mkdir(parents=True)
    rig.answers = ["entidades"]
    result = await run(rig, module, "crear_arbol", arbol=Path("backend/src/modelos"))
    assert rig.asked[0].question == Phrase("creacion.colision", {"nombre": "modelos"})
    assert rig.asked[0].subject == {"nombre": "modelos", "carpeta": "src"}
    # El nombre nuevo sustituye a la carpeta más profunda.
    assert (rig.home / "backend/src/entidades").is_dir()
    assert result.speech == created("las carpetas", "backend/src/entidades", "usuario")


async def test_en_una_estructura_hay_colision_si_existe_la_raiz(rig, module):
    (rig.home / "analizador").mkdir()
    rig.answers = ["analizador2"]
    await run(rig, module, "crear_estructura", estructura="proyecto python", nombre="analizador")
    assert list((rig.home / "analizador").iterdir()) == []  # la raíz existente no cambia
    assert (rig.home / "analizador2" / "src").is_dir()


async def test_si_el_destino_aparece_entretanto_no_se_sobrescribe(rig, module, monkeypatch):
    """`open(…, "x")` falla si el archivo aparece entre la comprobación y la creación."""
    target = rig.home / "carrera.txt"
    real_exists = Path.exists

    def exists_then_appears(path: Path) -> bool:
        if path == target and not real_exists(path):
            path.write_text("de otro")  # alguien lo crea justo después de comprobar
            return False
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", exists_then_appears)
    rig.answers = [CANCEL]
    result = await run(rig, module, "crear_archivo", nombre="carrera.txt")
    assert target.read_text() == "de otro"
    assert len(rig.asked) == 1 and result.detail == "cancelada"


# --- Prohibiciones ---------------------------------------------------------------------------

_FORBIDDEN_CALLS = {
    "unlink", "rmdir", "rmtree", "remove", "removedirs", "rename", "renames", "replace",
    "write_text", "write_bytes", "truncate", "move", "copy", "copyfile", "touch", "chmod",
}  # fmt: skip


def creation_source() -> str:
    parts = [FileCreation, file_manager._make, file_manager._levels]
    return "\n".join(inspect.getsource(part) for part in parts)


def test_el_codigo_no_borra_ni_escribe_sobre_rutas_existentes():
    tree = ast.parse(creation_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called = ast.unparse(node.func).rsplit(".", 1)[-1]
            assert called not in _FORBIDDEN_CALLS, ast.unparse(node)
            if called == "open":
                modes = [arg.value for arg in node.args[1:] if isinstance(arg, ast.Constant)]
                assert modes == ["x"], ast.unparse(node)
            if called == "mkdir":
                keywords = {k.arg: ast.unparse(k.value) for k in node.keywords}
                assert keywords.get("exist_ok") in ("False", "True")


def test_la_colision_no_se_comprueba_con_expresiones_regulares():
    tree = ast.parse(inspect.getsource(file_manager))
    imported = {
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    } | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {"re", "regex", "fnmatch"} & imported
