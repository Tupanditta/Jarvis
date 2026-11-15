"""Pruebas de arquitectura (T-3.11): importaciones prohibidas, registro y frases.

Recorren el código fuente: RNF-18 (registro), RNF-19 (interfaz común), RNF-20 (interfaz
desacoplada), RNF-27 (sin intérprete de órdenes) y los criterios de Plataforma y del
Sintetizador.
"""
import ast
import inspect
from pathlib import Path

import pytest

import jarvis_assistant
from jarvis_assistant import main as main_module
from jarvis_assistant.config import RouterSettings
from jarvis_assistant.core.action_api import IntentSpec, SlotType
from jarvis_assistant.intent_router.router import IntentRouter
from jarvis_assistant.speaker.phrases import PHRASES, parameters

SRC = Path(jarvis_assistant.__file__).resolve().parent
FILES = sorted(SRC.rglob("*.py"))


def relative(path: Path) -> str:
    return path.relative_to(SRC).as_posix()


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def imports_any(path: Path, *prefixes: str) -> list[str]:
    return sorted(
        name for name in imported_modules(path)
        if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)
    )  # fmt: skip


def under(*folders: str) -> list[Path]:
    return [path for path in FILES if relative(path).split("/")[0] in folders]


# --- Importaciones prohibidas ----------------------------------------------------------------


@pytest.mark.parametrize(
    "path", under("core", "action_modules", "intent_router", "speaker"), ids=relative
)
def test_el_nucleo_y_los_modulos_no_importan_la_interfaz_ni_qt(path):
    """RNF-20."""
    assert imports_any(path, "jarvis_assistant.ui", "PySide6") == []


@pytest.mark.parametrize("path", FILES, ids=relative)
def test_solo_los_adaptadores_tocan_el_sistema_operativo(path):
    """Criterio de Plataforma: `ctypes`, `winreg` y `sys.platform`, solo en `os_adapters/`,
    `ui/` y `process/`. `main.py` elige el adaptador según el sistema."""
    name = relative(path)
    if name.split("/")[0] in ("os_adapters", "ui", "process") or name == "main.py":
        return
    assert imports_any(path, "ctypes", "winreg", "msvcrt") == []
    assert "sys.platform" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", under("action_modules"), ids=relative)
def test_un_modulo_de_accion_no_importa_otro_modulo_ni_la_plataforma_real(path):
    others = [
        name for name in imports_any(path, "jarvis_assistant.action_modules")
        if name != "jarvis_assistant.action_modules"
    ]  # fmt: skip
    assert others == []
    assert imports_any(
        path, "jarvis_assistant.os_adapters.windows", "jarvis_assistant.process", "subprocess"
    ) == []


@pytest.mark.parametrize("path", under("intent_router"), ids=relative)
def test_el_enrutador_no_ejecuta_acciones_ni_habla_ni_publica_eventos(path):
    assert imports_any(
        path, "jarvis_assistant.action_modules", "jarvis_assistant.speaker",
        "jarvis_assistant.core.event_bus", "jarvis_assistant.core.orchestrator",
    ) == []  # fmt: skip


@pytest.mark.parametrize("path", FILES, ids=relative)
def test_ninguna_llamada_usa_un_interprete_de_ordenes(path):
    """RNF-27: ni `shell=True`, ni `os.system`, ni `create_subprocess_shell`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            assert keyword.arg != "shell", f"{relative(path)}:{node.lineno}"
        called = ast.unparse(node.func)
        assert called not in ("os.system", "os.popen"), f"{relative(path)}:{node.lineno}"
        assert not called.endswith("create_subprocess_shell"), f"{relative(path)}:{node.lineno}"


# --- Registro e interfaz común ---------------------------------------------------------------


@pytest.fixture
def modules():
    return [create() for create in main_module.ACTION_MODULES]


def test_cada_modulo_cumple_la_interfaz_comun(modules):
    names = [module.name for module in modules]
    assert len(set(names)) == len(names)
    for module in modules:
        assert module.name and module.title
        assert inspect.iscoroutinefunction(module.execute)
        assert list(inspect.signature(module.execute).parameters) == ["action", "params", "ctx"]
        specs = module.intents()
        assert specs and all(isinstance(spec, IntentSpec) for spec in specs)
        for hook in ("on_session_opened", "on_session_closed"):
            if hasattr(module, hook):
                assert inspect.iscoroutinefunction(getattr(module, hook))


def test_todos_los_modulos_se_registran_sin_conflictos_de_patrones(modules):
    router = IntentRouter(RouterSettings())
    for module in modules:
        router.register(module)
    registered = {module for module, _spec in router.specs()}
    assert registered == {"nucleo", *(module.name for module in modules)}


def test_cada_accion_declarada_la_atiende_su_modulo(modules):
    """Una acción del registro que `execute` no conoce es un error de registro (RNF-19)."""
    for module in modules:
        source = inspect.getsource(type(module).execute)
        for spec in module.intents():
            assert f'"{spec.action}"' in source, f"{module.name}.{spec.action}"


def test_las_entidades_de_cada_intencion_tienen_un_tipo_que_el_enrutador_resuelve(modules):
    supported = set(SlotType) - {SlotType.DURATION, SlotType.DATETIME}
    for module in modules:
        for spec in module.intents():
            assert all(slot.type in supported for slot in spec.slots)
            # Lo que se puede decir se puede explicar: la ayuda sale de aquí (RF-92).
            assert spec.panel is None or isinstance(spec.panel, str)
        described = {spec.action for spec in module.intents() if spec.description}
        assert described == {spec.action for spec in module.intents()}, module.name


def test_anadir_un_modulo_es_anadirlo_a_la_lista_de_main():
    """RNF-18: la lista de `main.py` es el único registro."""
    source = (SRC / "main.py").read_text(encoding="utf-8")
    assert "ACTION_MODULES" in source
    for path in under("core", "intent_router", "ui", "speaker"):
        assert imports_any(path, "jarvis_assistant.action_modules") == [], relative(path)


# --- Frases ----------------------------------------------------------------------------------


def phrase_uses() -> list[tuple[str, int, str, set[str] | None]]:
    """Cada `Phrase("id", {...})` del código: archivo, línea, id y parámetros literales."""
    uses = []
    for path in FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and ast.unparse(node.func) == "Phrase"):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue  # id calculado: lo cubren las pruebas de su módulo
            keys: set[str] | None = set()
            if len(node.args) > 1:
                params = node.args[1]
                if isinstance(params, ast.Dict) and all(
                    isinstance(key, ast.Constant) for key in params.keys
                ):
                    keys = {key.value for key in params.keys}  # type: ignore[union-attr]
                else:
                    keys = None  # parámetros no literales
            uses.append((relative(path), node.lineno, node.args[0].value, keys))
    return uses


def test_cada_frase_usada_existe_en_el_catalogo_y_recibe_sus_parametros():
    uses = phrase_uses()
    assert len(uses) > 30
    for file, line, phrase_id, keys in uses:
        assert phrase_id in PHRASES, f"{file}:{line}: {phrase_id}"
        if keys is not None:
            assert keys == set(parameters(phrase_id)), f"{file}:{line}: {phrase_id}"


def test_las_frases_de_ruta_que_calcula_el_enrutador_existen():
    for kind in ("no_existe", "no_es_carpeta"):
        assert parameters(f"ruta.{kind}") == ("nombre",)
