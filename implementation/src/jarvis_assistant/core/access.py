"""Control de acceso: perfiles protegidos, permisos y la sesión del Acedor (arquitectura.md,
sección 4; perfiles-protegidos.md; permisos.md).

Perfiles protegidos: «Hey Jarvis» (o «Abrir sesión») en un perfil con contraseña no llega a
la FSM. Abre la caja de la contraseña (`AccessChallenged`); la contraseña llega en
`AccessAttempted`, sin pasar por el enrutador, y solo un acierto entra en la FSM como
`AccessGranted`. Los fallos y los avisos de intrusión los lleva `core/security.py`.

Permisos: al abrir sesión se calculan los módulos que el perfil puede usar. El enrutador no
muestra los demás en la ayuda y `run_task` rechaza sus acciones sin ejecutarlas. El Acedor solo
usa los módulos de administración (`admin = True`), que nadie más tiene.

Lo usa solo el orquestador. No ejecuta acciones: `run_task` sigue siendo la única función que
las ejecuta (AD-13); aquí solo se decide quién entra y qué módulos puede usar.
"""
import asyncio
import logging
from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING

from jarvis_assistant.config import ADMIN_PROFILE_ID, Config, Profile, admin_profile
from jarvis_assistant.core import events, permissions
from jarvis_assistant.core.action_api import ActionModule, Phrase
from jarvis_assistant.core.clock import Clock
from jarvis_assistant.core.content import IntrusionItem
from jarvis_assistant.core.custody import AdminKey
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.event_bus import EventBus
from jarvis_assistant.core.notices import Notice, NoticeQueue
from jarvis_assistant.core.repositories import PermissionRepository
from jarvis_assistant.core.security import AccessOrigin, AttemptOutcome, ProfileVault
from jarvis_assistant.core.state_machine import AssistantState
from jarvis_assistant.intent_router.router import CORE_MODULE
from jarvis_assistant.speaker import formats

if TYPE_CHECKING:
    from jarvis_assistant.intent_router.router import IntentRouter
    from jarvis_assistant.speaker.speaker import Speaker

logger = logging.getLogger(__name__)

RemoveProfile = Callable[[str], None]  # quita un perfil de `profiles.toml`


class _AdminTools:
    """`ActionContext.admin` en la sesión del Acedor: su clave, viva hasta cerrar la sesión."""

    def __init__(self, access: "Access", key: AdminKey) -> None:
        self._access = access
        self._key = key
        self.restrictable = access.restrictable()

    def credentials(self) -> list[tuple[str, str, str | None]]:
        access = self._access
        protected = access.vault.protected_ids()
        profiles = [p for p in access.config().all_profiles() if p.id in protected]
        revealed = access.vault.custody.reveal(self._key, [p.id for p in profiles])
        return [(p.id, p.name, revealed[p.id]) for p in profiles]

    def remove_profile(self, profile_id: str) -> bool:
        return self._access.remove_profile(profile_id)


class Access:
    """Quién entra en la sesión y qué módulos puede usar.

    `modules` y `panels`: los del orquestador, que los sigue llenando al registrar módulos.
    `config`: la configuración vigente. `state`: el estado de la FSM. `in_session`: hay una
    sesión abierta. `poke`: avisa al bucle del núcleo de que mire. `forget`: el orquestador
    quita de su configuración un perfil eliminado. `remove_file`: quita un perfil de
    `profiles.toml` (lo usa el Acedor).
    """

    def __init__(
        self,
        *,
        bus: EventBus,
        clock: Clock,
        database: Database,
        speaker: "Speaker",
        router: "IntentRouter",
        modules: Mapping[str, ActionModule],
        panels: Mapping[tuple[str, str], str | None],
        notices: NoticeQueue,
        config: Callable[[], Config],
        state: Callable[[], AssistantState],
        in_session: Callable[[], bool],
        poke: Callable[[], None],
        forget: Callable[[str], None],
        remove_file: RemoveProfile | None = None,
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._speaker = speaker
        self._router = router
        self._modules = modules
        self._panels = panels
        self._notices = notices
        self.config = config
        self._state = state
        self._in_session = in_session
        self._poke = poke
        self._forget = forget
        self.remove_file = remove_file
        self.vault = ProfileVault(database, clock.now)
        self._permissions = PermissionRepository(database)
        self._profile_id: str | None = None  # el elegido en la pantalla dormida
        self._gate: str | None = None  # perfil protegido cuya contraseña se está pidiendo
        self._gate_speech: asyncio.Task | None = None  # lo que se dice con la caja abierta
        self._allowed: frozenset[str] | None = None  # módulos del perfil de la sesión
        self.admin: _AdminTools | None = None  # solo en la sesión del Acedor

    # --- Perfil ------------------------------------------------------------------------------

    def select(self, profile_id: str | None) -> None:
        """`ProfileSelected`: el perfil elegido en la pantalla dormida."""
        self._profile_id = profile_id

    def profile(self) -> Profile:
        """El perfil elegido en la pantalla dormida o, si no existe, el primero. El Acedor solo
        si está activado."""
        if self._profile_id == ADMIN_PROFILE_ID and self.vault.admin_active():
            return admin_profile()
        return self.config().profile(self._profile_id)

    def end_session(self) -> None:
        """Al cerrar la sesión: la clave del Acedor no sobrevive a su sesión."""
        self.admin = None

    # --- Perfiles protegidos -----------------------------------------------------------------

    def publish_protection(self) -> None:
        self._bus.publish(events.ProtectedProfilesChanged(
            self.vault.protected_ids(), admin_active=self.vault.admin_active()
        ))  # fmt: skip

    def acknowledge(self, alert_ids: Iterable[int]) -> None:
        """`IntrusionAcknowledged`: el usuario ha confirmado los avisos de intrusión."""
        if self.admin is not None:
            self.vault.acknowledge_admin(alert_ids)
        else:
            self.vault.acknowledge(alert_ids)

    def challenge(self) -> bool:
        """«Hey Jarvis» en dormido. Si el perfil elegido tiene contraseña, abre la caja (o la
        vuelve a mostrar) y devuelve True: la sesión no se abre todavía."""
        profile = self.profile()
        if not self.vault.is_protected(profile.id):
            return False
        first = self._gate != profile.id
        self._gate = profile.id
        self._bus.publish(events.AccessChallenged(profile.id, profile.name))
        if first:
            self._speak_at_gate(Phrase("seguridad.desafio"))
        return True

    def attempt(self, password: str) -> bool:
        """`AccessAttempted`. True si la contraseña es la buena: la caja se ha cerrado y la
        FSM debe recibir `AccessGranted`."""
        profile_id = self._gate
        if profile_id is None or self._state() is not AssistantState.DORMIDO:
            return False
        outcome = self.vault.attempt(profile_id, password, AccessOrigin.LOGIN)
        if outcome is AttemptOutcome.GRANTED:
            logger.info("Acceso concedido al perfil %s", profile_id)
            if profile_id == ADMIN_PROFILE_ID:
                key = self.vault.open_admin(password)
                if key is None:  # contraseña válida pero claves dañadas o reiniciadas
                    logger.error("No se ha podido abrir la clave del Acedor")
                    self._bus.publish(events.AccessDenied())
                    self._speak_at_gate(Phrase("seguridad.denegado"))
                    return False
                self.admin = _AdminTools(self, key)
            self._profile_id = profile_id
            self.close_gate(granted=True)
            return True
        # El tercer fallo responde igual que los demás: quien lo intenta no sabe que ha
        # quedado registrado un aviso de intrusión.
        logger.info("Acceso denegado al perfil %s", profile_id)
        self._bus.publish(events.AccessDenied())
        self._speak_at_gate(Phrase("seguridad.denegado"))
        if outcome is AttemptOutcome.LOCKED_OUT:
            self._gate = None
            self._bus.publish(events.AccessClosed(granted=False))
        return False

    def close_gate(self, *, granted: bool) -> None:
        if self._gate is None:
            return
        self._gate = None
        self._speaker.stop()  # cancelar calla la frase; al acertar, la sesión trae la suya
        self._bus.publish(events.AccessClosed(granted=granted))

    def gate_speaking(self) -> bool:
        """Se está diciendo algo con la caja de la contraseña abierta, en dormido."""
        return (
            self._state() is AssistantState.DORMIDO
            and self._gate_speech is not None and not self._gate_speech.done()
        )  # fmt: skip

    def _speak_at_gate(self, phrase: Phrase) -> None:
        """Dice `phrase` en dormido, sin despertar al asistente. La salida de audio se abre
        para la frase y se cierra al terminar si no se ha abierto sesión entretanto."""
        self._speaker.stop()
        if self._gate_speech is None or self._gate_speech.done():
            self._speaker.open_output()
        self._gate_speech = speech = asyncio.ensure_future(self._say_at_gate(phrase))
        speech.add_done_callback(lambda _done: self._poke())

    async def _say_at_gate(self, phrase: Phrase) -> None:
        try:
            await self._speaker.say(phrase)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("No se ha podido decir %s", phrase.id)
        finally:
            if (
                self._gate_speech is asyncio.current_task() and not self._in_session()
                and self._state() is AssistantState.DORMIDO
            ):  # fmt: skip
                self._speaker.close_output()

    def queue_intrusion_alerts(self, profile_id: str) -> None:
        """Los avisos de intrusión sin confirmar van los primeros, tras la frase de apertura:
        se dicen y aparece la tarjeta crítica, que sigue hasta que el usuario la confirma."""
        admin = profile_id == ADMIN_PROFILE_ID
        alerts = self.vault.pending_admin_alerts() if admin else self.vault.pending_alerts(
            profile_id
        )
        if not alerts:
            return
        names = {p.id: p.name for p in (*self.config().all_profiles(), admin_profile())}
        last = alerts[-1]
        when = formats.moment(last.at, self._clock.now())
        if admin:
            phrase = Phrase("seguridad.intrusion_acedor", {"n": len(alerts), "cuando": when})
        elif len(alerts) == 1:
            phrase = Phrase("seguridad.intrusion", {"cuando": when, "intentos": last.attempts})
        else:
            phrase = Phrase("seguridad.intrusiones", {"n": len(alerts), "cuando": when})
        items = tuple(
            IntrusionItem(
                alert.id, alert.at, alert.attempts, alert.origin.value,
                names.get(alert.profile_id, alert.profile_id) if admin else "",
            )
            for alert in alerts
        )  # fmt: skip
        shown = events.IntrusionAlertsShown(profile_id, items)
        self._notices.add_first(Notice(phrase, on_start=lambda: self._bus.publish(shown)))

    # --- Permisos ----------------------------------------------------------------------------

    def restrictable(self) -> tuple[tuple[str, str], ...]:
        """Módulos y medidores que el Acedor puede conceder o restringir."""
        return permissions.restrictable(self._modules)

    def apply_permissions(self) -> None:
        """Al abrir sesión: los módulos del perfil, en el enrutador y en la interfaz."""
        profile_id = self.profile().id
        restricted = (
            () if profile_id == ADMIN_PROFILE_ID else self._permissions.restricted(profile_id)
        )
        scope = permissions.session_scope(
            self._modules, self._panels, profile_id, restricted, core_module=CORE_MODULE
        )
        self._allowed = scope.allowed
        self._router.set_scope(scope.allowed)
        self._bus.publish(events.PermissionsApplied(scope.hidden_panels))

    def permitted(self, module: str) -> bool:
        return self._allowed is None or module in self._allowed

    def remove_profile(self, profile_id: str) -> bool:
        """El Acedor elimina un perfil: fuera de `profiles.toml` y sus datos retirados."""
        if self.remove_file is None or profile_id == ADMIN_PROFILE_ID:
            return False
        try:
            self.remove_file(profile_id)
        except Exception:
            logger.exception("No se ha podido eliminar el perfil %s", profile_id)
            return False
        self.vault.retire(profile_id)
        self._forget(profile_id)
        return True
