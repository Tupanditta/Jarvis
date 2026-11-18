"""Diálogo de varios turnos de principio a fin, con dobles (fase 4).

El grafo es el de `build_app`. El usuario escribe y responde sin repetir «Hey Jarvis». Cubre el
diálogo en el orquestador (T-4.1), la Creación (T-4.3, CU-09), la eliminación en el Historial
(T-4.4), el módulo Sesión (T-4.5, CU-10) y el cierre o la cancelación con un diálogo abierto
(T-4.6).
"""
from datetime import timedelta

import pytest

from integration.test_orders import Rig, said, settle
from jarvis_assistant.action_modules import file_manager
from jarvis_assistant.core import events
from jarvis_assistant.core.action_api import Phrase
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.notices import Notice
from jarvis_assistant.core.state_machine import AssistantState

S = AssistantState
# Además de los que registra `Rig`.
DIALOGUE = (events.DialogueOpened, events.DialogueClosed, events.SessionChanged,
            events.SessionOverflowed)  # fmt: skip


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    rig = Rig(tmp_path, monkeypatch)
    for event_type in DIALOGUE:
        rig.app.bus.subscribe(event_type, rig.events.append)
    await rig.start()
    await rig.open_session()
    yield rig
    await rig.stop()


def old_session(rig, name: str = "pruebas") -> int:
    """Una sesión anterior, ya cerrada."""
    opened = rig.clock.now() - timedelta(days=2)
    session_id = rig.sessions.create(name, opened)
    rig.sessions.close(session_id, opened + timedelta(hours=1), "voz")
    return session_id


def current_id(rig) -> int:
    (session,) = rig.sessions.find_open()
    return session.id


def last_task(rig):
    return rig.of(events.TaskUpdated)[-1]


def colision(name: str) -> str:
    return said("creacion.colision", nombre=name)


def creado(kind: str, name: str, folder: str = "usuario") -> str:
    return said("creacion.creado", tipo=kind, nombre=name, carpeta=folder)


async def ask_collision(rig) -> None:
    """«notas.txt» ya existe: el asistente pregunta otro nombre."""
    await rig.order("crea el archivo notas punto txt")
    assert rig.state is S.AWAITING_PARAMETER


# --- CU-09. Crear un archivo o carpeta -------------------------------------------------------


async def test_cu09_flujo_principal(rig):
    await rig.order("Crea el archivo informe punto txt en docs")
    assert (rig.home / "Docs" / "informe.txt").is_file()
    assert rig.spoken() == [creado("el archivo", "informe.txt", "Docs")]
    assert rig.tasks()[-1] == ("creacion", "crear informe.txt", "completado")
    assert rig.of(events.DialogueOpened) == []
    assert rig.state is S.LISTENING_COMMAND


async def test_cu09_sin_ubicacion_usa_el_directorio_de_trabajo(rig):
    await rig.order("ve a proyectos")
    await rig.order("crea la carpeta apuntes")
    assert (rig.home / "Proyectos" / "apuntes").is_dir()


async def test_cu09_a1_colision_resuelta_escribiendo_otro_nombre(rig):
    await ask_collision(rig)
    (opened,) = rig.of(events.DialogueOpened)
    assert opened.question == colision("notas.txt")
    assert opened.expected_type == "NEW_FILENAME"
    assert opened.hints == ("Otro nombre", "Cancelar")
    assert opened.timeout_seconds == 20.0
    assert opened.subject == {"nombre": "notas.txt", "carpeta": "usuario"}
    assert rig.spoken() == [colision("notas.txt")]
    assert rig.of(events.AssistantActivityChanged)[-1] == events.AssistantActivityChanged(
        "AWAITING_PARAMETER", Activity.ESPERANDO
    )
    assert rig.tasks() == [("creacion", "crea el archivo notas punto txt", "pendiente")]
    rig.events.clear()
    await rig.order("notas dos punto txt")  # sin repetir «Hey Jarvis»
    assert rig.of(events.DialogueClosed) == [events.DialogueClosed("answered")]
    assert (rig.home / "notas dos.txt").is_file()
    assert (rig.home / "notas.txt").read_text() == "x"
    assert rig.spoken() == [creado("el archivo", "notas dos.txt")]
    assert rig.tasks()[-1] == ("creacion", "crear notas dos.txt", "completado")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.of(events.AssistantActivityChanged)[-1].activity is Activity.ESCUCHANDO


async def test_cu09_a2_tercera_colision_seguida_cancela(rig):
    for name in ("notas dos.txt", "notas tres.txt"):
        (rig.home / name).write_text("x")
    await ask_collision(rig)
    await rig.order("notas dos punto txt")
    assert rig.state is S.AWAITING_PARAMETER
    rig.events.clear()
    await rig.order("notas tres punto txt")
    assert rig.spoken() == [said("general.operacion_cancelada")]
    assert rig.state is S.LISTENING_COMMAND
    task = last_task(rig)
    assert (task.status, task.detail) == ("error", "cancelada")
    assert sorted(p.name for p in rig.home.glob("*.txt")) == [
        "notas dos.txt", "notas tres.txt", "notas.txt",
    ]  # fmt: skip


async def test_cu09_a3_cancelar_no_crea_nada(rig):
    await ask_collision(rig)
    rig.events.clear()
    await rig.order("cancelar")
    assert rig.of(events.DialogueClosed) == [events.DialogueClosed("cancelled")]
    assert rig.spoken() == [said("general.operacion_cancelada")]  # una sola vez
    task = last_task(rig)
    assert (task.status, task.detail) == ("error", "cancelada")
    assert [p.name for p in rig.home.glob("*.txt")] == ["notas.txt"]
    assert rig.state is S.LISTENING_COMMAND


async def test_cu09_a4_veinte_segundos_sin_respuesta_cancelan(rig):
    await ask_collision(rig)
    rig.events.clear()
    await rig.advance(18.0)  # el tiempo empieza al terminar la pregunta
    assert rig.state is S.AWAITING_PARAMETER and rig.spoken() == []
    await rig.advance(3.0)
    assert rig.of(events.DialogueClosed) == [events.DialogueClosed("cancelled")]
    assert rig.spoken() == [said("general.operacion_cancelada")]
    assert (last_task(rig).status, last_task(rig).detail) == ("error", "cancelada")
    assert rig.state is S.LISTENING_COMMAND


async def test_cu09_a5_ubicacion_inexistente_no_crea_nada(rig):
    await rig.order("crea el archivo notas punto txt en fotos")
    assert rig.spoken() == [said("ruta.no_existe", nombre="fotos")]
    assert rig.tasks()[-1][2] == "error"
    assert not list(rig.home.glob("*fotos*"))


async def test_abrir_una_carpeta_inexistente_no_la_crea(rig):
    """«abre» se parece a «crea»: un error de ruta no se convierte en otra orden."""
    await rig.order("abre la carpeta fotos")
    assert rig.spoken() == [said("ruta.no_existe", nombre="fotos")]
    assert not (rig.home / "fotos").exists()


async def test_cu09_a7_arbol(rig):
    await rig.order("crea las carpetas backend barra src barra modelos")
    assert (rig.home / "backend" / "src" / "modelos").is_dir()
    assert rig.spoken() == [creado("las carpetas", "backend/src/modelos")]


# --- Diálogo en el orquestador (T-4.1) -------------------------------------------------------


async def test_una_respuesta_no_valida_repite_la_pregunta_y_la_segunda_cancela(rig):
    session = old_session(rig)
    await rig.order(f"elimina la sesión {session}")
    assert rig.state is S.AWAITING_CONFIRMATION
    rig.events.clear()
    await rig.order("quizá")
    question = said("historial.confirmar_eliminar", id=session, nombre="pruebas")
    assert rig.spoken() == [said("general.no_entendido"), question]
    assert rig.of(events.CommandReceived) == [events.CommandReceived("quizá", False)]
    assert rig.state is S.AWAITING_CONFIRMATION
    rig.events.clear()
    await rig.order("tampoco")
    assert rig.spoken() == [said("general.operacion_cancelada")]
    assert rig.state is S.LISTENING_COMMAND
    assert not rig.sessions.get(session).is_deleted


async def test_la_repeticion_reinicia_el_tiempo_de_espera(rig):
    session = old_session(rig)
    await rig.order(f"elimina la sesión {session}")
    await rig.advance(15.0)
    await rig.order("quizá")  # repite la pregunta: los 20 s empiezan de nuevo
    await rig.advance(15.0)
    assert rig.state is S.AWAITING_CONFIRMATION


async def test_hey_jarvis_en_espera_reinicia_el_tiempo_sin_voz(rig):
    await ask_collision(rig)
    await rig.advance(15.0)
    rig.events.clear()
    await rig.write("Hey Jarvis")
    await rig.advance(15.0)
    assert rig.state is S.AWAITING_PARAMETER and rig.spoken() == []
    await rig.advance(6.0)
    assert rig.state is S.LISTENING_COMMAND


async def test_en_espera_una_orden_es_una_respuesta_no_una_intencion(rig):
    await ask_collision(rig)
    await rig.order("abre github")  # un nombre válido: se crea «abre github»
    assert (rig.home / "abre github").is_file()
    assert rig.of(events.OpenedItemsChanged) == []  # no se ha abierto nada


async def test_un_mensaje_con_separador_en_espera_es_una_sola_respuesta(rig):
    await ask_collision(rig)
    await rig.order("cancelar -- lista")
    # No es «cancelar» ni dos órdenes: es un nombre con caracteres válidos.
    assert rig.of(events.DialogueClosed)[-1] == events.DialogueClosed("answered")


async def test_los_avisos_esperan_a_que_termine_el_dialogo(rig):
    """RN-39: un aviso que llega durante la pregunta se dice al terminar el diálogo."""
    await ask_collision(rig)
    rig.events.clear()
    rig.app.orchestrator._notify(Notice(Phrase("comandos.tiempo")))
    await rig.advance(2.0)
    assert rig.spoken() == [] and rig.state is S.AWAITING_PARAMETER
    await rig.order("cancelar")
    await rig.advance(2.0)
    assert rig.spoken() == [said("general.operacion_cancelada"), said("comandos.tiempo")]


async def test_dos_ordenes_a_la_vez_preguntan_de_una_en_una(rig):
    session = old_session(rig)
    await rig.order(f"crea el archivo notas punto txt -- elimina la sesión {session}")
    # Primero una pregunta; la otra espera a que se resuelva.
    assert len(rig.of(events.DialogueOpened)) == 1
    first = rig.of(events.DialogueOpened)[0]
    if first.expected_type == "NEW_FILENAME":
        await rig.order("otras notas punto txt")
        await rig.order("sí")
    else:
        await rig.order("sí")
        await rig.order("otras notas punto txt")
    assert len(rig.of(events.DialogueOpened)) == 2
    assert (rig.home / "otras notas.txt").is_file()
    assert rig.sessions.get(session).is_deleted
    assert rig.state is S.LISTENING_COMMAND


# --- CU-10. Sesión e historial ---------------------------------------------------------------


async def test_cu10_flujo_principal_nombre_importancia_y_consulta(rig):
    session = current_id(rig)
    await rig.order("Llama a la sesión práctica de redes")
    assert rig.spoken()[-1] == said("sesion.nombrada", nombre="práctica de redes")
    assert rig.of(events.SessionChanged)[-1] == events.SessionChanged(
        session, "práctica de redes", False
    )
    await rig.order("Marca la sesión como importante")
    assert rig.spoken()[-1] == said("sesion.importante")
    assert rig.of(events.SessionChanged)[-1].is_important
    stored = rig.sessions.get(session)
    assert stored.name_set_by_module and stored.importance_locked_by_module
    await rig.order("Muestra el historial")
    assert rig.of(events.HistoryShown)[-1].sessions[0].id == session


async def test_cu10_a1_desbordamiento_y_a2_restauracion(rig):
    start = rig.clock.now() - timedelta(days=30)
    old = []
    for index in range(10):
        session_id = rig.sessions.create(f"vieja {index}", start + timedelta(days=index))
        rig.sessions.set_importance(session_id, True, by_user=True)
        rig.sessions.close(session_id, start + timedelta(days=index, hours=1), "voz")
        old.append(session_id)
    await rig.order("marca la sesión como importante")
    assert rig.spoken() == [
        said("sesion.desbordamiento", nombre="vieja 0"), said("sesion.importante"),
    ]  # fmt: skip
    assert rig.of(events.SessionOverflowed) == [events.SessionOverflowed(old[0], "vieja 0")]
    assert not rig.sessions.get(old[0]).is_important
    await rig.order("la sesión no es importante")
    assert rig.sessions.get(old[0]).is_important


async def test_cu10_a1_la_desplazada_se_elimina_al_cerrar(rig):
    start = rig.clock.now() - timedelta(days=30)
    for index in range(10):
        session_id = rig.sessions.create(f"vieja {index}", start + timedelta(days=index))
        rig.sessions.set_importance(session_id, True, by_user=True)
        rig.sessions.close(session_id, start + timedelta(days=index, hours=1), "voz")
        if index == 0:
            oldest = session_id
    await rig.order("marca la sesión como importante")
    await rig.order("buenas noches jarvis")
    assert rig.sessions.get(oldest).is_deleted


async def test_cu10_flujo_secundario_eliminar_con_confirmacion(rig):
    session = old_session(rig)
    await rig.order(f"Elimina la sesión {session}")
    assert rig.state is S.AWAITING_CONFIRMATION
    (opened,) = rig.of(events.DialogueOpened)
    question = said("historial.confirmar_eliminar", id=session, nombre="pruebas")
    assert (opened.question, opened.expected_type, opened.hints) == (
        question, "BOOLEAN", ("Sí", "No", "Cancelar"),
    )  # fmt: skip
    assert opened.subject == {"id": session, "nombre": "pruebas"}
    assert [s.id for s in rig.of(events.HistoryShown)[-1].sessions] == [session]
    assert rig.of(events.AssistantActivityChanged)[-1] == events.AssistantActivityChanged(
        "AWAITING_CONFIRMATION", Activity.ESPERANDO
    )
    rig.events.clear()
    await rig.order("Sí")
    assert rig.spoken() == [said("historial.eliminada", id=session)]
    assert rig.sessions.get(session).is_deleted
    await rig.order("muestra el historial")
    assert session not in [s.id for s in rig.of(events.HistoryShown)[-1].sessions]


@pytest.mark.parametrize("answer", ["No", "cancelar"])
async def test_cu10_a6_no_o_cancelar_no_elimina(rig, answer):
    session = old_session(rig)
    await rig.order(f"elimina la sesión {session}")
    rig.events.clear()
    await rig.order(answer)
    assert rig.spoken() == [said("general.operacion_cancelada")]
    assert not rig.sessions.get(session).is_deleted
    assert (last_task(rig).status, last_task(rig).detail) == ("error", "cancelada")


async def test_cu10_a6_sin_respuesta_en_veinte_segundos_no_elimina(rig):
    session = old_session(rig)
    await rig.order(f"elimina la sesión {session}")
    await rig.advance(21.0)
    assert not rig.sessions.get(session).is_deleted
    assert rig.state is S.LISTENING_COMMAND


async def test_cu10_a4_y_a5_sin_pregunta(rig):
    await rig.order("elimina la sesión 99")
    assert rig.spoken() == [said("historial.no_existe", id=99)]
    rig.events.clear()
    await rig.order(f"elimina la sesión {current_id(rig)}")
    assert rig.spoken() == [said("historial.es_actual")]
    assert rig.of(events.DialogueOpened) == []


# --- T-4.6. Cierre y cancelación con un diálogo abierto --------------------------------------


async def test_gracias_jarvis_en_espera_cancela_el_dialogo_y_pasa_a_reposo(rig):
    await ask_collision(rig)
    rig.events.clear()
    await rig.order("gracias jarvis")
    assert rig.state is S.IDLE
    assert rig.of(events.DialogueClosed) == [events.DialogueClosed("cancelled")]
    assert rig.spoken() == [said("ciclo.reposo")]
    assert (last_task(rig).status, last_task(rig).detail) == ("error", "cancelada")
    assert [p.name for p in rig.home.glob("*.txt")] == ["notas.txt"]


async def test_buenas_noches_en_espera_cierra_la_sesion_y_cancela_todo(rig):
    """RN-46: el diálogo, la tarea que pregunta y una orden en curso terminan en error."""
    await rig.write("espera un poco")  # orden lenta de otro módulo
    await ask_collision(rig)
    rig.events.clear()
    await rig.order("buenas noches jarvis")
    assert rig.state is S.DORMIDO
    assert rig.of(events.DialogueClosed) == [events.DialogueClosed("cancelled")]
    statuses = {(t.module, t.status) for t in rig.of(events.TaskUpdated)}
    assert statuses == {("creacion", "error"), ("prueba", "error")}
    assert rig.spoken() == [said("ciclo.cierre")]
    assert [p.name for p in rig.home.glob("*.txt")] == ["notas.txt"]
    # La sesión siguiente empieza sin diálogo.
    await rig.write("Hey Jarvis")
    await rig.advance(1.0)
    assert rig.state is S.LISTENING_COMMAND
    await rig.order("lista")
    assert rig.of(events.DirectoryListed)


async def test_cancelar_con_un_turno_en_curso_y_sin_dialogo(rig):
    """RN-52: «cancelar» detiene la orden en curso; el diálogo no interviene."""
    await rig.write("espera un poco")
    rig.events.clear()
    await rig.order("cancelar")
    assert rig.spoken() == [said("general.cancelado")]
    assert (last_task(rig).status, last_task(rig).detail) == ("error", "cancelada")
    assert rig.of(events.DialogueClosed) == []


async def test_una_tarea_que_pregunta_y_falla_deja_la_fsm_en_escucha(rig, monkeypatch):
    """RNF-23 con diálogo: una excepción tras la respuesta deja la tarea en error y la FSM
    en escucha."""

    def broken(*_args, **_kwargs):
        raise RuntimeError("roto")

    await ask_collision(rig)
    monkeypatch.setattr(file_manager, "_make", broken)
    rig.events.clear()
    await rig.order("otro punto txt")
    await settle()
    assert rig.state is S.LISTENING_COMMAND
    assert last_task(rig).status == "error"
    assert rig.spoken() == [said("general.error")]
    await rig.order("lista")
    assert rig.of(events.DirectoryListed)
