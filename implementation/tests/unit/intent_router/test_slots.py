"""Analizadores de entidades (enrutador-intenciones.md, secciones 4, 6 y 7)."""
from pathlib import Path, PurePath

import pytest

from jarvis_assistant.config import Binary
from jarvis_assistant.intent_router.normalizer import tokenize
from jarvis_assistant.intent_router.slots import catalogs, command_line, names, numbers, paths

# --- Números ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("12", 12), ("0", 0), ("cero", 0), ("uno", 1), ("una", 1), ("doce", 12),
        ("dieciseis", 16), ("veintidos", 22), ("treinta", 30), ("treinta y uno", 31),
        ("noventa y nueve", 99), ("cien", 100), ("ciento tres", 103),
        ("doscientos cuarenta y cinco", 245), ("novecientos noventa y nueve", 999),
        ("quinientas", 500), ("primero", 1), ("la segunda", 2), ("el tercero", 3),
        ("decimo", 10), ("numero dos", 2), ("el numero 4", 4),
    ],
)  # fmt: skip
def test_numeros(text, value):
    assert numbers.parse(text) == value


@pytest.mark.parametrize(
    "text", ["", "el", "muchos", "treinta y", "treinta y veinte", "cien tres", "dos tres", "-3"]
)
def test_lo_que_no_es_un_numero(text):
    assert numbers.parse(text) is None


# --- Catálogos -------------------------------------------------------------------------------

APPS = ["Visual Studio Code", "Bloc de notas", "Calculadora"]


def test_catalogo_coincidencia_difusa():
    assert catalogs.best_match("visual studio code", APPS, 75) == "Visual Studio Code"
    assert catalogs.best_match("visual estudio code", APPS, 75) == "Visual Studio Code"
    assert catalogs.best_match("calculadora", APPS, 75) == "Calculadora"


def test_catalogo_sin_coincidencia():
    assert catalogs.best_match("el navegador", APPS, 75) is None
    assert catalogs.best_match("", APPS, 75) is None
    assert catalogs.best_match("calculadora", [], 75) is None


def test_catalogo_a_igualdad_gana_el_orden_alfabetico():
    assert catalogs.best_match("notas", ["Notas B", "Notas A"], 75) == "Notas A"
    assert catalogs.best_match("notas", ["Notas A", "Notas B"], 75) == "Notas A"


# --- Rutas -----------------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    home = tmp_path / "home"
    for folder in ("Proyectos/Jarvis/src", "Proyectos/Web", "Documentos", "Downloads"):
        (home / folder).mkdir(parents=True)
    (home / "notas.txt").write_text("x")
    return home


def resolve(spoken, home, workdir=None, places=None):
    return paths.resolve(spoken, workdir or home, places or {}, home=home, threshold=80)


def test_ruta_palabras_especiales(tree):
    work = tree / "Proyectos" / "Jarvis"
    assert resolve("aquí", tree, work) == work
    assert resolve("esta carpeta", tree, work) == work
    assert resolve("atrás", tree, work) == tree / "Proyectos"
    assert resolve("carpeta anterior", tree, work) == tree / "Proyectos"
    assert resolve("inicio", tree, work) == tree
    assert resolve("carpeta personal", tree, work) == tree


def test_ruta_hijo_del_directorio_de_trabajo_por_similitud(tree):
    assert resolve("proyectos", tree) == tree / "Proyectos"
    assert resolve("proyetos", tree) == tree / "Proyectos"  # errata
    assert resolve("Downloads", tree) == tree / "Downloads"  # otro idioma


def test_ruta_por_niveles_con_barra(tree):
    assert resolve("proyectos barra jarvis", tree) == tree / "Proyectos" / "Jarvis"
    assert resolve("proyectos barra jarvis barra src", tree) == tree / "Proyectos/Jarvis/src"


def test_ruta_lugar_con_nombre(tree, tmp_path):
    place = tmp_path / "otro" / "Universidad"
    place.mkdir(parents=True)
    places = {"universidad": place, "proyectos": tree / "Proyectos"}
    work = tree / "Documentos"
    assert resolve("universidad", tree, work, places) == place
    assert resolve("unibersidad", tree, work, places) == place
    assert resolve("proyectos barra web", tree, work, places) == tree / "Proyectos" / "Web"


def test_ruta_literal(tree):
    assert resolve(str(tree / "Documentos"), tree) == tree / "Documentos"
    assert resolve("Proyectos/Jarvis", tree) == tree / "Proyectos" / "Jarvis"


def test_ruta_que_no_existe(tree):
    with pytest.raises(paths.PathError) as error:
        resolve("fotos", tree)
    assert (error.value.kind, error.value.name) == ("no_existe", "fotos")
    with pytest.raises(paths.PathError) as error:
        resolve("proyectos barra fotos", tree)
    assert (error.value.kind, error.value.name) == ("no_existe", "fotos")
    with pytest.raises(paths.PathError) as error:
        resolve(str(tree / "nada"), tree)
    assert error.value.kind == "no_existe"


def test_ruta_que_no_es_una_carpeta(tree):
    with pytest.raises(paths.PathError) as error:
        resolve("notas.txt", tree)
    assert (error.value.kind, error.value.name) == ("no_es_carpeta", "notas.txt")
    with pytest.raises(paths.PathError) as error:
        resolve(str(tree / "notas.txt"), tree)
    assert error.value.kind == "no_es_carpeta"


def test_ruta_unidad_de_disco():
    assert paths._drive("disco ce") == Path("C:\\")
    assert paths._drive("unidad de") == Path("D:\\")
    assert paths._drive("disco duro") is None


# --- Nombres nuevos --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spoken", "name"),
    [
        ("notas punto txt", "notas.txt"),
        ("informe dos punto txt", "informe dos.txt"),
        ("mi guion bajo archivo", "mi_archivo"),
        ("copia guion uno", "copia-uno"),
        ("Apuntes", "Apuntes"),
        ("notas.txt", "notas.txt"),
        ("punto gitignore", ".gitignore"),
    ],
)
def test_nombres(spoken, name):
    assert names.build(spoken) == name


@pytest.mark.parametrize("spoken", ["", "   ", "a/b", "que?", "con", "NUL punto txt", "punto"])
def test_nombres_no_validos(spoken):
    with pytest.raises(names.InvalidNameError):
        names.build(spoken)


def test_ruta_nueva_con_barra():
    assert names.build_path("backend barra src barra modelos") == PurePath("backend/src/modelos")
    assert names.build_path("a/b") == PurePath("a/b")
    with pytest.raises(names.InvalidNameError):
        names.build_path("a barra barra b")


# --- Línea de comando ------------------------------------------------------------------------

BINARIES = (
    Binary("git", "git", aliases=("guit",)),
    Binary("gcc", "gcc", aliases=("ge ce ce",), timeout_seconds=60),
    Binary("g++", "g++"),
    Binary("python", "C:/Python/python.exe"),
)


def command(text, aliases=None):
    tokens = tokenize(text, aliases)
    return command_line.parse(tokens, 0, len(tokens.words), BINARIES)


def test_comando_binario_permitido_y_argumentos():
    parsed = command("git status")
    assert (parsed.name, parsed.executable, parsed.args) == ("git", "git", ("status",))
    assert parsed.text == "git status"
    assert command("python").args == ()
    assert command("python").executable == "C:/Python/python.exe"


def test_comando_conserva_las_mayusculas_de_los_argumentos():
    assert command("gcc Main.c -o Programa").args == ("Main.c", "-o", "Programa")
    assert command("gcc main.c").timeout_seconds == 60


def test_comando_guion_y_punto_escritos():
    assert command("gcc main punto c").args == ("main.c",)
    assert command("python guion guion version").args == ("--version",)
    assert command("gcc main punto c guion o programa").args == ("main.c", "-o", "programa")
    assert command("git add punto").args == ("add", ".")


def test_comando_por_alias():
    assert command("guit status").name == "git"
    assert command("ge ce ce main.c").args == ("main.c",)
    assert command("guit status", {"guit": "git"}).args == ("status",)
    assert command("g++ main.cpp").name == "g++"


def test_comando_sin_el_punto_final_de_la_frase():
    assert command("git status.").args == ("status",)


@pytest.mark.parametrize("text", ["rm -rf algo", "format c:", "gitx status"])
def test_comando_no_permitido(text):
    with pytest.raises(command_line.NotAllowedError):
        command(text)
