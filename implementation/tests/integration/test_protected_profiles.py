"""Perfiles protegidos de principio a fin, con dobles.

«Hey Jarvis» en un perfil con contraseña abre la caja de la contraseña en dormido; solo la
contraseña correcta abre la sesión. El tercer fallo seguido registra, sin decirlo, un aviso de
intrusión que el dueño recibe lo primero al entrar.
"""
import logging

import pytest

from integration.test_orders import RECORDED, Rig, said
from jarvis_assistant.config import Config, Profile
from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity
from jarvis_assistant.core.security import ProfileVault, hash_password
from jarvis_assistant.core.state_machine import AssistantState

S = AssistantState
PASSWORD = "clave-1234"
CONFIG = Config(profiles=(Profile("trabajo", "Trabajo"), Profile("secreto", "Confidencial")))
EXTRA = (
    events.SessionOpened, events.ProtectedProfilesChanged, events.AccessChallenged,
    events.AccessDenied, events.AccessClosed, events.IntrusionAlertsShown,
)  # fmt: skip


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    rig = Rig(tmp_path, monkeypatch, config=CONFIG)
    ProfileVault(rig.database).set_password_hash("secreto", hash_password(PASSWORD))
    for event_type in EXTRA:
        if event_type not in RECORDED:
            rig.app.bus.subscribe(event_type, rig.events.append)
    await rig.start()
    yield rig
    await rig.stop()


async def choose(rig, profile_id: str) -> None:
    rig.app.bus.publish(events.ProfileSelected(profile_id))
    await rig.advance(0.1)


async def attempt(rig, password: str) -> None:
    rig.app.bus.publish(events.AccessAttempted(password))
    await rig.advance(3.0)


async def wake(rig) -> None:
    await rig.write("Hey Jarvis")
    await rig.advance(3.0)


async def enter(rig) -> None:
    """Abre la sesión del perfil protegido con su contraseña."""
    await choose(rig, "secreto")
    await wake(rig)
    await attempt(rig, PASSWORD)
    await rig.until(lambda: rig.app.orchestrator.modules["apertura"]._discovery.done())
    await rig.advance(1.0)


async def lock_out(rig) -> None:
    await choose(rig, "secreto")
    await wake(rig)
    for _ in range(3):
        await attempt(rig, "mala")


def pending_alerts(rig):
    return ProfileVault(rig.database).pending_alerts("secreto")


async def test_al_arrancar_se_publica_que_perfiles_estan_protegidos(rig):
    assert rig.of(events.ProtectedProfilesChanged)[-1].profile_ids == {"secreto"}


async def test_un_perfil_sin_contrasena_abre_sesion_con_hey_jarvis(rig):
    await choose(rig, "trabajo")
    await wake(rig)
    assert rig.state is S.LISTENING_COMMAND
    assert rig.of(events.AccessChallenged) == []
    (opened,) = rig.of(events.SessionOpened)
    assert opened.profile_id == "trabajo"
    assert rig.spoken()[0] == said("ciclo.apertura")


async def test_hey_jarvis_en_un_perfil_protegido_pide_la_contrasena_sin_abrir_sesion(rig):
    await choose(rig, "secreto")
    await wake(rig)
    assert rig.state is S.DORMIDO
    assert rig.of(events.AccessChallenged) == [events.AccessChallenged("secreto", "Confidencial")]
    assert rig.of(events.SessionOpened) == []
    assert rig.spoken() == [said("seguridad.desafio")]
    # Hablar con la caja abierta no despierta al asistente: la pantalla sigue dormida.
    activities = {event.activity for event in rig.of(events.AssistantActivityChanged)}
    assert Activity.HABLANDO not in activities


async def test_abrir_sesion_desde_la_bandeja_tambien_pide_la_contrasena(rig):
    await choose(rig, "secreto")
    rig.app.bus.publish(events.OpenSessionRequested())
    await rig.advance(1.0)
    assert rig.state is S.DORMIDO
    assert len(rig.of(events.AccessChallenged)) == 1


async def test_la_contrasena_correcta_abre_la_sesion_con_la_frase_protegida(rig):
    await enter(rig)
    assert rig.state is S.LISTENING_COMMAND
    assert rig.of(events.AccessClosed) == [events.AccessClosed(granted=True)]
    (opened,) = rig.of(events.SessionOpened)
    assert opened.profile_id == "secreto"
    assert said("ciclo.apertura_protegida") in rig.spoken()
    assert said("ciclo.apertura") not in rig.spoken()


async def test_una_clave_incorrecta_se_rechaza_y_la_caja_sigue_abierta(rig):
    await choose(rig, "secreto")
    await wake(rig)
    await attempt(rig, "mala")
    assert rig.state is S.DORMIDO
    assert len(rig.of(events.AccessDenied)) == 1
    assert rig.of(events.AccessClosed) == []
    assert rig.spoken()[-1] == said("seguridad.denegado")
    assert pending_alerts(rig) == []


async def test_el_tercer_fallo_cierra_la_caja_y_registra_un_aviso_sin_decirlo(rig):
    await lock_out(rig)
    assert rig.state is S.DORMIDO
    assert rig.of(events.AccessClosed) == [events.AccessClosed(granted=False)]
    # Lo mismo que los fallos anteriores: nada delata el aviso.
    assert rig.spoken() == [said("seguridad.desafio"), *[said("seguridad.denegado")] * 3]
    assert rig.of(events.IntrusionAlertsShown) == []
    (alert,) = pending_alerts(rig)
    assert (alert.attempts, alert.origin.value) == (3, "inicio")


async def test_cancelar_no_reinicia_la_cuenta_de_fallos(rig):
    await choose(rig, "secreto")
    await wake(rig)
    await attempt(rig, "mala")
    await attempt(rig, "mala")
    rig.app.bus.publish(events.AccessCancelled())
    await rig.advance(1.0)
    assert rig.of(events.AccessClosed) == [events.AccessClosed(granted=False)]
    await wake(rig)
    await attempt(rig, "mala")
    assert len(pending_alerts(rig)) == 1


async def test_al_entrar_lo_primero_es_el_aviso_de_intrusion(rig):
    await lock_out(rig)
    rig.events.clear()
    await enter(rig)
    (shown,) = rig.of(events.IntrusionAlertsShown)
    assert shown.profile_id == "secreto"
    assert [item.attempts for item in shown.alerts] == [3]
    spoken = rig.spoken()
    opening = spoken.index(said("ciclo.apertura_protegida"))
    assert spoken[opening + 1].startswith("Alerta de seguridad")
    # Sin confirmar, sigue pendiente; al confirmarlo deja de estarlo.
    assert len(pending_alerts(rig)) == 1
    rig.app.bus.publish(events.IntrusionAcknowledged(tuple(i.alert_id for i in shown.alerts)))
    await rig.advance(0.1)
    assert pending_alerts(rig) == []


async def test_la_contrasena_no_aparece_en_ningun_evento_ni_en_el_registro(rig, caplog):
    caplog.set_level(logging.DEBUG)
    everything: list[events.Event] = []
    for event_type in (events.CommandReceived, events.SpeechStarted, events.AccessAttempted):
        rig.app.bus.subscribe(event_type, everything.append)
    await enter(rig)
    assert all(PASSWORD not in repr(event) for event in everything)
    assert all(PASSWORD not in repr(event) for event in rig.events)
    assert PASSWORD not in caplog.text
    assert rig.of(events.CommandReceived) == []
