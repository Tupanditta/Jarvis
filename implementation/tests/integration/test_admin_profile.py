"""El Acedor de principio a fin, con dobles: su sesión, permisos, credenciales y perfiles."""
import logging

import pytest

from integration.test_orders import RECORDED, Rig, said
from jarvis_assistant.config import ADMIN_PROFILE_ID, Config, Profile
from jarvis_assistant.core import events
from jarvis_assistant.core.custody import generate_keys
from jarvis_assistant.core.repositories import PermissionRepository, ReminderRepository
from jarvis_assistant.core.security import AccessOrigin, ProfileVault, hash_password
from jarvis_assistant.core.state_machine import AssistantState

S = AssistantState
ADMIN_PASSWORD = "maestra-1234"
WORK_PASSWORD = "clave-trabajo"
CONFIG = Config(profiles=(Profile("trabajo", "Trabajo"), Profile("casa", "Casa")))
EXTRA = (
    events.SessionOpened, events.ProtectedProfilesChanged, events.AccessChallenged,
    events.PermissionsApplied, events.PermissionsShown, events.CredentialsShown,
    events.ProfilesListed, events.IntrusionAlertsShown, events.DialogueOpened,
)  # fmt: skip


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    rig = Rig(tmp_path, monkeypatch, config=CONFIG)
    vault = ProfileVault(rig.database)
    vault.install_admin(hash_password(ADMIN_PASSWORD), *generate_keys(ADMIN_PASSWORD))
    vault.set_password_hash("trabajo", hash_password(WORK_PASSWORD))
    vault.custody.store("trabajo", WORK_PASSWORD)
    rig.removed = []
    rig.app.orchestrator._remove_profile_file = rig.removed.append
    for event_type in EXTRA:
        if event_type not in RECORDED:
            rig.app.bus.subscribe(event_type, rig.events.append)
    await rig.start()
    yield rig
    await rig.stop()


async def enter(rig, profile_id: str, password: str | None = None) -> None:
    rig.app.bus.publish(events.ProfileSelected(profile_id))
    await rig.advance(0.1)
    await rig.write("Hey Jarvis")
    await rig.advance(3.0)
    if password is not None:
        rig.app.bus.publish(events.AccessAttempted(password))
        await rig.advance(3.0)
    await rig.until(lambda: rig.app.orchestrator.modules["apertura"]._discovery.done())
    await rig.advance(1.0)


async def leave(rig) -> None:
    await rig.write("Buenas noches Jarvis")
    await rig.advance(5.0)
    assert rig.state is S.DORMIDO
    rig.events.clear()


def last(rig, kind):
    found = rig.of(kind)
    assert found, kind.__name__
    return found[-1]


async def test_el_selector_ofrece_al_acedor_cuando_esta_activado(rig):
    changed = last(rig, events.ProtectedProfilesChanged)
    assert changed.admin_active
    assert changed.profile_ids == {"trabajo", ADMIN_PROFILE_ID}


async def test_el_acedor_entra_con_su_contrasena_y_solo_ve_sus_modulos(rig):
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    assert rig.state is S.LISTENING_COMMAND
    assert last(rig, events.SessionOpened).profile_id == ADMIN_PROFILE_ID
    assert said("ciclo.apertura_protegida") in rig.spoken()
    hidden = last(rig, events.PermissionsApplied).hidden_panels
    assert {"comandos", "busqueda", "recordatorios"} <= hidden
    assert not hidden & {"permisos", "credenciales", "perfiles"}
    await rig.order("ayuda")
    modules = [group.module for group in last(rig, events.HelpShown).groups]
    assert set(modules) == {"permisos", "credenciales", "perfiles", "sesion", "nucleo"}


async def test_el_acedor_no_usa_los_modulos_normales(rig):
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    await rig.order("busca el archivo notas")
    assert rig.spoken()[-1] == said("permisos.denegado", modulo="Búsqueda")
    assert rig.of(events.SearchResultsReady) == []


async def test_el_acedor_ve_las_contrasenas_sin_que_se_digan(rig, caplog):
    caplog.set_level(logging.DEBUG)
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    await rig.order("muestra las contraseñas")
    (item,) = last(rig, events.CredentialsShown).items
    assert (item.profile_id, item.password) == ("trabajo", WORK_PASSWORD)
    assert rig.spoken()[-1] == said("credenciales.mostradas")
    assert all(WORK_PASSWORD not in text for text in rig.spoken())
    assert all(WORK_PASSWORD not in repr(event) for event in rig.events)
    assert WORK_PASSWORD not in caplog.text
    await leave(rig)
    assert rig.app.orchestrator._admin is None  # su clave no sobrevive a la sesión


async def test_restringir_un_modulo_lo_oculta_y_lo_rechaza_en_el_perfil(rig):
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    await rig.order("quita permiso de búsqueda a Casa")
    assert rig.spoken()[-1] == said("permisos.restringido", perfil="Casa", modulo="Búsqueda")
    assert ("casa", "busqueda") in last(rig, events.PermissionsShown).restricted
    await leave(rig)

    await enter(rig, "casa")
    assert "busqueda" in last(rig, events.PermissionsApplied).hidden_panels
    await rig.order("busca el archivo notas")
    assert rig.spoken()[-1] == said("permisos.denegado", modulo="Búsqueda")
    assert rig.of(events.SearchResultsReady) == []
    await rig.order("ayuda")
    assert "busqueda" not in [group.module for group in last(rig, events.HelpShown).groups]
    await leave(rig)

    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    await rig.order("da permiso de búsqueda a Casa")
    assert PermissionRepository(rig.database).restricted("casa") == frozenset()


async def test_los_medidores_se_restringen_como_un_modulo_y_se_ocultan(rig):
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    shown = last(rig, events.PermissionsShown)
    assert {"recursos", "ruido"} <= {module.id for module in shown.modules}
    await rig.order("quita permiso de ruido a Casa")
    assert rig.spoken()[-1] == said("permisos.restringido", perfil="Casa", modulo="Ruido")
    await leave(rig)

    await enter(rig, "casa")
    hidden = last(rig, events.PermissionsApplied).hidden_panels
    assert "ruido" in hidden and "recursos" not in hidden


async def test_un_perfil_normal_no_usa_los_modulos_del_acedor(rig):
    await enter(rig, "casa")
    hidden = last(rig, events.PermissionsApplied).hidden_panels
    assert {"permisos", "credenciales", "perfiles"} <= hidden
    await rig.order("muestra las contraseñas")
    assert rig.spoken()[-1] == said("permisos.denegado", modulo="Credenciales")
    assert rig.of(events.CredentialsShown) == [] or all(
        not event.items for event in rig.of(events.CredentialsShown)
    )


async def test_una_ventana_no_esquiva_un_permiso(rig):
    PermissionRepository(rig.database).set_allowed(
        "casa", "permisos", True, rig.clock.now()
    )  # ni concediéndolo: los del Acedor no son de nadie más
    await enter(rig, "casa")
    rig.app.bus.publish(events.PermissionChangeRequested("trabajo", "comandos", False))
    await rig.advance(1.0)
    assert PermissionRepository(rig.database).restricted("trabajo") == frozenset()
    assert rig.spoken()[-1] == said("permisos.denegado", modulo="Permisos")


async def test_el_acedor_elimina_un_perfil_tras_confirmarlo(rig):
    ReminderRepository(rig.database, "casa").create("Pan", [], None, rig.clock.now())
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    await rig.order("elimina el perfil Casa")
    assert rig.state is S.AWAITING_CONFIRMATION
    await rig.order("sí")
    assert rig.removed == ["casa"]
    assert rig.spoken()[-1] == said("perfiles.eliminado", perfil="Casa")
    assert ReminderRepository(rig.database, "casa").listable() == []
    assert [p.id for p in last(rig, events.ProfilesListed).profiles] == ["trabajo"]


async def test_el_acedor_recibe_los_avisos_de_intrusion_de_todos(rig):
    vault = ProfileVault(rig.database)
    for _ in range(3):
        vault.attempt("trabajo", "mala", AccessOrigin.LOGIN)
    await enter(rig, ADMIN_PROFILE_ID, ADMIN_PASSWORD)
    (shown,) = rig.of(events.IntrusionAlertsShown)
    assert [item.profile_name for item in shown.alerts] == ["Trabajo"]
    assert any(text.startswith("Alerta de seguridad") for text in rig.spoken())
    rig.app.bus.publish(events.IntrusionAcknowledged((shown.alerts[0].alert_id,)))
    await rig.advance(0.1)
    assert vault.pending_admin_alerts() == []
    assert len(vault.pending_alerts("trabajo")) == 1  # el dueño aún no lo ha visto
