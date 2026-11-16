"""Órdenes sin diálogo de principio a fin, con dobles (fase 3).

El grafo es el de `build_app`, con los módulos reales y un módulo de pruebas. El usuario
escribe: cada orden entra como el evento `TextSubmitted` que publica la caja de texto.
Cubre `run_task` (T-3.1), los avisos (T-3.6), las intenciones del núcleo (T-3.10) y los casos
de uso CU-01, CU-02, CU-06, CU-07 y CU-08.
"""
import asyncio
import dataclasses
from concurrent.futures import Executor, Future

import pytest

from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from fakes.voice import FakePlayer, FakeSynthesizer
from jarvis_assistant import main as main_module
from jarvis_assistant.config import (
    Catalog,
    Config,
    ConfigError,
    InputSettings,
    PageEntry,
    Settings,
    UserSettings,
)
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import ActionResult, IntentSpec, Phrase, Slot, SlotType
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.notices import Notice
from jarvis_assistant.core.repositories import ActivityRepository, SessionRepository
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.main import Adapters, build_app
from jarvis_assistant.os_adapters.base import DiscoveredApp, SearchOutcome
from jarvis_assistant.speaker.phrases import PHRASES, render

S = AssistantState
RECORDED = (
    events.AssistantActivityChanged, events.CommandReceived, events.SpeechStarted,
    events.SpeechFinished, events.TaskUpdated, events.PanelActivated, events.ListeningResumed,
    events.RestEntered, events.SessionClosed, events.WorkdirChanged, events.DirectoryListed,
    events.DirectoryTreeBuilt, events.CommandOutputAppended, events.OpenedItemsChanged,
    events.SearchResultsReady, events.HistoryShown, events.SessionActivitiesShown,
    events.HelpShown, events.ConfigReloadFailed, events.ShowScreenRequested,
    events.WindowAsideRequested,
)  # fmt: skip

CONFIG = Config(catalog=Catalog(pages=(PageEntry("GitHub", "https://github.com"),)))


def said(phrase_id: str, **params) -> str:
    return render(Phrase(phrase_id, params))


async def settle() -> None:
    for _ in range(40):
        await asyncio.sleep(0)


class InlineExecutor(Executor):
    """Sintetiza en el acto, sin hilo: las pruebas no dependen de tiempos reales."""

    def submit(self, fn, /, *args, **kwargs):
        future: Future = Future()
        future.set_result(fn(*args, **kwargs))
        return future


class Probe:
    """Módulo de pruebas: acciones lentas, que fallan y que avisan."""

    name = "prueba"
    title = "Prueba"

    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started: list[str] = []

    def intents(self):
        return (
            IntentSpec("esperar", ("espera {algo}",), (Slot("algo", SlotType.TEXT),),
                       "Esperar", "Espera algo", panel="prueba"),
            IntentSpec("romper", ("rompe",)),
            IntentSpec("fallar", ("falla",)),
            IntentSpec("avisar", ("avisa",)),
            IntentSpec("recordar", ("recuerda",)),
        )  # fmt: skip

    async def execute(self, action, params, ctx):
        self.started.append(str(params.get("algo", action)))
        if action == "esperar":
            await self.gate.wait()
            return ActionResult("completado", Phrase("comandos.consola"), description="hecho")
        if action == "romper":
            raise RuntimeError("el módulo se ha roto")
        if action == "fallar":
            return ActionResult("error", Phrase("comandos.ocupado"))
        notice = Notice(Phrase("comandos.tiempo"), panel="prueba", reminder=action == "recordar")
        ctx.notify(notice)
        return ActionResult("completado")


class FakeStream:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()

    def feed(self, *lines: bytes) -> None:
        for line in lines:
            self._queue.put_nowait(line)

    async def readline(self) -> bytes:
        return await self._queue.get()


class FakeProcess:
    pid = 4321

    def __init__(self) -> None:
        self.stdout = FakeStream()
        self.stderr = FakeStream()
        self._code: asyncio.Future[int] = asyncio.get_running_loop().create_future()

    def finish(self, code: int) -> None:
        self.stdout.feed(b"")
        self.stderr.feed(b"")
        if not self._code.done():
            self._code.set_result(code)

    async def wait(self) -> int:
        return await self._code


class Rig:
    def __init__(self, tmp_path, monkeypatch, config: Config = CONFIG, reload=None) -> None:
        self.clock = FakeClock()
        self.database = Database(":memory:")
        self.database.migrate()
        self.player = FakePlayer(self.clock)
        self.platform = FakePlatform(tmp_path)
        self.platform.discovered = [DiscoveredApp("Calculadora", "calc.lnk")]
        self.home = tmp_path / "usuario"
        for folder in ("Proyectos/Jarvis", "Docs"):
            (self.home / folder).mkdir(parents=True)
        (self.home / "notas.txt").write_text("x")
        self.probe = Probe()
        monkeypatch.setattr(
            main_module, "ACTION_MODULES", [*main_module.ACTION_MODULES, lambda: self.probe]
        )
        adapters = Adapters(
            platform=self.platform, clock=self.clock, database=self.database,
            synthesizer=FakeSynthesizer(), player=self.player,
        )  # fmt: skip
        self.app = build_app(
            config, adapters, home=self.home, reload_config=reload,
            windows=("Comandos", "Búsqueda"),
        )  # fmt: skip
        self.app.speaker._executor.shutdown()
        self.app.speaker._executor = InlineExecutor()
        self.events: list[events.Event] = []
        for event_type in RECORDED:
            self.app.bus.subscribe(event_type, self.events.append)
        self.activities = ActivityRepository(self.database)
        self.sessions = SessionRepository(self.database)
        self.processes: list[FakeProcess] = []
        self.killed: list[int] = []
        runner = self.app.orchestrator.modules["comandos"]
        runner._launch = self._launch
        runner._kill_tree = self._kill
        self.task: asyncio.Task | None = None

    async def _launch(self, executable, args, cwd):
        self.processes.append(FakeProcess())
        return self.processes[-1]

    def _kill(self, pid: int) -> None:
        self.killed.append(pid)
        for process in self.processes:
            process.finish(-9)

    async def start(self) -> None:
        await self.app.speaker.preload()
        self.task = asyncio.ensure_future(self.app.orchestrator.run())
        await settle()

    async def stop(self) -> None:
        if self.task is not None and not self.task.done():
            self.task.cancel()
        self.app.speaker.close()
        self.database.close()

    async def advance(self, seconds: float) -> None:
        steps = max(1, round(seconds / 0.25))
        for _ in range(steps):
            self.clock.advance(seconds / steps)
            await settle()

    async def write(self, text: str) -> None:
        self.app.bus.publish(events.TextSubmitted(text))
        await settle()

    async def until(self, condition) -> None:
        """Espera a algo que ocurre en un hilo real (árbol, búsqueda, descubrimiento)."""
        for _ in range(400):
            if condition():
                return
            await asyncio.sleep(0.005)
            await settle()
        raise AssertionError("La condición no se ha cumplido a tiempo")

    async def open_session(self) -> None:
        await self.write("Hey Jarvis")
        await self.until(lambda: self.app.orchestrator.modules["apertura"]._discovery.done())
        await self.advance(1.0)
        self.events.clear()

    async def order(self, text: str) -> None:
        """Escribe una orden y deja que termine su respuesta."""
        await self.write(text)
        await self.advance(1.0)

    @property
    def state(self) -> AssistantState:
        return self.app.machine.state

    def of(self, kind: type) -> list:
        return [event for event in self.events if isinstance(event, kind)]

    def spoken(self) -> list[str]:
        return [event.text for event in self.of(events.SpeechStarted)]

    def tasks(self) -> list[tuple[str, str, str]]:
        return [(t.module, t.description, t.status) for t in self.of(events.TaskUpdated)]

    def activity_rows(self):
        (session,) = self.sessions.find_open()
        return [(a.module, a.description, a.status) for a in self.activities.of_session(session.id)]


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    rig = Rig(tmp_path, monkeypatch)
    await rig.start()
    await rig.open_session()
    yield rig
    await rig.stop()


# --- T-3.1. run_task -------------------------------------------------------------------------


async def test_una_tarea_recorre_pendiente_y_completado(rig):
    await rig.write("espera un poco")
    assert rig.tasks() == [("prueba", "espera un poco", "pendiente")]
    assert rig.of(events.PanelActivated) == [events.PanelActivated("prueba")]
    assert rig.of(events.AssistantActivityChanged)[-1].activity is Activity.PROCESANDO
    assert rig.activity_rows() == [("prueba", "espera un poco", "pendiente")]
    rig.probe.gate.set()
    await settle()
    # El módulo sustituye la descripción; la respuesta se dice al terminar.
    assert rig.tasks()[-1] == ("prueba", "hecho", "completado")
    assert rig.activity_rows() == [("prueba", "hecho", "completado")]
    assert rig.spoken() == [PHRASES["comandos.consola"][0]]
    assert rig.of(events.AssistantActivityChanged)[-1].activity is Activity.HABLANDO
    await rig.advance(1.0)
    assert rig.of(events.AssistantActivityChanged)[-1].activity is Activity.ESCUCHANDO
    updates = rig.of(events.TaskUpdated)
    assert len({update.task_id for update in updates}) == 1
    assert updates[-1].detail is None and updates[-1].parent_id is None


async def test_una_tarea_que_termina_en_error_muestra_su_motivo(rig):
    await rig.order("falla")
    assert rig.tasks() == [("prueba", "falla", "pendiente"), ("prueba", "falla", "error")]
    assert rig.of(events.TaskUpdated)[-1].detail == PHRASES["comandos.ocupado"][0]
    assert rig.spoken() == [PHRASES["comandos.ocupado"][0]]
    assert rig.activity_rows() == [("prueba", "falla", "error")]


async def test_un_modulo_que_lanza_una_excepcion_no_rompe_nada(rig):
    """RNF-23."""
    await rig.order("rompe")
    assert rig.tasks()[-1] == ("prueba", "rompe", "error")
    assert rig.spoken() == [PHRASES["general.error"][0]]
    assert rig.state is S.LISTENING_COMMAND
    assert not rig.task.done()
    rig.events.clear()
    await rig.order("dónde estoy")  # el asistente sigue atendiendo órdenes
    assert rig.tasks()[-1][2] == "completado"


async def test_una_entidad_que_no_se_resuelve_crea_la_tarea_en_error(rig):
    await rig.order("ve a fotos")
    assert rig.tasks() == [
        ("comandos", "ve a fotos", "pendiente"), ("comandos", "ve a fotos", "error"),
    ]  # fmt: skip
    assert rig.spoken() == [said("ruta.no_existe", nombre="fotos")]
    assert rig.app.workdir.path == rig.home


async def test_una_orden_no_reconocida_no_crea_ninguna_tarea(rig):
    await rig.order("qué tiempo hace hoy")
    assert rig.tasks() == [] and rig.spoken() == []
    assert rig.of(events.CommandReceived) == [events.CommandReceived("qué tiempo hace hoy", False)]


# --- Cola de órdenes y frases de control (RN-52) ---------------------------------------------


async def test_las_ordenes_escritas_durante_otra_esperan_en_la_cola(rig):
    await rig.write("espera uno")
    await rig.write("espera dos")
    await rig.write("espera tres")
    assert rig.probe.started == ["uno"]
    assert [e.text for e in rig.of(events.CommandReceived)] == [
        "espera uno", "espera dos", "espera tres",
    ]  # fmt: skip
    rig.probe.gate.set()
    await settle()
    assert rig.probe.started == ["uno", "dos", "tres"]  # ninguna se descarta


async def test_cancelar_detiene_la_orden_en_curso(rig):
    await rig.write("espera uno")
    await rig.write("espera dos")
    await rig.write("cancelar")
    assert rig.tasks()[-1] == ("prueba", "espera uno", "error")
    assert rig.of(events.TaskUpdated)[-1].detail == "cancelada"
    assert rig.spoken() == [PHRASES["general.cancelado"][0]]
    await rig.advance(1.0)
    assert rig.probe.started == ["uno"]  # la orden en espera también se descarta
    assert rig.state is S.LISTENING_COMMAND


async def test_cancelar_sin_nada_en_curso_no_hace_nada(rig):
    await rig.write("cancelar")
    assert rig.spoken() == [] and rig.tasks() == []


async def test_gracias_jarvis_cancela_el_turno_y_pasa_a_reposo(rig):
    await rig.write("espera uno")
    await rig.write("gracias jarvis")
    assert rig.state is S.IDLE
    assert rig.tasks()[-1] == ("prueba", "espera uno", "error")
    assert rig.spoken() == [PHRASES["ciclo.reposo"][0]]


async def test_buenas_noches_con_una_orden_en_curso_cierra_la_sesion(rig):
    await rig.write("espera uno")
    (session,) = rig.sessions.find_open()
    await rig.write("buenas noches jarvis")
    assert rig.state is S.DORMIDO
    assert rig.tasks()[-1] == ("prueba", "espera uno", "error")
    assert [a.status for a in rig.activities.of_session(session.id)] == ["error"]


async def test_la_cuenta_de_inactividad_no_corre_durante_el_turno(tmp_path, monkeypatch):
    settings = Settings(input=InputSettings(inactivity_to_idle_seconds=5))
    rig = Rig(tmp_path, monkeypatch, dataclasses.replace(CONFIG, settings=settings))
    await rig.start()
    await rig.open_session()
    await rig.write("espera uno")
    await rig.advance(20)
    assert rig.state is S.LISTENING_COMMAND
    rig.probe.gate.set()
    await rig.advance(1.0)  # la respuesta
    await rig.advance(4.5)
    assert rig.state is S.LISTENING_COMMAND
    await rig.advance(1.0)  # 5 s desde el fin de la respuesta
    assert rig.state is S.IDLE
    await rig.stop()


# --- Interrupción de la locución (RF-70, RF-85) ----------------------------------------------


async def test_hey_jarvis_interrumpe_la_respuesta(rig):
    await rig.write("dónde estoy")
    assert rig.app.speaker.speaking
    await rig.write("Hey Jarvis")
    assert not rig.app.speaker.speaking
    assert rig.of(events.SpeechFinished) == [events.SpeechFinished(interrupted=True)]
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == [said("comandos.pwd", ruta=str(rig.home))]  # sin «Le escucho»


async def test_el_boton_de_silencio_calla_la_respuesta(rig):
    await rig.write("dónde estoy")
    rig.app.bus.publish(events.SilenceRequested())
    await settle()
    assert rig.of(events.SpeechFinished) == [events.SpeechFinished(interrupted=True)]
    rig.events.clear()
    await rig.order("lista")  # sigue atendiendo
    assert rig.tasks()[-1][2] == "completado"


async def test_cancelar_durante_la_respuesta_la_corta(rig):
    await rig.write("dónde estoy")
    await rig.write("cancelar")
    assert rig.of(events.SpeechFinished)[0] == events.SpeechFinished(interrupted=True)
    assert rig.tasks()[-1][2] == "completado"  # la acción ya había terminado
    assert rig.spoken()[-1] == PHRASES["general.cancelado"][0]


# --- Intenciones del núcleo (RF-92, RF-94) ---------------------------------------------------


async def test_ayuda_muestra_las_ordenes_del_registro(rig):
    await rig.order("ayuda")
    (shown,) = rig.of(events.HelpShown)
    assert [group.module for group in shown.groups] == [
        "sesion", "comandos", "apertura", "busqueda", "creacion", "historial", "recordatorio",
        "protocolos", "prueba", "nucleo",
    ]  # fmt: skip
    assert shown.groups == rig.app.router.help()
    assert rig.of(events.PanelActivated) == [events.PanelActivated("ayuda")]
    assert rig.spoken() == [PHRASES["general.ayuda"][0]]
    assert rig.tasks() == []  # no es una tarea de ningún módulo


async def test_repite_la_ultima_respuesta(rig):
    await rig.order("repite")
    assert rig.spoken() == [PHRASES["general.nada_que_repetir"][0]]
    rig.events.clear()
    await rig.order("dónde estoy")
    await rig.order("repite")
    pwd = said("comandos.pwd", ruta=str(rig.home))
    assert rig.spoken() == [pwd, pwd]


def modules(rig) -> str:
    """Los módulos que nombra «preséntate»: los del registro, con «y» antes del último."""
    *rest, last = (
        group.title.lower() for group in rig.app.router.help() if group.module != "nucleo"
    )
    return f"{', '.join(rest)} y {last}"


async def test_presentate_sin_nombre_configurado(rig):
    await rig.order("preséntate")
    await rig.advance(5.0)
    spoken = rig.spoken()
    assert spoken == [said("presentacion.anonima", modulos=modules(rig))]  # una sola frase
    assert "comandos, aperturas, búsqueda" in spoken[0]
    assert "Hey" not in spoken[0]  # nada en inglés: la voz es española
    assert rig.tasks() == []  # no es una tarea de ningún módulo


async def test_presentate_con_el_nombre_de_la_configuracion(tmp_path, monkeypatch):
    settings = Settings(user=UserSettings(name="Jane Doe"))
    rig = Rig(tmp_path, monkeypatch, dataclasses.replace(CONFIG, settings=settings))
    await rig.start()
    await rig.open_session()
    await rig.order("presentate")
    await rig.advance(5.0)
    assert rig.spoken() == [said("presentacion", nombre="Jane Doe", modulos=modules(rig))]
    await rig.stop()


async def test_mostrar_y_ocultar_la_pantalla_sin_voz(rig):
    await rig.order("oculta la pantalla")
    await rig.order("muestra la pantalla")
    assert rig.of(events.ShowScreenRequested) == [
        events.ShowScreenRequested(visible=False), events.ShowScreenRequested(visible=True),
    ]  # fmt: skip
    assert rig.spoken() == []


async def test_apartar_ventanas_sin_voz(rig):
    await rig.order("aparta comandos")
    await rig.order("aparta módulos")
    assert rig.of(events.WindowAsideRequested) == [
        events.WindowAsideRequested("Comandos"), events.WindowAsideRequested(None),
    ]  # fmt: skip
    assert rig.spoken() == []


async def test_desapartar_ventanas_sin_voz(rig):
    await rig.order("desaparta búsqueda")
    await rig.order("desaparta módulos")
    assert rig.of(events.WindowAsideRequested) == [
        events.WindowAsideRequested("Búsqueda", aside=False),
        events.WindowAsideRequested(None, aside=False),
    ]  # fmt: skip
    assert rig.spoken() == []


async def test_apartar_una_ventana_que_no_existe_lo_dice(rig):
    await rig.order("aparta el calendario")
    assert rig.of(events.WindowAsideRequested) == []
    assert rig.spoken() == [said("entidad.no_encontrado", nombre="el calendario")]


# --- T-3.6. Avisos (RN-39) -------------------------------------------------------------------


async def test_un_aviso_se_entrega_cuando_el_asistente_queda_libre(rig):
    await rig.write("avisa")
    await settle()
    assert rig.spoken() == [PHRASES["comandos.tiempo"][0]]
    assert rig.of(events.PanelActivated)[-1] == events.PanelActivated("prueba")


async def test_un_aviso_espera_a_que_termine_la_locucion(rig):
    await rig.write("dónde estoy")
    rig.app.orchestrator._notify(Notice(Phrase("comandos.tiempo")))
    await settle()
    assert len(rig.spoken()) == 1  # la respuesta sigue sonando: el aviso espera
    await rig.advance(1.0)
    assert rig.spoken()[-1] == PHRASES["comandos.tiempo"][0]
    assert rig.of(events.SpeechFinished)[0] == events.SpeechFinished(interrupted=False)


async def test_en_reposo_un_aviso_normal_espera_y_uno_de_recordatorio_despierta(rig):
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.events.clear()
    rig.app.orchestrator._notify(Notice(Phrase("comandos.tiempo")))
    await settle()
    assert rig.state is S.IDLE and rig.spoken() == []
    rig.app.orchestrator._notify(Notice(Phrase("comandos.ocupado"), reminder=True))
    await settle()
    assert rig.state is S.LISTENING_COMMAND
    assert rig.of(events.ListeningResumed) == [events.ListeningResumed(silent=True)]
    assert rig.spoken() == [PHRASES["comandos.ocupado"][0]]  # sin «Le escucho»
    await rig.advance(1.0)
    assert rig.spoken()[-1] == PHRASES["comandos.tiempo"][0]  # ya en escucha, el que esperaba


async def test_al_cerrar_la_sesion_los_avisos_se_descartan(rig):
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.app.orchestrator._notify(Notice(Phrase("comandos.tiempo")))
    await rig.write("buenas noches jarvis")
    await rig.advance(1.0)
    await rig.open_session()
    await rig.advance(2.0)
    assert PHRASES["comandos.tiempo"][0] not in rig.spoken()


# --- CU-02. Árbol; comandos nativos ----------------------------------------------------------


async def test_cu02_arbol_del_directorio_de_trabajo(rig):
    await rig.write("árbol")
    await rig.until(lambda: rig.of(events.DirectoryTreeBuilt))
    await rig.advance(1.0)
    (tree,) = rig.of(events.DirectoryTreeBuilt)
    assert tree.root == str(rig.home)
    assert [(node.name, node.depth) for node in tree.nodes] == [
        ("Docs", 1), ("Proyectos", 1), ("Jarvis", 2), ("notas.txt", 1),
    ]  # fmt: skip
    assert rig.spoken() == [said(
        "comandos.arbol", carpeta=rig.home.name, carpetas="3 carpetas", archivos="1 archivo"
    )]
    assert rig.tasks()[-1] == ("comandos", f"árbol de {rig.home}", "completado")
    assert rig.of(events.PanelActivated) == [events.PanelActivated("comandos")]


async def test_cu02_a2_ruta_invalida(rig):
    await rig.order("árbol de fotos")
    assert rig.of(events.DirectoryTreeBuilt) == []
    assert rig.spoken() == [said("ruta.no_existe", nombre="fotos")]
    assert rig.tasks()[-1][2] == "error"


async def test_cd_cambia_el_directorio_para_las_ordenes_siguientes(rig):
    await rig.order("ve a proyectos barra jarvis")
    assert rig.app.workdir.path == rig.home / "Proyectos" / "Jarvis"
    assert rig.spoken() == [said("comandos.cd", carpeta="Jarvis")]
    await rig.order("ve atrás")
    assert rig.app.workdir.path == rig.home / "Proyectos"
    await rig.order("lista")
    assert rig.of(events.DirectoryListed)[-1].path == str(rig.home / "Proyectos")
    # Pasar a reposo y volver no lo cambia; una sesión nueva vuelve a la carpeta personal.
    await rig.order("gracias jarvis")
    await rig.order("hey jarvis")
    assert rig.app.workdir.path == rig.home / "Proyectos"
    await rig.order("buenas noches jarvis")
    await rig.open_session()
    assert rig.app.workdir.path == rig.home


# --- CU-06. Binario externo ------------------------------------------------------------------


async def test_cu06_flujo_principal(rig):
    await rig.write("ejecuta git status")
    assert rig.tasks() == [
        ("comandos", "ejecuta git status", "pendiente"), ("comandos", "git status", "pendiente"),
    ]  # fmt: skip
    assert rig.spoken() == [said("comandos.ejecutando", comando="git status")]
    await rig.advance(1.0)
    # Paso 3: sigue atendiendo órdenes mientras el programa se ejecuta (RNF-07).
    await rig.order("dónde estoy")
    assert rig.tasks()[-1] == ("comandos", "dónde estoy", "completado")
    process = rig.processes[0]
    process.stdout.feed(b"On branch main\n")
    await rig.advance(0.25)
    assert rig.of(events.CommandOutputAppended)[-1].lines == ("On branch main",)
    process.finish(0)
    await settle()
    assert rig.tasks()[-1] == ("comandos", "git status", "completado")
    assert rig.spoken()[-1] == said("comandos.ok", comando="git status")  # el aviso
    assert rig.activity_rows()[0] == ("comandos", "git status", "completado")


async def test_cu06_a1_codigo_distinto_de_cero(rig):
    await rig.order("ejecuta git status")
    rig.processes[0].finish(2)
    await settle()
    assert rig.tasks()[-1] == ("comandos", "git status", "error")
    assert rig.of(events.TaskUpdated)[-1].detail == said("comandos.fallo", comando="git status")
    assert rig.spoken()[-1] == said("comandos.fallo", comando="git status")


async def test_cu06_a2_binario_no_permitido(rig):
    await rig.order("ejecuta rm -rf algo")
    assert rig.spoken() == [PHRASES["comandos.no_permitido"][0]]
    assert rig.tasks()[-1][2] == "error"
    assert rig.processes == []


async def test_cu06_a5_ya_hay_un_binario_en_ejecucion(rig):
    await rig.order("ejecuta git status")
    await rig.order("ejecuta git log")
    assert rig.spoken()[-1] == PHRASES["comandos.ocupado"][0]
    assert len(rig.processes) == 1


async def test_cu06_a6_cancelar_termina_el_programa(rig):
    await rig.order("ejecuta git status")
    await rig.write("cancelar")
    assert rig.killed == [4321]
    assert rig.tasks()[-1] == ("comandos", "git status", "error")
    assert rig.of(events.TaskUpdated)[-1].detail == "cancelada"
    assert rig.spoken()[-1] == PHRASES["general.cancelado"][0]


async def test_cu06_a6_el_cierre_de_sesion_termina_el_programa(rig):
    await rig.order("ejecuta git status")
    (session,) = rig.sessions.find_open()
    await rig.write("buenas noches jarvis")
    assert rig.killed == [4321]
    assert rig.of(events.TaskUpdated)[-1].detail == "sesión cerrada"
    assert [a.status for a in rig.activities.of_session(session.id)] == ["error"]
    await rig.advance(2.0)
    assert said("comandos.fallo", comando="git status") not in rig.spoken()


async def test_cu06_hey_jarvis_se_atiende_con_un_binario_en_ejecucion(rig):
    await rig.order("ejecuta git status")
    await rig.order("gracias jarvis")
    assert rig.state is S.IDLE
    await rig.order("hey jarvis")
    assert rig.state is S.LISTENING_COMMAND
    rig.processes[0].finish(0)
    await settle()
    assert rig.spoken()[-1] == said("comandos.ok", comando="git status")


# --- CU-01 y CU-07. Apertura -----------------------------------------------------------------


async def test_cu01_abre_una_carpeta(rig):
    await rig.order("abre la carpeta docs")
    assert rig.platform.calls[-2] == ("open_folder", (rig.home / "Docs",))
    assert rig.spoken() == [said("apertura.abriendo", nombre="Docs")]
    assert rig.tasks()[-1] == ("apertura", "abrir carpeta Docs", "completado")
    item = rig.of(events.OpenedItemsChanged)[-1].items[0]
    assert (item.title, item.kind, item.can_focus) == ("Docs", "carpeta", True)
    assert rig.app.workdir.path == rig.home  # el directorio de trabajo no cambia
    assert "bring_own_window_to_front" not in [name for name, _ in rig.platform.calls]


async def test_cu01_a1_y_a2_ruta_invalida(rig):
    await rig.order("abre la carpeta fotos")
    assert rig.spoken() == [said("ruta.no_existe", nombre="fotos")]
    await rig.order("abre la carpeta notas.txt")
    assert rig.spoken()[-1] == said("ruta.no_es_carpeta", nombre="notas.txt")
    assert rig.of(events.OpenedItemsChanged) == []


async def test_cu01_a3_el_gestor_no_se_puede_abrir(rig):
    rig.platform.launch_error = OSError("sin gestor")
    await rig.order("abre esta carpeta")
    assert rig.spoken() == [PHRASES["ruta.gestor_fallo"][0]]
    assert rig.tasks()[-1][2] == "error"


async def test_cu07_abre_una_pagina_y_una_aplicacion_y_las_trae_al_frente(rig):
    await rig.order("abre GitHub")
    await rig.order("abre la calculadora")
    assert rig.spoken() == [
        said("apertura.abriendo", nombre="GitHub"), said("apertura.abriendo", nombre="Calculadora"),
    ]  # fmt: skip
    items = rig.of(events.OpenedItemsChanged)[-1].items
    assert [(item.title, item.kind, item.can_focus) for item in items] == [
        ("GitHub", "pagina", True), ("Calculadora", "aplicacion", True),
    ]  # fmt: skip
    # Paso 6: con una orden y con el botón de la tarjeta.
    await rig.order("trae al frente github")
    rig.app.bus.publish(events.FocusItemRequested(items[1].id))
    await settle()
    assert [ref.title for ref in rig.platform.focused] == ["Edge", "Calculadora"]
    assert rig.tasks()[-1] == ("apertura", "traer al frente Calculadora", "completado")
    assert len(rig.spoken()) == 2  # traer al frente no dice nada


async def test_cu07_a1_nombre_no_encontrado(rig):
    await rig.order("abre el navegador")
    assert rig.spoken() == [said("entidad.no_encontrado", nombre="el navegador")]
    assert rig.tasks()[-1] == ("apertura", "abre el navegador", "error")


async def test_cu07_a5_la_ventana_ya_se_cerro(rig):
    await rig.order("abre GitHub")
    rig.platform._windows.clear()
    await rig.order("trae al frente github")
    assert rig.spoken()[-1] == PHRASES["apertura.ventana_cerrada"][0]
    assert not rig.of(events.OpenedItemsChanged)[-1].items[0].can_focus


async def test_al_cerrar_la_sesion_la_lista_de_aperturas_se_vacia(rig):
    await rig.order("abre GitHub")
    await rig.order("buenas noches jarvis")
    assert rig.of(events.OpenedItemsChanged)[-1].items == ()


# --- CU-08. Búsqueda -------------------------------------------------------------------------


async def test_cu08_busca_y_abre_un_resultado(rig):
    informe = rig.home / "Docs" / "informe.txt"
    informe.write_text("x")
    carpeta = rig.home / "Docs" / "informes"
    carpeta.mkdir()
    rig.platform.search_outcome = SearchOutcome((carpeta, informe), 2)
    await rig.order("busca informe")
    (shown,) = rig.of(events.SearchResultsReady)
    assert [(r.index, r.name) for r in shown.results] == [(1, "informe.txt"), (2, "informes")]
    assert (shown.query, shown.kind, shown.total, shown.limited) == ("informe", "ambos", 2, False)
    assert rig.spoken() == [said(
        "busqueda.varios", consulta="informe", n=2, nombre="informe.txt", carpeta="Docs"
    )]
    await rig.order("abre el resultado uno")
    assert rig.platform.calls[-1] == ("open_with_default", (informe,))
    assert rig.spoken()[-1] == said("apertura.abriendo", nombre="informe.txt")
    await rig.order("abre la carpeta del resultado uno")  # A4
    assert rig.platform.calls[-1] == ("open_folder", (informe.parent,))
    await rig.order("abre el resultado nueve")  # A5
    assert rig.spoken()[-1] == said("general.indice_invalido", n=9)
    informe.unlink()
    await rig.order("abre el resultado uno")  # A6
    assert rig.spoken()[-1] == PHRASES["busqueda.no_existe"][0]


async def test_cu08_a3_busqueda_limitada(rig):
    await rig.write("busca la carpeta jarvis")
    await rig.until(lambda: rig.of(events.SearchResultsReady))  # corre en un hilo
    await rig.advance(1.0)
    await rig.advance(1.0)
    await rig.advance(1.0)
    (shown,) = rig.of(events.SearchResultsReady)
    assert shown.limited and [r.name for r in shown.results] == ["Jarvis"]
    # Un solo resultado: tras los avisos, ofrece abrirlo.
    assert rig.spoken() == [
        said("busqueda.uno", consulta="jarvis", nombre="Jarvis", carpeta="Proyectos"),
        PHRASES["busqueda.limitada"][0], PHRASES["busqueda.instalar"][0],
        PHRASES["busqueda.ofrecer_abrir"][0],
    ]  # fmt: skip
    assert rig.state is S.AWAITING_CONFIRMATION
    await rig.order("sí")
    assert rig.platform.calls[-1][0] == "open_folder"
    assert rig.spoken()[-1] == said("apertura.abriendo", nombre="Jarvis")
    assert rig.tasks()[-1] == ("busqueda", "buscar jarvis", "completado")


# --- Historial (RF-08, RF-09, RF-10) ---------------------------------------------------------


async def test_el_historial_muestra_la_sesion_actual_y_sus_actividades(rig):
    await rig.order("dónde estoy")
    await rig.order("muestra el historial")
    (session,) = rig.sessions.find_open()
    (history,) = rig.of(events.HistoryShown)
    assert [s.id for s in history.sessions] == [session.id] and history.current_id == session.id
    assert rig.spoken()[-1] == said("historial.mostrado", sesiones="1 sesión")
    await rig.order("qué he hecho")
    (shown,) = rig.of(events.SessionActivitiesShown)
    assert [(a.module, a.status) for a in shown.activities] == [
        ("comandos", "completado"), ("historial", "completado"), ("historial", "pendiente"),
    ]  # fmt: skip


# --- RF-96. Recarga de la configuración ------------------------------------------------------


async def test_la_configuracion_se_relee_al_abrir_cada_sesion(tmp_path, monkeypatch):
    loads = []

    def reload(previous: Config):
        loads.append(previous)
        aliases = {"enseña": "lista"} if len(loads) > 1 else {}
        return dataclasses.replace(previous, aliases=aliases), []

    rig = Rig(tmp_path, monkeypatch, reload=reload)
    await rig.start()
    await rig.open_session()
    await rig.order("enseña")
    assert rig.tasks() == []
    await rig.order("buenas noches jarvis")
    await rig.open_session()
    await rig.order("enseña")  # el alias nuevo ya vale
    assert rig.tasks()[-1] == ("comandos", f"ls {rig.home}", "completado")
    assert len(loads) == 2
    await rig.stop()


async def test_un_archivo_invalido_conserva_el_anterior_y_se_avisa_tras_la_apertura(
    tmp_path, monkeypatch
):
    def reload(previous: Config):
        return previous, [
            ConfigError("catalog.toml", "pages[0].url", "debe empezar por http://"),
            ConfigError("catalog.toml", "apps", "debe ser una lista de tablas"),
            ConfigError("settings.toml", "antigua", "clave desconocida", warning=True),
        ]

    rig = Rig(tmp_path, monkeypatch, reload=reload)
    await rig.start()
    await rig.write("Hey Jarvis")
    assert [(e.file, e.reason) for e in rig.of(events.ConfigReloadFailed)] == [
        ("catalog.toml", "debe empezar por http://"),
        ("catalog.toml", "debe ser una lista de tablas"),
    ]
    assert rig.spoken() == [PHRASES["ciclo.apertura"][0]]
    await rig.advance(1.0)
    assert rig.spoken() == [PHRASES["ciclo.apertura"][0], said("config.error", archivo="catalog")]
    await rig.advance(1.0)
    await rig.order("abre GitHub")  # se conserva la configuración anterior
    assert rig.spoken()[-1] == said("apertura.abriendo", nombre="GitHub")
    await rig.stop()
