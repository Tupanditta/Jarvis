"""Permisos por perfil (`core/permissions.py`): alcance de la sesión y lo restringible."""
from dataclasses import dataclass

from jarvis_assistant.config import ADMIN_PROFILE_ID, METERS
from jarvis_assistant.core.permissions import restrictable, session_scope

CORE = "nucleo"


@dataclass
class FakeModule:
    name: str
    title: str
    admin: bool = False
    always_allowed: bool = False


MODULES = {
    module.name: module
    for module in (
        FakeModule("comandos", "Comandos"),
        FakeModule("recordatorio", "Recordatorios"),
        FakeModule("sesion", "Sesión", always_allowed=True),
        FakeModule("administracion", "Administración", admin=True),
    )
}
PANELS = {
    ("comandos", "ls"): "comandos",
    ("recordatorio", "crear"): "recordatorios",
    ("recordatorio", "listar"): "recordatorios",
    ("sesion", "historial"): "historial",
    ("administracion", "permisos"): "permisos",
    ("comandos", "cd"): None,
}
METER = METERS[0].id


def test_sin_restricciones_un_perfil_usa_todo_menos_la_administracion():
    scope = session_scope(MODULES, PANELS, "perfil", (), core_module=CORE)
    assert scope.allowed == {CORE, "comandos", "recordatorio", "sesion"}
    assert scope.hidden_panels == {"permisos"}


def test_lo_restringido_no_se_usa_y_su_panel_se_oculta():
    scope = session_scope(MODULES, PANELS, "perfil", ("recordatorio", METER), core_module=CORE)
    assert scope.allowed == {CORE, "comandos", "sesion"}
    assert scope.hidden_panels == {"permisos", "recordatorios", METER}


def test_lo_que_se_necesita_siempre_no_se_puede_restringir():
    scope = session_scope(MODULES, PANELS, "perfil", ("sesion", CORE), core_module=CORE)
    assert {"sesion", CORE} <= scope.allowed


def test_el_acedor_solo_usa_la_administracion_y_ve_los_medidores():
    scope = session_scope(MODULES, PANELS, ADMIN_PROFILE_ID, (METER,), core_module=CORE)
    assert scope.allowed == {CORE, "sesion", "administracion"}
    assert scope.hidden_panels == {"comandos", "recordatorios"}


def test_un_panel_que_comparte_un_modulo_permitido_no_se_oculta():
    panels = {**PANELS, ("administracion", "ver"): "comandos"}
    scope = session_scope(MODULES, panels, "perfil", (), core_module=CORE)
    assert "comandos" not in scope.hidden_panels


def test_restringible_son_los_modulos_normales_y_los_medidores():
    assert restrictable(MODULES) == (
        ("comandos", "Comandos"), ("recordatorio", "Recordatorios"),
        *((meter.id, meter.title) for meter in METERS),
    )  # fmt: skip
