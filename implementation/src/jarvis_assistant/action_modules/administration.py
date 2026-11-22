"""Módulos del Acedor: Permisos, Credenciales y Perfiles.

Solo existen en la sesión del Acedor (`admin = True`): ningún otro perfil los tiene ni se le
pueden conceder. Lo que solo el Acedor tiene (su clave, la lista de módulos restringibles,
eliminar perfiles) llega en `ctx.admin`; sin él, no hacen nada.

- Permisos: dar y quitar permiso de un módulo a un perfil, y la tabla perfil × módulo.
- Credenciales: las contraseñas de los perfiles protegidos, en su ventana. Nunca se dicen en
  voz alta ni se escriben en el registro.
- Perfiles: eliminar un perfil, con confirmación. Ni el Acedor ni el último perfil.
"""
import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from jarvis_assistant.core.action_api import (
    ActionContext,
    ActionResult,
    ExpectedType,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.content import CredentialItem, NamedItem
from jarvis_assistant.core.events import (
    CredentialsShown,
    PermissionChangeRequested,
    PermissionsShown,
    ProfileRemovalRequested,
    ProfilesListed,
)
from jarvis_assistant.core.repositories import PermissionRepository

logger = logging.getLogger(__name__)

PERMISSIONS_PANEL = "permisos"
CREDENTIALS_PANEL = "credenciales"
PROFILES_PANEL = "perfiles"
MODULES_CATALOG = "modulos"
PROFILES_CATALOG = "perfiles"
REMOVABLE_CATALOG = "perfiles_eliminables"

UserActions = Mapping[type, Callable[[Any], tuple[str, Mapping[str, object]]]]


def _find(items: Sequence[NamedItem], wanted: object) -> NamedItem | None:
    """Por id o por nombre (la voz da el nombre; una ventana, el id)."""
    text = str(wanted or "").strip().casefold()
    return next(
        (item for item in items if text in (item.id.casefold(), item.name.casefold())), None
    )


def _profiles(ctx: ActionContext) -> tuple[NamedItem, ...]:
    """Los perfiles de `profiles.toml` (el Acedor no está en él)."""
    return tuple(NamedItem(p.id, p.name) for p in ctx.config.all_profiles())


def _not_admin() -> ActionResult:
    return ActionResult("error", Phrase("permisos.solo_acedor"))


class PermissionManager:
    """Dar y quitar permisos por módulo y perfil (tabla `profile_permissions`)."""

    name = "permisos"
    title = "Permisos"
    admin = True

    def __init__(self) -> None:
        self._profiles: tuple[NamedItem, ...] = ()
        self._modules: tuple[NamedItem, ...] = ()

    def intents(self) -> Sequence[IntentSpec]:
        target = (
            Slot("modulo", SlotType.CATALOG, catalog=MODULES_CATALOG),
            Slot("perfil", SlotType.CATALOG, catalog=PROFILES_CATALOG),
        )
        return (
            IntentSpec(
                "conceder",
                ("da permiso de {modulo} a {perfil}", "concede {modulo} a {perfil}",
                 "permite {modulo} a {perfil}", "autoriza {modulo} a {perfil}"),
                target, "Dar permiso", "Da permiso de comandos a Trabajo",
                panel=PERMISSIONS_PANEL, in_protocols=False,
            ),
            IntentSpec(
                "restringir",
                ("quita permiso de {modulo} a {perfil}", "restringe {modulo} a {perfil}",
                 "prohibe {modulo} a {perfil}", "quita {modulo} a {perfil}"),
                target, "Quitar permiso", "Quita permiso de comandos a Casa",
                panel=PERMISSIONS_PANEL, in_protocols=False,
            ),
            IntentSpec(
                "ver",
                ("muestra los permisos", "ver permisos", "permisos de los perfiles"),
                (), "Ver los permisos", "Muestra los permisos",
                panel=PERMISSIONS_PANEL, in_protocols=False, record=False,
            ),
        )  # fmt: skip

    def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]:
        return {
            MODULES_CATALOG: (lambda: [module.name for module in self._modules],),
            PROFILES_CATALOG: (lambda: [profile.name for profile in self._profiles],),
        }

    def user_actions(self) -> UserActions:
        return {
            PermissionChangeRequested: lambda event: (
                "conceder" if event.allowed else "restringir",
                {"perfil": event.profile_id, "modulo": event.module},
            )
        }

    async def on_session_opened(self, ctx: ActionContext) -> None:
        if ctx.admin is None:
            self._profiles, self._modules = (), ()
            return
        self._refresh(ctx)
        self._publish(ctx)

    def _refresh(self, ctx: ActionContext) -> None:
        self._profiles = _profiles(ctx)
        admin = ctx.admin
        self._modules = tuple(
            NamedItem(name, title) for name, title in (admin.restrictable if admin else ())
        )

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        if ctx.admin is None:
            return _not_admin()
        self._refresh(ctx)
        if action == "ver":
            self._publish(ctx)
            return ActionResult("completado", Phrase("permisos.mostrados"))
        profile = _find(self._profiles, params.get("perfil"))
        module = _find(self._modules, params.get("modulo"))
        if profile is None or module is None:
            return ActionResult("error", Phrase("permisos.no_encontrado"))
        allowed = {"conceder": True, "restringir": False}[action]
        PermissionRepository(ctx.db).set_allowed(profile.id, module.id, allowed, ctx.clock.now())
        logger.info("Permiso de %s para %s: %s", module.id, profile.id, allowed)
        self._publish(ctx)
        phrase = "permisos.concedido" if allowed else "permisos.restringido"
        return ActionResult(
            "completado", Phrase(phrase, {"modulo": module.name, "perfil": profile.name}),
            description=f"{module.name} {'permitido' if allowed else 'restringido'}"
            f" a {profile.name}",
        )  # fmt: skip

    def _publish(self, ctx: ActionContext) -> None:
        restricted = PermissionRepository(ctx.db).all_restricted()
        pairs = frozenset(
            (profile, module) for profile, modules in restricted.items() for module in modules
        )
        ctx.publish(PermissionsShown(self._profiles, self._modules, pairs))


class CredentialVault:
    """Las contraseñas de los perfiles protegidos, solo en su ventana."""

    name = "credenciales"
    title = "Credenciales"
    admin = True

    def intents(self) -> Sequence[IntentSpec]:
        return (
            IntentSpec(
                "ver",
                ("muestra las contraseñas", "ver contraseñas", "muestra las credenciales",
                 "contraseñas de los perfiles"),
                (), "Ver las contraseñas", "Muestra las contraseñas",
                panel=CREDENTIALS_PANEL, in_protocols=False, record=False,
            ),
        )  # fmt: skip

    async def on_session_opened(self, ctx: ActionContext) -> None:
        if ctx.admin is None:
            ctx.publish(CredentialsShown(()))  # la ventana no guarda nada de otra sesión

    async def on_session_closed(self, ctx: ActionContext) -> None:
        ctx.publish(CredentialsShown(()))  # al cerrar, la ventana las olvida

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        if ctx.admin is None or action != "ver":
            return _not_admin()
        items = tuple(
            CredentialItem(profile_id, name, password)
            for profile_id, name, password in ctx.admin.credentials()
        )
        ctx.publish(CredentialsShown(items))
        if not items:
            return ActionResult("completado", Phrase("credenciales.ninguna"))
        return ActionResult("completado", Phrase("credenciales.mostradas"))


class ProfileManager:
    """Eliminar perfiles: solo el Acedor, con confirmación."""

    name = "perfiles"
    title = "Perfiles"
    admin = True

    def __init__(self) -> None:
        self._profiles: tuple[NamedItem, ...] = ()

    def intents(self) -> Sequence[IntentSpec]:
        return (
            IntentSpec(
                "eliminar",
                ("elimina el perfil {perfil}", "borra el perfil {perfil}",
                 "quita el perfil {perfil}"),
                (Slot("perfil", SlotType.CATALOG, catalog=REMOVABLE_CATALOG),),
                "Eliminar un perfil", "Elimina el perfil Casa",
                panel=PROFILES_PANEL, in_protocols=False,
            ),
            IntentSpec(
                "ver",
                ("muestra los perfiles", "ver perfiles", "lista los perfiles"),
                (), "Ver los perfiles", "Muestra los perfiles",
                panel=PROFILES_PANEL, in_protocols=False, record=False,
            ),
        )  # fmt: skip

    def catalogs(self) -> Mapping[str, Sequence[Callable[[], Sequence[str]]]]:
        return {REMOVABLE_CATALOG: (lambda: [profile.name for profile in self._profiles],)}

    def user_actions(self) -> UserActions:
        return {
            ProfileRemovalRequested: lambda event: ("eliminar", {"perfil": event.profile_id})
        }

    async def on_session_opened(self, ctx: ActionContext) -> None:
        self._profiles = _profiles(ctx) if ctx.admin is not None else ()
        if ctx.admin is not None:
            ctx.publish(ProfilesListed(self._profiles))

    async def execute(
        self, action: str, params: Mapping[str, object], ctx: ActionContext
    ) -> ActionResult:
        if ctx.admin is None:
            return _not_admin()
        if action == "ver":
            ctx.publish(ProfilesListed(self._profiles))
            return ActionResult("completado", Phrase("perfiles.mostrados"))
        assert action == "eliminar"
        profile = _find(self._profiles, params.get("perfil"))
        if profile is None:
            return ActionResult("error", Phrase("permisos.no_encontrado"))
        if len(self._profiles) <= 1:
            return ActionResult("error", Phrase("perfiles.ultimo"))
        answer = await ctx.ask(
            Phrase("perfiles.confirmar", {"perfil": profile.name}), ExpectedType.BOOLEAN,
            subject={"perfil": profile.name},
        )  # fmt: skip
        if answer.cancelled or answer.value is not True:
            return ActionResult.cancelled(Phrase("general.operacion_cancelada"))
        if not ctx.admin.remove_profile(profile.id):
            return ActionResult("error", Phrase("perfiles.no_eliminado"))
        self._profiles = tuple(p for p in self._profiles if p.id != profile.id)
        ctx.publish(ProfilesListed(self._profiles))
        return ActionResult(
            "completado", Phrase("perfiles.eliminado", {"perfil": profile.name}),
            description=f"Perfil {profile.name} eliminado",
        )  # fmt: skip
