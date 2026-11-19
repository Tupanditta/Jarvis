"""Consolas de Comandos: cada una con su directorio de trabajo (`core/workdir.py`)."""
from pathlib import Path

from jarvis_assistant.core.action_api import MAIN_CONSOLE, is_console
from jarvis_assistant.core.workdir import Consoles, Workdir

HOME = Path("C:/Users/usuario")


def make() -> Consoles:
    return Consoles(Workdir(HOME))


def test_la_principal_siempre_existe_y_es_la_activa():
    consoles = make()
    assert consoles.active == MAIN_CONSOLE and consoles.exists(MAIN_CONSOLE)
    assert consoles.get(None) is consoles.main and consoles.path == HOME


def test_la_consola_de_un_protocolo_tiene_su_propio_directorio():
    consoles = make()
    first, created = consoles.open_for("protocolo-a", "Comandos · a")
    second, _ = consoles.open_for("protocolo-b", "Comandos · b")
    assert created and first == "comandos:protocolo-a" and is_console(first)
    consoles.get(first).change(HOME / "Algebra")
    consoles.get(second).change(HOME / "Fisica")
    assert consoles.get(first).path == HOME / "Algebra"
    assert consoles.get(second).path == HOME / "Fisica"
    assert consoles.main.path == HOME
    assert consoles.title(first) == "Comandos · a"


def test_reabrir_la_consola_de_un_protocolo_la_reutiliza_en_la_carpeta_personal():
    consoles = make()
    console, _ = consoles.open_for("protocolo-a", "Comandos · a")
    workdir = consoles.get(console)
    workdir.change(HOME / "Algebra")
    again, created = consoles.open_for("protocolo-a", "Comandos · a")
    assert again == console and not created
    assert consoles.get(again) is workdir and workdir.path == HOME


def test_la_copia_del_boton_empieza_en_la_carpeta_de_la_original():
    consoles = make()
    consoles.main.change(HOME / "Proyectos")
    copy = consoles.open_copy(MAIN_CONSOLE)
    assert copy == "comandos:2" and consoles.title(copy) == "Comandos 2"
    assert consoles.get(copy).path == HOME / "Proyectos"
    consoles.get(copy).change(HOME)
    assert consoles.main.path == HOME / "Proyectos"  # independientes
    assert consoles.open_copy(copy) == "comandos:3"


def test_el_enrutador_ve_la_consola_activa_o_la_de_using():
    consoles = make()
    console, _ = consoles.open_for("protocolo-a", "Comandos · a")
    consoles.get(console).change(HOME / "Algebra")
    assert consoles.path == HOME
    consoles.focus(console)
    assert consoles.path == HOME / "Algebra"
    with consoles.using(MAIN_CONSOLE):
        assert consoles.path == HOME
    assert consoles.path == HOME / "Algebra"


def test_cerrar_una_consola_devuelve_la_activa_a_la_principal():
    consoles = make()
    console, _ = consoles.open_for("protocolo-a", "Comandos · a")
    consoles.focus(console)
    assert consoles.close(console)
    assert not consoles.exists(console) and consoles.active == MAIN_CONSOLE
    assert consoles.get(console) is consoles.main  # una que ya no existe usa la principal
    assert not consoles.close(console) and not consoles.close(MAIN_CONSOLE)
    consoles.focus(console)
    assert consoles.active == MAIN_CONSOLE


def test_una_sesion_nueva_deja_solo_la_principal():
    consoles = make()
    console, _ = consoles.open_for("protocolo-a", "Comandos · a")
    consoles.focus(console)
    consoles.main.change(HOME / "Proyectos")
    consoles.reset()
    assert not consoles.exists(console) and consoles.active == MAIN_CONSOLE
    assert consoles.main.path == HOME
    assert consoles.open_copy(MAIN_CONSOLE) == "comandos:2"
