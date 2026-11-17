"""Perfiles protegidos: contraseña, intentos fallidos y avisos de intrusión.

Un perfil es un entorno de trabajo (Trabajo, Casa, Estudio…). Uno protegido pide su
contraseña antes de abrir sesión y antes de editarlo en la configuración. Tres fallos
seguidos, en cualquiera de los dos sitios y aunque se cancele entre medias, registran un
aviso de intrusión que el dueño recibe al entrar. Quien falla no sabe nada del aviso.

La contraseña nunca se guarda ni se registra: solo su hash scrypt con sal, en la base de datos
(tabla `profile_credentials`), no en `profiles.toml`. No hay recuperación: un perfil con la
contraseña olvidada solo se elimina quitándolo a mano de `profiles.toml`.

El Acedor (`ADMIN_PROFILE_ID`) es un perfil protegido más, con dos diferencias: tiene un par
de claves con el que puede ver las contraseñas de los demás (`core/custody.py`) y recibe los
avisos de intrusión de todos los perfiles, que confirma aparte del dueño.

Lo usan el orquestador (hilo del núcleo) y la ventana de configuración (hilo de la interfaz),
cada uno con su propia conexión a la base de datos.
"""
import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from jarvis_assistant.config.profiles import ADMIN_PROFILE_ID
from jarvis_assistant.core.custody import AdminKey, CredentialCustody
from jarvis_assistant.core.database import Database, from_db, to_db

PASSWORD_MIN_LENGTH = 4
MAX_ATTEMPTS = 3

# scrypt: coste de memoria 16 MiB, unas decenas de milisegundos por comprobación.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32
_SCHEME = "scrypt"


class AccessOrigin(StrEnum):
    """Dónde se ha pedido la contraseña."""

    LOGIN = "inicio"
    SETTINGS = "configuracion"


class AttemptOutcome(StrEnum):
    GRANTED = "concedido"
    DENIED = "denegado"  # clave incorrecta; aún quedan intentos
    LOCKED_OUT = "bloqueado"  # tercer fallo seguido: aviso registrado


@dataclass(frozen=True)
class IntrusionAlert:
    id: int
    profile_id: str
    at: datetime  # UTC
    attempts: int
    origin: AccessOrigin


def password_problem(password: str) -> str:
    """Por qué no vale como contraseña, en una frase para el usuario; vacío si vale."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
    return ""


def hash_password(password: str) -> str:
    """Hash con sal nueva: `scrypt$n$r$p$sal$clave`, en base64."""
    salt = secrets.token_bytes(_SALT_BYTES)
    key = _derive(password, salt, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P)
    encode = base64.b64encode
    return "$".join((
        _SCHEME, str(_SCRYPT_N), str(_SCRYPT_R), str(_SCRYPT_P),
        encode(salt).decode("ascii"), encode(key).decode("ascii"),
    ))  # fmt: skip


def verify_password(password: str, stored: str) -> bool:
    """Compara en tiempo constante. Un hash con formato desconocido no deja pasar a nadie."""
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != _SCHEME:
            return False
        expected = base64.b64decode(key, validate=True)
        actual = _derive(
            password, base64.b64decode(salt, validate=True), int(n), int(r), int(p),
            size=len(expected),
        )  # fmt: skip
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


def _derive(password: str, salt: bytes, n: int, r: int, p: int, size: int = _KEY_BYTES) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=size,
        maxmem=128 * n * r * p + 1024 * 1024,
    )  # fmt: skip


class ProfileVault:
    """Tablas `profile_credentials` e `intrusion_alerts`, y la regla de los tres intentos."""

    def __init__(
        self, db: Database, now: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._db = db
        self._now = now
        self.custody = CredentialCustody(db, now)

    # --- Consultas ---------------------------------------------------------------------------

    def is_protected(self, profile_id: str) -> bool:
        return self._hash_of(profile_id) is not None

    def protected_ids(self) -> frozenset[str]:
        rows = self._db.conn.execute(
            "SELECT profile_id FROM profile_credentials WHERE is_deleted = 0"
        ).fetchall()
        return frozenset(row["profile_id"] for row in rows)

    def pending_alerts(self, profile_id: str) -> list[IntrusionAlert]:
        """Avisos sin confirmar del perfil, del más antiguo al más reciente."""
        return self._alerts(
            "profile_id = ? AND acknowledged_at IS NULL", (profile_id,)
        )

    def pending_admin_alerts(self) -> list[IntrusionAlert]:
        """Avisos de todos los perfiles que el Acedor no ha confirmado."""
        return self._alerts("admin_acknowledged_at IS NULL", ())

    def _alerts(self, condition: str, args: tuple[object, ...]) -> list[IntrusionAlert]:
        rows = self._db.conn.execute(
            f"SELECT * FROM intrusion_alerts WHERE {condition} ORDER BY attempted_at, id", args
        ).fetchall()
        return [
            IntrusionAlert(
                id=row["id"], profile_id=row["profile_id"], at=from_db(row["attempted_at"]),
                attempts=row["attempts"], origin=AccessOrigin(row["origin"]),
            )
            for row in rows
        ]  # fmt: skip

    # --- Acceso ------------------------------------------------------------------------------

    def attempt(self, profile_id: str, password: str, origin: AccessOrigin) -> AttemptOutcome:
        """Comprueba la contraseña. Un acierto pone la cuenta de fallos a cero; el tercer
        fallo seguido registra un aviso de intrusión y la pone a cero. Un perfil sin
        contraseña siempre concede."""
        stored = self._hash_of(profile_id)
        if stored is None:
            return AttemptOutcome.GRANTED
        granted = verify_password(password, stored)
        with self._db.transaction() as conn:
            if granted:
                conn.execute(
                    "UPDATE profile_credentials SET failed_attempts = 0 WHERE profile_id = ?",
                    (profile_id,),
                )
                # Una contraseña anterior al Acedor solo era un hash: ahora se sella.
                if profile_id != ADMIN_PROFILE_ID and not self.custody.has(profile_id):
                    self.custody.store(profile_id, password)
                return AttemptOutcome.GRANTED
            failed = conn.execute(
                "UPDATE profile_credentials SET failed_attempts = failed_attempts + 1"
                " WHERE profile_id = ? RETURNING failed_attempts",
                (profile_id,),
            ).fetchone()["failed_attempts"]
            if failed < MAX_ATTEMPTS:
                return AttemptOutcome.DENIED
            conn.execute(
                "UPDATE profile_credentials SET failed_attempts = 0 WHERE profile_id = ?",
                (profile_id,),
            )
            conn.execute(
                "INSERT INTO intrusion_alerts (profile_id, attempted_at, attempts, origin)"
                " VALUES (?, ?, ?, ?)",
                (profile_id, to_db(self._now()), failed, origin.value),
            )
            return AttemptOutcome.LOCKED_OUT

    def acknowledge_admin(self, alert_ids: Iterable[int]) -> None:
        """El Acedor ha visto los avisos. Los de su propio perfil quedan vistos también como
        dueño."""
        ids = list(alert_ids)
        if not ids:
            return
        now = to_db(self._now())
        with self._db.transaction() as conn:
            conn.executemany(
                "UPDATE intrusion_alerts SET admin_acknowledged_at = ?"
                " WHERE id = ? AND admin_acknowledged_at IS NULL",
                [(now, alert_id) for alert_id in ids],
            )
            conn.executemany(
                "UPDATE intrusion_alerts SET acknowledged_at = ?"
                " WHERE id = ? AND profile_id = ? AND acknowledged_at IS NULL",
                [(now, alert_id, ADMIN_PROFILE_ID) for alert_id in ids],
            )

    def acknowledge(self, alert_ids: Iterable[int]) -> None:
        """El dueño ha visto los avisos."""
        ids = list(alert_ids)
        if not ids:
            return
        with self._db.transaction() as conn:
            conn.executemany(
                "UPDATE intrusion_alerts SET acknowledged_at = ?"
                " WHERE id = ? AND acknowledged_at IS NULL",
                [(to_db(self._now()), alert_id) for alert_id in ids],
            )

    # --- Gestión (configuración) -------------------------------------------------------------

    def set_password_hash(self, profile_id: str, password_hash: str) -> None:
        """Pone o cambia la contraseña (ya convertida en hash con `hash_password`)."""
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO profile_credentials (profile_id, password_hash, updated_at)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT (profile_id) DO UPDATE SET password_hash = excluded.password_hash,"
                " failed_attempts = 0, updated_at = excluded.updated_at, is_deleted = 0",
                (profile_id, password_hash, to_db(self._now())),
            )

    def clear_password(self, profile_id: str) -> None:
        """Quita la contraseña: el perfil deja de estar protegido."""
        self.custody.discard(profile_id)
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE profile_credentials SET is_deleted = 1, failed_attempts = 0,"
                " updated_at = ? WHERE profile_id = ?",
                (to_db(self._now()), profile_id),
            )

    def retire(self, profile_id: str) -> None:
        """El perfil se ha eliminado desde la configuración: sus recordatorios, su contraseña
        y sus avisos dejan de contar. Un perfil nuevo con el mismo id empieza limpio."""
        now = to_db(self._now())
        self.custody.discard(profile_id)
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE reminders SET status = 'eliminado'"
                " WHERE profile_id = ? AND status <> 'eliminado'",
                (profile_id,),
            )
            conn.execute(
                "UPDATE profile_credentials SET is_deleted = 1, failed_attempts = 0,"
                " updated_at = ? WHERE profile_id = ?",
                (now, profile_id),
            )
            conn.execute(
                "UPDATE intrusion_alerts SET acknowledged_at = ?"
                " WHERE profile_id = ? AND acknowledged_at IS NULL",
                (now, profile_id),
            )

    # --- Acedor ------------------------------------------------------------------------------

    def admin_active(self) -> bool:
        """El Acedor está activado: tiene contraseña y claves."""
        return self.is_protected(ADMIN_PROFILE_ID) and self.custody.active

    def install_admin(self, password_hash: str, public_key: str, private_key: str) -> None:
        """Activa al Acedor o cambia su contraseña (sus claves ya preparadas)."""
        with self._db.transaction():
            self.set_password_hash(ADMIN_PROFILE_ID, password_hash)
            self.custody.install(public_key, private_key)

    def open_admin(self, password: str) -> AdminKey | None:
        """La clave del Acedor para su sesión, o None si la contraseña no vale."""
        return self.custody.unlock(password)

    def reset_admin(self) -> None:
        """El Acedor ha olvidado su contraseña: deja de estar activo y las contraseñas
        custodiadas dejan de poder verse. Los permisos se conservan."""
        with self._db.transaction():
            self.clear_password(ADMIN_PROFILE_ID)
            self.custody.reset()

    # --- Interno -----------------------------------------------------------------------------

    def _hash_of(self, profile_id: str) -> str | None:
        row = self._db.conn.execute(
            "SELECT password_hash FROM profile_credentials"
            " WHERE profile_id = ? AND is_deleted = 0",
            (profile_id,),
        ).fetchone()
        return None if row is None else row["password_hash"]
