"""Juego de frases de prueba de las intenciones (catalogo-intenciones.md, sección 6; RNF-11).

El enrutador se monta con los módulos reales de `main.ACTION_MODULES`, sobre un sistema de
archivos temporal: texto escrito → intención y entidades esperadas.
"""
import pytest

from jarvis_assistant.action_modules.app_launcher import AppLauncher
from jarvis_assistant.config import AppEntry, Catalog, PageEntry, RouterSettings
from jarvis_assistant.core.action_api import (
    CommandLine,
    Intent,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.state_machine import (
    Answer,
    AssistantState,
    Control,
    ControlKind,
    IntentMatched,
    NoMatch,
    WakeWord,
)
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router.router import (
    HELP,
    REPEAT,
    IntentRouter,
    ParamError,
    RegistrationError,
)
from jarvis_assistant.main import ACTION_MODULES
from jarvis_assistant.os_adapters.base import DiscoveredApp

S = AssistantState
WINDOW_TITLES = ("Actividad", "Comandos", "Aperturas", "Búsqueda", "Historial", "Ayuda",
                 "Recordatorios", "Protocolo")  # fmt: skip
ALIASES = {"ce de": "cd", "ele ese": "ls", "guit": "git"}


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "home"
    for folder in ("Proyectos/Jarvis", "Documentos", "Descargas", "Downloads"):
        (home / folder).mkdir(parents=True)
    (home / "notas.txt").write_text("x")
    return home


@pytest.fixture
def router(home):
    workdir = Workdir(home)
    places = {"documentos": home / "Documentos", "descargas": home / "Descargas"}
    router = IntentRouter(
        RouterSettings(), ALIASES, places=places, workdir=workdir, windows=WINDOW_TITLES
    )
    for create in ACTION_MODULES:
        module = create()
        if isinstance(module, AppLauncher):
            module._catalog = Catalog(
                apps=(AppEntry("Visual Studio Code", "code.exe", aliases=("code", "el editor")),),
                pages=(PageEntry("GitHub", "https://github.com", aliases=("git hub",)),),
            )
            module._discovered = (DiscoveredApp("Bloc de notas", "notepad.lnk"),)
        router.register(module)
    router.workdir = workdir
    return router


def intent_of(router, text, state=S.LISTENING_COMMAND) -> Intent:
    entry = router.route(text, state)
    assert isinstance(entry, IntentMatched), f"«{text}» → {entry!r}"
    return entry.intent


# --- Un caso por cada patrón -----------------------------------------------------------------

PLAIN = [
    # Núcleo
    ("ayuda", "nucleo.ayuda"), ("qué puedes hacer", "nucleo.ayuda"),
    ("qué sabes hacer", "nucleo.ayuda"),
    ("repite", "nucleo.repetir"), ("repítelo", "nucleo.repetir"),
    ("puedes repetir", "nucleo.repetir"),
    ("preséntate", "nucleo.presentate"), ("presentate", "nucleo.presentate"),
    ("quién eres", "nucleo.presentate"),
    ("muestra la pantalla", "nucleo.mostrar_pantalla"),
    ("pantalla completa", "nucleo.mostrar_pantalla"),
    ("oculta la pantalla", "nucleo.ocultar_pantalla"),
    ("minimiza la pantalla", "nucleo.ocultar_pantalla"),
    ("aparta módulos", "nucleo.apartar_ventanas"),
    ("aparta los módulos", "nucleo.apartar_ventanas"),
    ("aparta todas las ventanas", "nucleo.apartar_ventanas"),
    ("desaparta módulos", "nucleo.desapartar_ventanas"),
    ("desaparta los módulos", "nucleo.desapartar_ventanas"),
    ("desaparta todas las ventanas", "nucleo.desapartar_ventanas"),
    # Historial
    ("muestra el historial", "historial.mostrar"), ("historial de sesiones", "historial.mostrar"),
    ("enséñame el historial", "historial.mostrar"),
    ("actividades de esta sesión", "historial.actividades"),
    ("qué he hecho", "historial.actividades"),
    # Comandos
    ("lista", "comandos.ls"), ("lista el directorio", "comandos.ls"),
    ("qué hay aquí", "comandos.ls"), ("ls", "comandos.ls"),
    ("dónde estoy", "comandos.pwd"), ("directorio actual", "comandos.pwd"),
    ("en qué carpeta estoy", "comandos.pwd"),
    ("árbol", "comandos.arbol"), ("muestra el árbol", "comandos.arbol"),
    ("limpia", "comandos.clear"), ("limpia la consola", "comandos.clear"),
    ("clear", "comandos.clear"),
    ("abre una consola", "comandos.abrir_consola"), ("abre la consola", "comandos.abrir_consola"),
    ("abre una terminal", "comandos.abrir_consola"),
    ("abre la terminal", "comandos.abrir_consola"),
    # Apertura
    ("abre esta carpeta", "apertura.abrir_carpeta"),
    ("abre la carpeta actual", "apertura.abrir_carpeta"),
]  # fmt: skip


@pytest.mark.parametrize(("text", "key"), PLAIN)
def test_patrones_sin_entidades(router, text, key):
    intent = intent_of(router, text)
    assert intent.key == key
    assert intent.params == {} and intent.error is None


def with_entities(home):
    code = CommandLine("git", "git", ("status",))
    return [
        ("aparta comandos", "nucleo.apartar_ventana", {"ventana": "Comandos"}),
        ("aparta busqueda", "nucleo.apartar_ventana", {"ventana": "Búsqueda"}),
        ("aparta la ventana de recordatorios", "nucleo.apartar_ventana",
         {"ventana": "Recordatorios"}),
        ("desaparta comandos", "nucleo.desapartar_ventana", {"ventana": "Comandos"}),
        ("desaparta la ventana de búsqueda", "nucleo.desapartar_ventana",
         {"ventana": "Búsqueda"}),
        ("actividades de la sesión doce", "historial.actividades", {"id": 12}),
        ("muestra las actividades de la sesión 3", "historial.actividades", {"id": 3}),
        ("qué hice en la sesión doce", "historial.actividades", {"id": 12}),
        ("ve a proyectos barra jarvis", "comandos.cd", {"ruta": home / "Proyectos/Jarvis"}),
        ("entra en proyectos", "comandos.cd", {"ruta": home / "Proyectos"}),
        ("cambia a la carpeta documentos", "comandos.cd", {"ruta": home / "Documentos"}),
        ("cd proyectos", "comandos.cd", {"ruta": home / "Proyectos"}),
        ("ve atrás", "comandos.cd", {"ruta": home.parent}),
        ("árbol de documentos", "comandos.arbol", {"ruta": home / "Documentos"}),
        ("muestra el árbol de proyectos", "comandos.arbol", {"ruta": home / "Proyectos"}),
        ("mapa de proyectos", "comandos.arbol", {"ruta": home / "Proyectos"}),
        ("ejecuta git status", "comandos.ejecutar", {"comando": code}),
        ("lanza el comando git status", "comandos.ejecutar", {"comando": code}),
        ("corre git status", "comandos.ejecutar", {"comando": code}),
        ("abre Visual Studio Code", "apertura.abrir", {"objetivo": "Visual Studio Code"}),
        ("abrir el editor", "apertura.abrir", {"objetivo": "el editor"}),
        ("lanza GitHub", "apertura.abrir", {"objetivo": "GitHub"}),
        ("inicia el bloc de notas", "apertura.abrir", {"objetivo": "Bloc de notas"}),
        ("abre la carpeta descargas", "apertura.abrir_carpeta", {"ruta": home / "Descargas"}),
        ("muestra la carpeta proyectos", "apertura.abrir_carpeta", {"ruta": home / "Proyectos"}),
        ("busca presupuesto", "busqueda.buscar", {"consulta": "presupuesto", "tipo": "ambos"}),
        ("encuentra presupuesto", "busqueda.buscar",
         {"consulta": "presupuesto", "tipo": "ambos"}),
        ("busca el archivo factura enero", "busqueda.buscar",
         {"consulta": "factura enero", "tipo": "archivos"}),
        ("busca archivos factura", "busqueda.buscar", {"consulta": "factura", "tipo": "archivos"}),
        ("encuentra el archivo factura", "busqueda.buscar",
         {"consulta": "factura", "tipo": "archivos"}),
        ("busca la carpeta prácticas", "busqueda.buscar",
         {"consulta": "prácticas", "tipo": "carpetas"}),
        ("busca carpetas prácticas", "busqueda.buscar",
         {"consulta": "prácticas", "tipo": "carpetas"}),
        ("encuentra la carpeta prácticas", "busqueda.buscar",
         {"consulta": "prácticas", "tipo": "carpetas"}),
        ("abre el resultado dos", "busqueda.abrir_resultado", {"n": 2}),
        ("abre el resultado número 3", "busqueda.abrir_resultado", {"n": 3}),
        ("abre la carpeta del resultado dos", "busqueda.abrir_ubicacion", {"n": 2}),
        ("dónde está el resultado dos", "busqueda.abrir_ubicacion", {"n": 2}),
    ]  # fmt: skip


def test_patrones_con_entidades(router, home):
    for text, key, params in with_entities(home):
        intent = intent_of(router, text)
        assert (intent.key, dict(intent.params), intent.error) == (key, params, None), text


def test_traer_al_frente_busca_entre_lo_abierto(router):
    assert intent_of(router, "trae al frente GitHub").error == Phrase(
        "entidad.no_encontrado", {"nombre": "GitHub"}
    )


# --- Variaciones de escritura ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("¿Dónde estoy?", "comandos.pwd"),
        ("DONDE ESTOY", "comandos.pwd"),
        ("donde estoi", "comandos.pwd"),
        ("Muestra el historial.", "historial.mostrar"),
        ("muetra el historial", "historial.mostrar"),
        ("que hay aqui", "comandos.ls"),
        ("ele ese", "comandos.ls"),
        ("Abre una terminal, por favor", None),
        ("avre la carpeta descargas", "apertura.abrir_carpeta"),
        ("abre la carpta descargas", "apertura.abrir_carpeta"),
        ("ce de proyectos", "comandos.cd"),
        ("Ejecuta guit status", "comandos.ejecutar"),
        ("ejecta git status", "comandos.ejecutar"),
        ("buska presupuesto", "busqueda.buscar"),
    ],
)
def test_variaciones_de_escritura(router, text, key):
    entry = router.route(text, S.LISTENING_COMMAND)
    if key is None:
        assert isinstance(entry, NoMatch | IntentMatched)  # no debe confundirse con otra orden
        assert not isinstance(entry, IntentMatched) or entry.intent.key != "comandos.pwd"
    else:
        assert isinstance(entry, IntentMatched) and entry.intent.key == key, text
        assert entry.intent.error is None, text


def test_entidades_en_otro_idioma(router, home):
    assert intent_of(router, "abre Visual Studio Code").params["objetivo"] == "Visual Studio Code"
    assert intent_of(router, "ejecuta git status").params["comando"].args == ("status",)
    assert intent_of(router, "ve a Downloads").params["ruta"] == home / "Downloads"


def test_el_texto_libre_conserva_lo_que_el_usuario_escribio(router):
    assert intent_of(router, "Busca Informe FINAL (v2).").params["consulta"] == "Informe FINAL (v2)"


def test_la_descripcion_de_la_tarea_es_el_texto_escrito(router):
    assert intent_of(router, "  ¿Dónde estoy? ").description == "¿Dónde estoy?"
    assert intent_of(router, "lista").panel == "comandos"


# --- Desambiguación --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("abre la carpeta descargas", "apertura.abrir_carpeta"),
        ("abre una terminal", "comandos.abrir_consola"),
        ("abre la carpeta del resultado dos", "busqueda.abrir_ubicacion"),
        ("abre el resultado dos", "busqueda.abrir_resultado"),
        ("abre GitHub", "apertura.abrir"),
        ("lanza el comando git status", "comandos.ejecutar"),
        ("lanza GitHub", "apertura.abrir"),
        ("busca el archivo notas", "busqueda.buscar"),
        ("muestra el árbol de documentos", "comandos.arbol"),
        ("muestra la carpeta documentos", "apertura.abrir_carpeta"),
        ("muestra las actividades de la sesión 2", "historial.actividades"),
    ],
)
def test_desambiguacion_por_especificidad(router, text, key):
    assert intent_of(router, text).key == key


def test_si_las_entidades_no_se_resuelven_se_prueba_el_siguiente_candidato(router):
    # «abre el resultado…» esperaba un número; «abre {objetivo}» sí se resuelve.
    intent = intent_of(router, "abre el editor")
    assert (intent.key, intent.params) == ("apertura.abrir", {"objetivo": "el editor"})
    intent = intent_of(router, "abre el resultado github")
    assert intent.key == "apertura.abrir"


def test_si_ningun_candidato_se_resuelve_vale_el_error_del_primero(router):
    intent = intent_of(router, "abre la carpeta fotos")
    assert intent.key == "apertura.abrir_carpeta"
    assert intent.error == Phrase("ruta.no_existe", {"nombre": "fotos"})
    assert intent.params == {}


@pytest.mark.parametrize(
    ("text", "key", "error"),
    [
        ("ve a fotos", "comandos.cd", Phrase("ruta.no_existe", {"nombre": "fotos"})),
        ("ve a notas.txt", "comandos.cd", Phrase("ruta.no_es_carpeta", {"nombre": "notas.txt"})),
        ("ejecuta rm -rf algo", "comandos.ejecutar", Phrase("comandos.no_permitido")),
        ("abre el navegador", "apertura.abrir",
         Phrase("entidad.no_encontrado", {"nombre": "el navegador"})),
        ("abre el resultado muchos", "busqueda.abrir_resultado", Phrase("entidad.numero")),
        # Una alternativa de otro módulo que solo se parece no se prueba: no se crea nada.
        ("abr la carpeta fotos", "apertura.abrir_carpeta",
         Phrase("ruta.no_existe", {"nombre": "fotos"})),
        ("crea el archivo notas en fotos", "creacion.crear_archivo",
         Phrase("ruta.no_existe", {"nombre": "fotos"})),
    ],
)  # fmt: skip
def test_errores_de_entidad(router, text, key, error):
    intent = intent_of(router, text)
    assert (intent.key, intent.error) == (key, error)


# --- Activación, control y controles negativos -----------------------------------------------


@pytest.mark.parametrize("text", ["hey jarvis", "Hey, Jarvis.", "hey jarbis", "jarvis"])
@pytest.mark.parametrize("state", list(AssistantState))
def test_frase_de_activacion_en_todos_los_estados(router, text, state):
    assert router.route(text, state) == WakeWord()


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("gracias jarvis", ControlKind.REPOSO),
        ("gracias, Jarvis.", ControlKind.REPOSO),
        ("grasias jarvis", ControlKind.REPOSO),
        ("buenas noches jarvis", ControlKind.CERRAR),
        ("cancelar", ControlKind.CANCELAR),
        ("olvídalo", ControlKind.CANCELAR),
    ],
)
def test_frases_de_control(router, text, kind):
    assert router.route(text, S.LISTENING_COMMAND) == Control(kind)


@pytest.mark.parametrize(
    "text",
    ["muchas gracias jarvis por todo", "buenas noches", "qué tiempo hace hoy", "abre", "hola",
     "cd", "busca", "ejecuta"],
)  # fmt: skip
def test_controles_negativos(router, text):
    assert router.route(text, S.LISTENING_COMMAND) == NoMatch(text)


def test_jarvis_delante_de_una_orden_no_es_frase_de_activacion(router):
    entry = router.route("jarvis abre el navegador", S.LISTENING_COMMAND)
    assert entry == NoMatch("jarvis abre el navegador")


def test_texto_vacio(router):
    assert router.route("", S.DORMIDO) is None
    assert router.route("   ", S.LISTENING_COMMAND) == NoMatch("   ")


def test_en_espera_una_orden_no_se_clasifica_como_intencion(router):
    entry = router.route("abre GitHub", S.AWAITING_CONFIRMATION)
    assert entry == Answer(valid=False)


def test_en_dormido_solo_vale_la_frase_de_activacion(router):
    assert router.route("lista", S.DORMIDO) is None


def test_en_reposo_una_orden_se_atiende(router):
    assert intent_of(router, "lista", S.IDLE).key == "comandos.ls"


# --- Determinismo, registro, ayuda y protocolos ----------------------------------------------


def test_misma_entrada_misma_salida_en_mil_repeticiones(router):
    texts = ["abre la carpeta descargas", "ejecuta git status", "abre el navegador", "hola"]
    first = [router.route(text, S.LISTENING_COMMAND) for text in texts]
    for _ in range(250):
        assert [router.route(text, S.LISTENING_COMMAND) for text in texts] == first


class _Module:
    title = "Prueba"

    def __init__(self, name, *specs):
        self.name = name
        self._specs = specs

    def intents(self):
        return self._specs


def test_registrar_dos_intenciones_con_el_mismo_patron_falla(router):
    with pytest.raises(RegistrationError, match=r"comandos\.ls"):
        router.register(_Module("otro", IntentSpec("listar", ("Lista",))))
    with pytest.raises(RegistrationError):
        router.register(
            _Module("otro", IntentSpec("a", ("haz algo",)), IntentSpec("b", ("haz algo",)))
        )


@pytest.mark.parametrize(
    "spec",
    [
        IntentSpec("a", ()),
        IntentSpec("a", ("{x} primero",), (Slot("x", SlotType.TEXT),)),
        IntentSpec("a", ("haz {x}",)),
        IntentSpec("a", ("haz {x}",), (Slot("x", SlotType.CATALOG, catalog="no existe"),)),
    ],
)
def test_intenciones_que_no_se_pueden_registrar(router, spec):
    with pytest.raises(RegistrationError):
        router.register(_Module("otro", spec))
    assert router.route("haz algo", S.LISTENING_COMMAND) == NoMatch("haz algo")


def test_un_modulo_no_se_registra_dos_veces(router):
    with pytest.raises(RegistrationError):
        router.register(ACTION_MODULES[0]())


def test_la_ayuda_sale_del_registro(router):
    groups = router.help()
    assert [group.module for group in groups] == [
        "comandos", "apertura", "busqueda", "creacion", "historial", "recordatorio",
        "protocolos", "permisos", "credenciales", "perfiles", "nucleo",
    ]  # fmt: skip
    assert groups[0].title == "Comandos"
    for group in groups:
        for entry in group.entries:
            assert entry.description and entry.example
            # El ejemplo de la ayuda es una orden que el enrutador entiende.
            assert intent_of(router, entry.example).module == group.module, entry.example
    assert len(groups[2].entries) == 3  # las tres variantes de «buscar» son una sola orden


def test_intenciones_del_nucleo(router):
    assert intent_of(router, "ayuda") == HELP
    assert intent_of(router, "repite") == REPEAT


def test_los_parametros_de_un_protocolo_se_resuelven_igual(router, home):
    assert router.resolve_params("comandos", "cd", {"ruta": "proyectos barra jarvis"}) == {
        "ruta": home / "Proyectos" / "Jarvis"
    }
    assert router.resolve_params("comandos", "ejecutar", {"comando": "git status"}) == {
        "comando": CommandLine("git", "git", ("status",))
    }
    assert router.resolve_params("busqueda", "buscar", {"consulta": "notas"}) == {
        "consulta": "notas", "tipo": "ambos",
    }  # fmt: skip
    assert router.resolve_params("historial", "actividades", {"id": 4}) == {"id": 4}
    with pytest.raises(ParamError):
        router.resolve_params("comandos", "cd", {"ruta": "fotos"})
    with pytest.raises(KeyError):
        router.resolve_params("comandos", "volar", {})


def test_con_permisos_la_ayuda_solo_lista_los_modulos_permitidos(router):
    router.set_scope(frozenset({"apertura", "nucleo"}))
    assert [group.module for group in router.help()] == ["apertura", "nucleo"]
    # Una orden de un módulo no permitido sigue reconociéndose: `run_task` la rechaza.
    assert intent_of(router, "ejecuta git status").module == "comandos"
    router.set_scope(None)
    assert "comandos" in [group.module for group in router.help()]
