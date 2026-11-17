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


@pytest.mark.parametrize("path", [p for p in FILES if relative(p).split("/")[0] != "configurator"],
                         ids=relative)
def test_nadie_importa_la_ventana_de_configuracion_salvo_main(path):
    if relative(path) in COMPOSITION_ROOT:
        return
    assert imports_any(path, "jarvis_assistant.configurator") == []


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


# --- Dependencias entre paquetes (T-7.7) -----------------------------------------------------

# Qué puede importar cada paquete de los demás (arquitectura.md, sección 8). Un paquete siempre
# puede importar sus propios módulos. Una dependencia nueva entre paquetes se añade aquí a
# propósito, nunca por accidente: así los paquetes siguen siendo independientes y sustituibles.
ALLOWED_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "config": (),
    "paths": (),
    # `os_adapters.base` solo para anotar tipos: el núcleo no llama al sistema operativo.
    "core": ("config", "os_adapters.base"),
    "intent_router": ("config", "core.action_api", "core.state_machine", "core.workdir"),
    "speaker": ("config", "core.action_api", "core.clock", "core.event_bus", "core.events"),
    # Lo que un módulo de acción conoce: la interfaz común y sus tipos, los repositorios, los
    # contratos de la plataforma y funciones puras de texto compartidas con el enrutador y la
    # voz. Nunca el orquestador, la FSM, la cola de órdenes, otro módulo ni la interfaz.
    "action_modules": (
        "config",
        "core.action_api", "core.clock", "core.content", "core.database", "core.event_bus",
        "core.events", "core.notices", "core.repositories", "core.workdir",
        "os_adapters.base", "os_adapters.processes",
        "intent_router.normalizer", "intent_router.slots",
        "speaker.formats", "speaker.phrases",
    ),
    "os_adapters": ("process.single_instance",),
    # La ventana de configuración: edita y escribe la configuración y reutiliza los
    # componentes y modelos de la interfaz para el editor de plantillas. Del núcleo, solo los
    # tipos de eventos y, para los perfiles protegidos, la base de datos y su contraseña
    # (`core.security`), con su propia conexión. Nadie depende de ella salvo `main.py`.
    "configurator": (
        "config", "core.custody", "core.database", "core.events", "core.security",
        "ui.app", "ui.view_models", "ui.workspace",
    ),
    "process": ("core.events",),
    "ui": (
        "config", "core.action_api", "core.content", "core.event_bus", "core.events",
        "core.repositories",
    ),
}  # fmt: skip

# El orquestador une el enrutador, la voz y los módulos: es el único del núcleo que conoce el
# enrutador y la voz. Los módulos de acción los recibe ya creados de `main.py`.
HUB_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "core/orchestrator.py": (
        "intent_router.batch", "intent_router.router", "speaker.formats", "speaker.phrases",
        "speaker.speaker",
    ),
}  # fmt: skip

# Raíz de composición: conoce todos los paquetes para construir y conectar el grafo.
COMPOSITION_ROOT = ("main.py", "__main__.py", "__init__.py")


def package_of(name: str) -> str:
    """`core/events.py` → `core`; `config.py` → `config`."""
    first = name.split("/")[0]
    return first.removesuffix(".py")


def internal_imports(path: Path) -> list[str]:
    """Lo que importa del propio proyecto, sin el prefijo: `core.events`, `config.Config`…"""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [f"{node.module}.{alias.name}" for alias in node.names]
        else:
            continue
        found += [
            name.removeprefix("jarvis_assistant.") for name in names
            if name.startswith("jarvis_assistant.")
        ]  # fmt: skip
    return found


def allowed(target: str, prefixes: tuple[str, ...]) -> bool:
    return any(target == prefix or target.startswith(prefix + ".") for prefix in prefixes)


@pytest.mark.parametrize(
    "path", [path for path in FILES if relative(path) not in COMPOSITION_ROOT], ids=relative
)
def test_cada_paquete_solo_depende_de_lo_que_permite_el_mapa_de_dependencias(path):
    name = relative(path)
    package = package_of(name)
    assert package in ALLOWED_DEPENDENCIES, f"paquete nuevo sin reglas: {package}"
    permitted = (package, *ALLOWED_DEPENDENCIES[package], *HUB_DEPENDENCIES.get(name, ()))
    forbidden = [target for target in internal_imports(path) if not allowed(target, permitted)]
    assert forbidden == [], name


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
    supported = set(SlotType)
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
