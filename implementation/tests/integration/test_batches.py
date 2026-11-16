"""Varias órdenes en un mensaje, cola de órdenes y cola de voz, de principio a fin.

El grafo es el de `build_app` con los módulos reales y dos módulos de pruebas. Cubre el
separador `--`, la ejecución en paralelo entre módulos y en orden dentro de uno, la espera
por un recurso compartido (el directorio de trabajo), el orden de las respuestas y las
acciones pedidas desde las ventanas.
"""
import asyncio

import pytest
from test_orders import Rig, settle

from jarvis_assistant import main as main_module
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    WORKDIR,
    ActionResult,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.speaker.phrases import PHRASES

S = AssistantState


def first(phrase_id: str, **params) -> str:
    """La primera variante de la frase: cada prueba empieza con la rotación a cero."""
    return PHRASES[phrase_id][0].format(**params)


class Other:
    """Segundo módulo de pruebas: acciones lentas con su propia puerta."""

    name = "otra"
    title = "Otra"

    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started: list[str] = []
        self.target = None  # carpeta a la que cambia «mueve»

    def intents(self):
        return (
            IntentSpec("aguardar", ("aguarda {algo}",), (Slot("algo", SlotType.TEXT),)),
            IntentSpec("mover", ("mueve",), writes=frozenset({WORKDIR})),
            IntentSpec("informar", ("informa",)),
        )

    async def execute(self, action, params, ctx):
        self.started.append(str(params.get("algo", action)))
        if action == "informar":
            await ctx.say(Phrase("busqueda.limitada"))
            return ActionResult("completado", Phrase("busqueda.instalar"))
        await self.gate.wait()
        if action == "mover":
            ctx.workdir.change(self.target)
            return ActionResult("completado")
        return ActionResult("completado", Phrase("comandos.tiempo"))


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    other = Other()
    monkeypatch.setattr(
        main_module, "ACTION_MODULES", [*main_module.ACTION_MODULES, lambda: other]
    )
    rig = Rig(tmp_path, monkeypatch)
    rig.other = other
    queue: list[events.OrderQueueChanged] = []
    rig.app.bus.subscribe(events.OrderQueueChanged, queue.append)
    rig.queue = queue
    await rig.start()
    await rig.open_session()
    queue.clear()
    yield rig
    await rig.stop()


def received(rig) -> list[tuple[str, bool]]:
    return [(e.text, e.recognized) for e in rig.of(events.CommandReceived)]


# --- Separador y reparto ---------------------------------------------------------------------


async def test_las_ordenes_de_modulos_distintos_se_ejecutan_a_la_vez(rig):
    await rig.write("espera uno -- aguarda dos")
    assert rig.probe.started == ["uno"] and rig.other.started == ["dos"]
    assert received(rig) == [("espera uno", True), ("aguarda dos", True)]
    assert [t[0] for t in rig.tasks()] == ["prueba", "otra"]
    assert rig.queue == []  # ninguna ha tenido que esperar


async def test_las_ordenes_del_mismo_modulo_se_ejecutan_en_el_orden_escrito(rig):
    await rig.write("espera uno -- espera dos -- espera tres")
    assert rig.probe.started == ["uno"]
    assert rig.queue[-1].waiting == ("espera dos", "espera tres")
    assert len(rig.tasks()) == 1  # las que esperan aún no son tareas
    rig.probe.gate.set()
    await settle()
    assert rig.probe.started == ["uno", "dos", "tres"]
    assert rig.queue[-1].waiting == ()


async def test_una_orden_escrita_con_otra_en_curso_no_se_descarta(rig):
    await rig.write("espera uno")
    await rig.write("espera dos")
    await rig.write("espera tres")
    assert rig.probe.started == ["uno"]
    assert rig.queue[-1].waiting == ("espera dos", "espera tres")
    rig.probe.gate.set()
    await settle()
    assert rig.probe.started == ["uno", "dos", "tres"]


async def test_una_parte_no_reconocida_no_detiene_a_las_demas(rig):
    await rig.write("lista -- qué tiempo hace hoy -- dónde estoy")
    assert received(rig) == [
        ("lista", True), ("qué tiempo hace hoy", False), ("dónde estoy", True),
    ]  # fmt: skip
    await rig.advance(1.0)
    await rig.advance(1.0)
    assert [t[2] for t in rig.tasks()].count("completado") == 2


async def test_el_separador_pegado_tambien_separa_y_una_opcion_de_un_programa_no(rig):
    await rig.write("espera uno--aguarda dos")
    assert rig.probe.started == ["uno"] and rig.other.started == ["dos"]
    await rig.write("aguarda con --prisa")
    rig.other.gate.set()
    await settle()
    assert rig.other.started == ["dos", "con --prisa"]


async def test_en_un_mensaje_con_varias_ordenes_las_frases_de_control_no_valen(rig):
    await rig.write("espera uno -- gracias jarvis")
    assert rig.state is S.LISTENING_COMMAND
    assert received(rig) == [("espera uno", True), ("gracias jarvis", False)]
    assert rig.probe.started == ["uno"]


async def test_en_reposo_un_mensaje_con_varias_ordenes_despierta_y_las_ejecuta(rig):
    await rig.order("gracias jarvis")
    assert rig.state is S.IDLE
    await rig.write("espera uno -- aguarda dos")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.probe.started == ["uno"] and rig.other.started == ["dos"]


async def test_en_dormido_un_mensaje_con_varias_ordenes_no_tiene_efecto(rig):
    await rig.order("buenas noches jarvis")
    await rig.advance(1.0)
    rig.events.clear()
    await rig.write("espera uno -- aguarda dos")
    assert rig.state is S.DORMIDO
    assert rig.probe.started == [] and received(rig) == []


# --- Recursos compartidos: el directorio de trabajo ------------------------------------------


async def test_una_orden_ve_el_directorio_que_deja_la_anterior_aunque_sea_de_otro_modulo(rig):
    await rig.write("ve a proyectos -- abre esta carpeta")
    await rig.advance(1.0)
    await rig.advance(1.0)
    assert ("open_folder", (rig.home / "Proyectos",)) in rig.platform.calls


async def test_una_ruta_se_resuelve_cuando_le_llega_el_turno_no_al_escribirla(rig):
    await rig.write("ve a proyectos -- ve a jarvis")
    assert rig.app.workdir.path == rig.home / "Proyectos" / "Jarvis"


async def test_quien_usa_el_directorio_espera_a_quien_lo_cambia_y_el_resto_no(rig):
    rig.other.target = rig.home / "Docs"
    await rig.write("mueve -- abre esta carpeta -- espera uno")
    assert rig.other.started == ["mover"]
    assert rig.probe.started == ["uno"]  # no depende del directorio: va en paralelo
    assert rig.queue[-1].waiting == ("abre esta carpeta",)
    assert not any(call[0] == "open_folder" for call in rig.platform.calls)
    rig.other.gate.set()
    await settle()
    assert ("open_folder", (rig.home / "Docs",)) in rig.platform.calls


async def test_traer_al_frente_encuentra_lo_que_abre_la_orden_anterior(rig):
    await rig.write("abre github -- trae al frente github")
    await rig.advance(1.0)
    assert [t[1] for t in rig.tasks() if t[2] != "pendiente"] == [
        "abrir GitHub", "traer al frente GitHub",
    ]  # fmt: skip


# --- Cola de voz -----------------------------------------------------------------------------


async def test_las_respuestas_se_dicen_en_el_orden_en_que_terminan_y_sin_solaparse(rig):
    await rig.write("espera uno -- aguarda dos")
    rig.other.gate.set()  # la segunda orden termina antes
    await settle()
    rig.probe.gate.set()
    await settle()
    assert rig.spoken() == [first("comandos.tiempo")]  # la primera respuesta sigue sonando
    await rig.advance(1.0)
    assert rig.spoken() == [first("comandos.tiempo"), first("comandos.consola")]
    await rig.advance(1.0)
    voice = [type(e).__name__ for e in rig.of(events.SpeechStarted | events.SpeechFinished)]
    assert voice == ["SpeechStarted", "SpeechFinished", "SpeechStarted", "SpeechFinished"]
    assert rig.of(events.AssistantActivityChanged)[-1].activity is events.Activity.ESCUCHANDO


async def test_las_frases_de_una_tarea_se_dicen_seguidas(rig):
    rig.other.gate.set()
    await rig.write("informa -- espera uno")
    rig.probe.gate.set()
    for _ in range(3):
        await rig.advance(1.0)
    assert rig.spoken() == [
        first("busqueda.limitada"), first("busqueda.instalar"), first("comandos.consola"),
    ]  # fmt: skip


async def test_el_boton_de_silencio_calla_tambien_las_respuestas_en_espera(rig):
    rig.probe.gate.set()
    rig.other.gate.set()
    await rig.write("espera uno -- aguarda dos")
    assert len(rig.spoken()) == 1
    rig.app.bus.publish(events.SilenceRequested())
    await settle()
    await rig.advance(1.0)
    assert len(rig.spoken()) == 1
    assert rig.of(events.SpeechFinished)[-1].interrupted


async def test_cancelar_detiene_las_ordenes_en_curso_y_en_espera_y_lo_dice_una_vez(rig):
    await rig.write("espera uno -- espera dos -- aguarda tres")
    await rig.write("cancelar")
    assert rig.probe.started == ["uno"] and rig.other.started == ["tres"]
    finished = [t for t in rig.tasks() if t[2] == "error"]
    assert sorted(t[0] for t in finished) == ["otra", "prueba"]
    assert rig.queue[-1].waiting == ()
    assert rig.spoken() == [first("general.cancelado")]
    rig.probe.gate.set()
    await rig.advance(1.0)
    assert rig.probe.started == ["uno"]  # la que esperaba no llega a empezar


async def test_la_cuenta_de_inactividad_empieza_cuando_termina_la_ultima_respuesta(rig):
    limit = rig.app.config.settings.input.inactivity_to_idle_seconds
    rig.probe.gate.set()
    rig.other.gate.set()
    await rig.write("espera uno -- aguarda dos")
    await rig.advance(1.0)
    assert rig.clock.pending.count(limit) == 0  # aún suena la segunda respuesta
    await rig.advance(1.0)
    assert limit in rig.clock.pending
    await rig.advance(limit)
    assert rig.state is S.IDLE


# --- Acciones pedidas desde las ventanas ------------------------------------------------------


async def test_una_accion_pedida_desde_una_ventana_entra_en_la_cola_como_una_orden(rig):
    rig.app.bus.publish(events.ActionRequested("comandos", "cd", {"ruta": rig.home / "Docs"}))
    await settle()
    assert rig.app.workdir.path == rig.home / "Docs"
    assert rig.tasks()[-1] == ("comandos", f"cd {rig.home / 'Docs'}", "completado")
    await rig.advance(1.0)
    # Se responde como si la orden se hubiera escrito.
    assert rig.spoken() == [first("comandos.cd", carpeta="Docs")]


async def test_una_accion_de_una_ventana_que_falla_si_se_dice(rig):
    rig.app.bus.publish(events.ActionRequested("comandos", "cd", {"ruta": rig.home / "Fotos"}))
    await settle()
    assert rig.tasks()[-1][2] == "error"
    assert rig.spoken() == [first("ruta.no_existe", nombre="Fotos")]


async def test_la_ayuda_pedida_desde_su_ventana_se_responde_como_una_orden(rig):
    rig.app.bus.publish(events.ActionRequested("nucleo", "ayuda"))
    await settle()
    assert rig.of(events.HelpShown) and rig.of(events.PanelActivated)[-1].panel == "ayuda"
    assert rig.spoken() == [first("general.ayuda")]


async def test_el_catalogo_se_publica_al_abrir_la_sesion_para_el_acceso_rapido(rig):
    targets: list[events.LaunchTargetsChanged] = []
    rig.app.bus.subscribe(events.LaunchTargetsChanged, targets.append)
    await rig.order("buenas noches jarvis")
    await rig.advance(1.0)
    await rig.open_session()
    assert [(t.name, t.kind) for t in targets[-1].targets] == [("GitHub", "pagina")]


async def test_una_accion_que_no_existe_se_ignora(rig):
    rig.app.bus.publish(events.ActionRequested("comandos", "formatear"))
    rig.app.bus.publish(events.ActionRequested("nadie", "cd"))
    await settle()
    assert rig.tasks() == []
    assert not rig.task.done()
