"""Protocolos de principio a fin, con dobles (fase 6; CU-13).

El grafo es el de `build_app`, con los módulos reales y un módulo falso cuyas acciones se usan
como tareas de protocolo. Cubre la ejecución y sus subtareas (T-6.2), la integración con Sesión
(T-6.3), los eventos del panel (T-6.4) y la validación de `protocols.toml` contra el registro
(T-6.1).
"""
import asyncio
import dataclasses
from datetime import timedelta
from types import MappingProxyType

import pytest

from integration.test_orders import CONFIG, Rig, said, settle
from jarvis_assistant import main as main_module
from jarvis_assistant.config import ConfigError, ProtocolDef, ProtocolTask
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import (
    ActionResult,
    ExpectedType,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.state_machine import AssistantState

S = AssistantState
PROTOCOL_EVENTS = (
    events.ProtocolStarted, events.ProtocolFinished, events.ProtocolsListed,
    events.DialogueOpened, events.SessionChanged, events.SessionOverflowed,
)  # fmt: skip


class Fake:
    """Módulo falso: anota lo que recibe, falla, pregunta y espera."""

    name = "falso"
    title = "Falso"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, str]] = []
        self.gate = asyncio.Event()

    def intents(self):
        return (
            IntentSpec("apuntar", ("apunta {texto}",), (Slot("texto", SlotType.TEXT),),
                       "Apuntar", "Apunta algo"),
            IntentSpec("mirar", ("mira la carpeta {ruta}",),
                       (Slot("ruta", SlotType.DIR_PATH),), "Mirar", "Mira la carpeta docs"),
            IntentSpec("estropear", ("estropea todo",), (), "Estropear", "Estropea todo"),
            IntentSpec("consultar", ("consulta algo",), (), "Consultar", "Consulta algo"),
            IntentSpec("aguardar", ("aguarda un rato",), (), "Aguardar", "Aguarda un rato"),
            IntentSpec("solo_voz", ("solo por voz",), (), "Solo por voz", "Solo por voz",
                       in_protocols=False),
        )  # fmt: skip

    async def execute(self, action, params, ctx):
        self.calls.append((action, dict(params), ctx.origin))
        match action:
            case "apuntar" | "mirar":
                return ActionResult("completado", Phrase("comandos.consola"))
            case "estropear":
                return ActionResult("error", Phrase("comandos.ocupado"))
            case "consultar":
                answer = await ctx.ask(Phrase("recordatorio.confirmar_eliminar", {"n": 1}),
                                       ExpectedType.BOOLEAN)
                if answer.cancelled or answer.value is not True:
                    return ActionResult("error")
                return ActionResult("completado", Phrase("comandos.consola"))
            case "aguardar":
                await self.gate.wait()
                return ActionResult("completado")
            case "solo_voz":
                return ActionResult("completado")
        raise ValueError(action)


def task(module: str, action: str, stop: bool = False, **params) -> ProtocolTask:
    return ProtocolTask(module, action, MappingProxyType(params), stop_on_error=stop)


def protocol(*tasks: ProtocolTask, name="modo trabajo", important=False, **kw) -> ProtocolDef:
    return ProtocolDef(name.replace(" ", "-"), name, tasks, important=important, **kw)


WORK = protocol(
    task("comandos", "cd", ruta="proyectos"),
    task("falso", "mirar", ruta="jarvis"),  # relativa: dentro de «proyectos» (al ejecutarse)
    task("falso", "apuntar", texto="hola"),
    important=True, aliases=("a trabajar",),
)


async def make_rig(tmp_path, monkeypatch, *protocols, reload=None) -> tuple[Rig, Fake]:
    fake = Fake()
    monkeypatch.setattr(
        main_module, "ACTION_MODULES", [*main_module.ACTION_MODULES, lambda: fake]
    )
    config = dataclasses.replace(CONFIG, protocols=protocols)
    rig = Rig(tmp_path, monkeypatch, config, reload=reload)
    for event_type in PROTOCOL_EVENTS:
        rig.app.bus.subscribe(event_type, rig.events.append)
    await rig.start()
    await rig.open_session()
    return rig, fake


@pytest.fixture
async def work(tmp_path, monkeypatch):
    rig, fake = await make_rig(tmp_path, monkeypatch, WORK)
    yield rig, fake
    await rig.stop()


def current(rig):
    (session,) = rig.sessions.find_open()
    return session


def updates_of(rig, task_id: int) -> list[tuple[str, str | None]]:
    return [(t.status, t.detail) for t in rig.of(events.TaskUpdated) if t.task_id == task_id]


def final(rig, task_id: int) -> tuple[str, str | None]:
    return updates_of(rig, task_id)[-1]


# --- CU-13. Flujo principal ------------------------------------------------------------------


async def test_cu13_flujo_principal(work):
    rig, fake = work
    session = current(rig)
    await rig.order("Protocolo modo trabajo")

    # Panel con todas las tareas en `pendiente` (RF-53) y la propuesta de nombre (RF-54).
    (started,) = rig.of(events.ProtocolStarted)
    assert started.name == "modo trabajo"
    assert started.steps == ("cd proyectos", "mirar jarvis", "apuntar hola")
    assert all(updates_of(rig, i)[0] == ("pendiente", None) for i in started.step_ids)
    parent = started.task_id
    assert {t.parent_id for t in rig.of(events.TaskUpdated) if t.task_id in started.step_ids} == {
        parent
    }
    assert events.PanelActivated("protocolo") in rig.of(events.PanelActivated)
    assert rig.state is S.AWAITING_CONFIRMATION
    assert rig.spoken() == [
        said("protocolos.inicio", nombre="modo trabajo"),
        said("sesion.proponer_nombre", nombre="modo trabajo"),
    ]  # fmt: skip
    assert fake.calls == []  # las tareas esperan a que se resuelva la pregunta

    rig.events.clear()
    await rig.order("Sí")
    renamed = rig.sessions.get(session.id)
    assert renamed.name == "modo trabajo" and not renamed.name_set_by_module
    assert renamed.is_important  # RN-36
    assert not renamed.importance_locked_by_module

    # Tareas en orden, con los parámetros resueltos en su momento (RF-56).
    assert fake.calls == [
        ("mirar", {"ruta": rig.home / "Proyectos" / "Jarvis"}, "protocolo"),
        ("apuntar", {"texto": "hola"}, "protocolo"),
    ]
    assert all(final(rig, i) == ("completado", None) for i in started.step_ids)
    # Sin frases intermedias: solo el resumen (RF-57).
    assert rig.spoken() == [said("protocolos.completado", nombre="modo trabajo")]
    assert rig.of(events.ProtocolFinished) == [events.ProtocolFinished(parent, 3, 0)]
    assert final(rig, parent) == ("completado", None)
    # Todo queda en el historial con el protocolo como tarea padre.
    rows = rig.activities.of_session(session.id)
    protocol_row = next(row for row in rows if row.id == parent)
    assert (protocol_row.module, protocol_row.description, protocol_row.status) == (
        "protocolos", "protocolo modo trabajo", "completado",
    )  # fmt: skip
    children = [(r.module, r.status) for r in rows if r.parent_id == parent]
    assert ("comandos", "completado") in children and ("falso", "completado") in children
    assert rig.state is S.LISTENING_COMMAND


async def test_un_alias_tambien_lanza_el_protocolo(work):
    rig, _fake = work
    await rig.order("activa el protocolo a trabajar")
    assert rig.of(events.ProtocolStarted)[0].name == "modo trabajo"


# --- Renombrado e importancia (T-6.3) --------------------------------------------------------


async def test_a1_nombre_fijado_por_el_usuario_no_pregunta(work):
    rig, fake = work
    await rig.order("llama a la sesión redes")
    rig.events.clear()
    await rig.order("protocolo modo trabajo")
    assert rig.of(events.DialogueOpened) == []
    assert current(rig).name == "redes"  # RN-03
    assert len(fake.calls) == 2


async def test_a2_un_no_no_detiene_el_protocolo(work):
    rig, fake = work
    name = current(rig).name
    await rig.order("protocolo modo trabajo")
    await rig.order("No")
    assert current(rig).name == name
    assert len(fake.calls) == 2
    parent = rig.of(events.ProtocolStarted)[0].task_id
    assert final(rig, parent) == ("completado", None)


async def test_a2_cancelar_la_pregunta_del_nombre_detiene_el_protocolo(work):
    """«Cancelar» ante la propuesta de nombre detiene el protocolo antes de su primera tarea:
    todas quedan en `error` «cancelada» y la sesión no cambia."""
    rig, fake = work
    session = current(rig)
    await rig.order("protocolo modo trabajo")
    await rig.order("cancelar")
    await rig.advance(2.0)
    (started,) = rig.of(events.ProtocolStarted)
    assert fake.calls == []
    assert [final(rig, i) for i in started.step_ids] == [("error", "cancelada")] * 3
    assert final(rig, started.task_id) == ("error", "cancelada")
    assert rig.of(events.ProtocolFinished)[-1] == events.ProtocolFinished(started.task_id, 0, 3)
    after = current(rig)
    assert after.name == session.name
    assert not after.is_important  # el protocolo es importante, pero no ha llegado a marcarla
    assert rig.spoken()[-1] == said("general.operacion_cancelada")
    assert not any("protocolo" in line.casefold() for line in rig.spoken()[2:])
    assert rig.state is S.LISTENING_COMMAND


async def test_a2_sin_respuesta_el_protocolo_continua(work):
    rig, fake = work
    await rig.order("protocolo modo trabajo")
    await rig.advance(25.0)
    assert len(fake.calls) == 2
    assert rig.state is S.LISTENING_COMMAND


async def test_un_protocolo_importante_no_cambia_una_sesion_ya_importante(work):
    rig, _fake = work
    await rig.order("llama a la sesión redes")
    await rig.order("marca la sesión como importante")
    rig.events.clear()
    await rig.order("protocolo modo trabajo")
    session = current(rig)
    assert session.is_important and session.importance_locked_by_module
    assert rig.of(events.SessionOverflowed) == []


async def test_un_protocolo_importante_hace_importante_una_sesion_desmarcada(work):
    """RN-05: el usuario la desmarcó; el protocolo la marca igualmente."""
    rig, _fake = work
    await rig.order("llama a la sesión redes")
    await rig.order("la sesión no es importante")
    await rig.order("protocolo modo trabajo")
    assert current(rig).is_important


async def test_a3_desbordamiento_de_sesiones_importantes(work):
    rig, _fake = work
    start = rig.clock.now() - timedelta(days=30)
    old = []
    for index in range(10):
        session_id = rig.sessions.create(f"vieja {index}", start + timedelta(days=index))
        rig.sessions.set_importance(session_id, True, by_user=True)
        rig.sessions.close(session_id, start + timedelta(days=index, hours=1), "voz")
        old.append(session_id)
    await rig.order("llama a la sesión redes")
    rig.events.clear()
    await rig.order("protocolo modo trabajo")
    assert rig.of(events.SessionOverflowed) == [events.SessionOverflowed(old[0], "vieja 0")]
    assert said("sesion.desbordamiento", nombre="vieja 0") in rig.spoken()
    assert current(rig).is_important


async def test_un_protocolo_no_importante_no_toca_la_importancia(tmp_path, monkeypatch):
    only_tasks = protocol(task("falso", "apuntar", texto="x"))
    rig, _fake = await make_rig(tmp_path, monkeypatch, only_tasks)
    try:
        await rig.order("llama a la sesión redes")
        await rig.order("protocolo modo trabajo")
        assert not current(rig).is_important
    finally:
        await rig.stop()


# --- Errores, diálogo y cancelación (T-6.2) --------------------------------------------------


async def run(tmp_path, monkeypatch, *tasks: ProtocolTask) -> tuple[Rig, Fake]:
    """Un protocolo con `tasks` en una sesión con nombre (sin la pregunta del nombre)."""
    rig, fake = await make_rig(tmp_path, monkeypatch, protocol(*tasks))
    await rig.order("llama a la sesión redes")
    rig.events.clear()
    return rig, fake


async def test_a4_una_tarea_en_error_no_detiene_el_protocolo(tmp_path, monkeypatch):
    rig, fake = await run(
        tmp_path, monkeypatch, task("falso", "estropear"), task("falso", "apuntar", texto="x")
    )
    try:
        await rig.order("protocolo modo trabajo")
        await rig.advance(2.0)
        (started,) = rig.of(events.ProtocolStarted)
        first, second = started.step_ids
        assert final(rig, first)[0] == "error"
        assert final(rig, second) == ("completado", None)
        assert [call[0] for call in fake.calls] == ["estropear", "apuntar"]
        # El motivo del error sí se dice; al final, el resumen con el recuento.
        assert rig.spoken() == [
            said("protocolos.inicio", nombre="modo trabajo"),
            said("comandos.ocupado"),
            said("protocolos.con_errores", nombre="modo trabajo", n="1 error"),
        ]  # fmt: skip
        assert final(rig, started.task_id) == ("error", "1 error")
        assert rig.of(events.ProtocolFinished)[-1].failed == 1
    finally:
        await rig.stop()


async def test_a5_stop_on_error_deja_las_restantes_en_error(tmp_path, monkeypatch):
    rig, fake = await run(
        tmp_path, monkeypatch,
        task("falso", "estropear", stop=True), task("falso", "apuntar", texto="x"),
        task("falso", "apuntar", texto="y"),
    )  # fmt: skip
    try:
        await rig.order("protocolo modo trabajo")
        await rig.advance(2.0)
        (started,) = rig.of(events.ProtocolStarted)
        assert [call[0] for call in fake.calls] == ["estropear"]
        assert [final(rig, i) for i in started.step_ids[1:]] == [
            ("error", "protocolo detenido"), ("error", "protocolo detenido"),
        ]  # fmt: skip
        assert rig.spoken()[-1] == said(
            "protocolos.con_errores", nombre="modo trabajo", n="3 errores"
        )
        assert rig.of(events.ProtocolFinished)[-1] == events.ProtocolFinished(
            started.task_id, 0, 3
        )
    finally:
        await rig.stop()


async def test_una_entidad_que_no_se_resuelve_deja_la_tarea_en_error(tmp_path, monkeypatch):
    rig, fake = await run(
        tmp_path, monkeypatch, task("falso", "mirar", ruta="no existe"),
        task("falso", "apuntar", texto="x"),
    )  # fmt: skip
    try:
        await rig.order("protocolo modo trabajo")
        first, _second = rig.of(events.ProtocolStarted)[0].step_ids
        assert final(rig, first)[0] == "error"
        assert [call[0] for call in fake.calls] == ["apuntar"]
        assert said("ruta.no_existe", nombre="no existe") in rig.spoken()
    finally:
        await rig.stop()


async def test_a6_una_tarea_con_dialogo_espera_la_respuesta(tmp_path, monkeypatch):
    rig, fake = await run(
        tmp_path, monkeypatch, task("falso", "consultar"), task("falso", "apuntar", texto="x")
    )
    try:
        await rig.order("protocolo modo trabajo")
        assert rig.state is S.AWAITING_CONFIRMATION  # RN-35
        assert [call[0] for call in fake.calls] == ["consultar"]
        await rig.order("sí")
        assert [call[0] for call in fake.calls] == ["consultar", "apuntar"]
        assert rig.spoken()[-1] == said("protocolos.completado", nombre="modo trabajo")
    finally:
        await rig.stop()


async def test_a6_dialogo_cancelado_deja_la_tarea_en_error_y_sigue(tmp_path, monkeypatch):
    rig, fake = await run(
        tmp_path, monkeypatch, task("falso", "consultar"), task("falso", "apuntar", texto="x")
    )
    try:
        await rig.order("protocolo modo trabajo")
        await rig.order("cancelar")
        first, second = rig.of(events.ProtocolStarted)[0].step_ids
        assert final(rig, first)[0] == "error"
        assert final(rig, second) == ("completado", None)
        assert [call[0] for call in fake.calls] == ["consultar", "apuntar"]
    finally:
        await rig.stop()


async def test_a7_cancelar_detiene_el_protocolo(tmp_path, monkeypatch):
    rig, fake = await run(
        tmp_path, monkeypatch, task("falso", "apuntar", texto="x"), task("falso", "aguardar"),
        task("falso", "apuntar", texto="y"),
    )  # fmt: skip
    try:
        await rig.write("protocolo modo trabajo")
        await rig.write("cancelar")
        (started,) = rig.of(events.ProtocolStarted)
        assert [final(rig, i) for i in started.step_ids] == [
            ("completado", None), ("error", "cancelada"), ("error", "cancelada"),
        ]  # fmt: skip
        assert final(rig, started.task_id) == ("error", "cancelada")
        assert rig.of(events.ProtocolFinished)[-1] == events.ProtocolFinished(
            started.task_id, 1, 2
        )
        assert [call[0] for call in fake.calls] == ["apuntar", "aguardar"]
        await rig.advance(2.0)
        assert rig.spoken()[-1] == said("general.cancelado")
        assert rig.state is S.LISTENING_COMMAND
    finally:
        await rig.stop()


async def test_el_cierre_de_sesion_detiene_el_protocolo(tmp_path, monkeypatch):
    rig, _fake = await run(
        tmp_path, monkeypatch, task("falso", "aguardar"), task("falso", "apuntar", texto="y")
    )
    try:
        session = current(rig)
        await rig.write("protocolo modo trabajo")
        await rig.write("buenas noches jarvis")
        (started,) = rig.of(events.ProtocolStarted)
        assert [final(rig, i) for i in [*started.step_ids, started.task_id]] == [
            ("error", "sesión cerrada")
        ] * 3  # RN-46
        steps = set(started.step_ids)
        statuses = {a.status for a in rig.activities.of_session(session.id) if a.id in steps}
        assert statuses == {"error"}
    finally:
        await rig.stop()


async def test_rn55_otra_orden_espera_a_que_termine_el_protocolo(tmp_path, monkeypatch):
    rig, fake = await run(tmp_path, monkeypatch, task("falso", "aguardar"))
    try:
        await rig.write("protocolo modo trabajo")
        await rig.write("protocolo modo trabajo")
        await rig.write("apunta algo")
        assert len(rig.of(events.ProtocolStarted)) == 1
        assert [call[0] for call in fake.calls] == ["aguardar"]
        fake.gate.set()
        await settle()
        await rig.advance(1.0)
        assert len(rig.of(events.ProtocolStarted)) == 2
        await settle()
        assert [call[0] for call in fake.calls] == ["aguardar", "aguardar", "apuntar"]
    finally:
        await rig.stop()


# --- A8, A9: no encontrado y listado ---------------------------------------------------------


async def test_a8_protocolo_no_encontrado(work):
    rig, _fake = work
    await rig.order("protocolo vacaciones en la playa")
    assert rig.spoken() == [said("entidad.no_encontrado", nombre="vacaciones en la playa")]
    assert rig.tasks()[-1][2] == "error"
    assert rig.of(events.ProtocolStarted) == []


async def test_a9_listar_los_protocolos(work):
    rig, _fake = work
    await rig.order("Qué protocolos hay")
    (listed,) = rig.of(events.ProtocolsListed)
    assert [(p.id, p.name, p.aliases, p.important) for p in listed.protocols] == [
        ("modo-trabajo", "modo trabajo", ("a trabajar",), True)
    ]
    assert listed.protocols[0].steps == ("cd proyectos", "mirar jarvis", "apuntar hola")
    assert rig.spoken() == [said("protocolos.lista", n="1 protocolo")]
    assert rig.of(events.PanelActivated) == [events.PanelActivated("protocolo")]


async def test_a9_sin_protocolos(tmp_path, monkeypatch):
    rig, _fake = await make_rig(tmp_path, monkeypatch)
    try:
        await rig.order("muestra los protocolos")
        assert rig.of(events.ProtocolsListed) == [events.ProtocolsListed(())]
        assert rig.spoken() == [said("protocolos.ninguno")]
    finally:
        await rig.stop()


# --- T-6.1. Validación contra el registro ----------------------------------------------------


INVALID = (
    protocol(task("falso", "volar"), name="no existe"),
    protocol(task("falso", "solo_voz"), name="solo voz"),
    protocol(task("protocolos", "ejecutar", protocolo="modo trabajo"), name="anidado"),
    protocol(task("falso", "mirar"), name="sin ruta"),
)


async def test_los_protocolos_no_validos_se_descartan_y_los_demas_se_cargan(tmp_path, monkeypatch):
    rig, _fake = await make_rig(tmp_path, monkeypatch, WORK, *INVALID)
    try:
        assert [p.name for p in rig.app.orchestrator._config.protocols] == ["modo trabajo"]
        await rig.order("qué protocolos hay")
        assert [p.name for p in rig.of(events.ProtocolsListed)[0].protocols] == ["modo trabajo"]
        await rig.order("protocolo solo voz")
        assert rig.of(events.ProtocolStarted) == []
    finally:
        await rig.stop()


async def test_un_protocolo_no_valido_al_recargar_se_avisa(tmp_path, monkeypatch):
    """La recarga al abrir cada sesión (RF-96) valida otra vez y avisa tras la apertura."""

    def reload(previous):
        return dataclasses.replace(previous, protocols=(WORK, INVALID[0])), []

    rig, _fake = await make_rig(tmp_path, monkeypatch, reload=reload)
    try:
        assert [p.name for p in rig.app.orchestrator._config.protocols] == ["modo trabajo"]
        await rig.order("buenas noches jarvis")
        rig.events.clear()
        await rig.write("hey jarvis")
        await rig.advance(8.0)
        assert events.ConfigReloadFailed(
            "protocols.toml", "no-existe: la acción falso.volar no existe"
        ) in rig.of(events.ConfigReloadFailed)
        assert said("config.error", archivo="protocols") in rig.spoken()
    finally:
        await rig.stop()


def test_config_error_de_un_protocolo_indica_tarea():
    from jarvis_assistant.config import validate_protocols

    valid, errors = validate_protocols((INVALID[0],), lambda _m, _a: ())
    assert valid == ()
    assert errors == [
        ConfigError("protocols.toml", "protocols[0].tasks[0]",
                    "no-existe: la acción falso.volar no existe")
    ]  # fmt: skip


# --- T-6.5. RNF-19: todas las acciones admitidas, desde un protocolo -------------------------

# Parámetros de ejemplo de cada acción con `in_protocols = True` de los módulos reales, escritos
# como en `protocols.toml`. Una acción nueva que se pueda usar en protocolos debe añadirse aquí.
EVERY_ACTION: tuple[tuple[str, str, dict], ...] = (
    ("comandos", "cd", {"ruta": "proyectos"}),
    ("comandos", "pwd", {}),
    ("comandos", "ls", {}),
    ("comandos", "arbol", {"ruta": "jarvis"}),
    ("comandos", "clear", {}),
    ("comandos", "ejecutar", {"comando": "git status"}),
    ("comandos", "abrir_consola", {}),
    ("apertura", "abrir", {"objetivo": "GitHub"}),
    ("apertura", "abrir_carpeta", {"ruta": "jarvis"}),
    ("busqueda", "buscar", {"consulta": "informe"}),
    ("creacion", "crear_archivo", {"nombre": "notas punto txt"}),
    ("creacion", "crear_carpeta", {"nombre": "apuntes"}),
    ("creacion", "crear_arbol", {"arbol": "src barra modelos"}),
    ("creacion", "crear_estructura", {"estructura": "proyecto python", "nombre": "analizador"}),
    ("historial", "mostrar", {}),
    ("historial", "actividades", {}),
    ("recordatorio", "crear", {"texto": "tengo que llamar a Ana",
                               "avisos": "mañana a las nueve"}),
    ("recordatorio", "mostrar", {}),
    # Al final: la ventana de lo abierto se busca en segundo plano y tarda en aparecer.
    ("apertura", "traer_al_frente", {"objetivo": "GitHub"}),
)  # fmt: skip


async def test_rnf19_cada_accion_admitida_se_invoca_desde_un_protocolo(tmp_path, monkeypatch):
    from jarvis_assistant.config import StructureDef
    from jarvis_assistant.os_adapters.base import SearchOutcome

    everything = protocol(*(task(m, a, **p) for m, a, p in EVERY_ACTION), name="todo")
    fake = Fake()
    monkeypatch.setattr(
        main_module, "ACTION_MODULES", [*main_module.ACTION_MODULES, lambda: fake]
    )
    config = dataclasses.replace(
        CONFIG, protocols=(everything,),
        structures=(StructureDef("proyecto python", ("src", "tests")),),
    )  # fmt: skip
    rig = Rig(tmp_path, monkeypatch, config)
    for event_type in PROTOCOL_EVENTS:
        rig.app.bus.subscribe(event_type, rig.events.append)

    async def launch_finished(executable, args, cwd):  # el binario termina en el acto
        process = await rig._launch(executable, args, cwd)
        process.finish(0)
        return process

    rig.app.orchestrator.modules["comandos"]._launch = launch_finished
    rig.platform.search_outcome = SearchOutcome((), 0)
    try:
        await rig.start()
        await rig.open_session()
        # El registro: todas las acciones admitidas de los módulos reales están en la tabla.
        real = {name for name in rig.app.orchestrator.modules} - {"falso", "prueba"}
        admitted = {
            (module, spec.action) for module, spec in rig.app.router.specs()
            if module in real and spec.in_protocols
        }  # fmt: skip
        assert admitted == {(m, a) for m, a, _p in EVERY_ACTION}

        await rig.order("llama a la sesión todo")
        await rig.write("protocolo todo")
        await rig.until(lambda: rig.of(events.ProtocolFinished) != [])
        (started,) = rig.of(events.ProtocolStarted)
        updates = {t.task_id: t for t in rig.of(events.TaskUpdated)}
        outcome = [
            (m, a, updates[i].status, updates[i].detail)
            for (m, a, _p), i in zip(EVERY_ACTION, started.step_ids, strict=True)
        ]  # fmt: skip
        assert [row for row in outcome if row[2] != "completado"] == []
        assert rig.of(events.ProtocolFinished) == [
            events.ProtocolFinished(started.task_id, len(EVERY_ACTION), 0)
        ]
        assert (rig.home / "Proyectos" / "notas.txt").is_file()  # tras el `cd`, relativo
    finally:
        await rig.stop()
