"""Custodia de contraseñas para el Acedor (X25519 + AES-GCM).

El Acedor puede ver las contraseñas de los perfiles protegidos, aunque las pongan otros sin
estar él. Para eso tiene un par de claves X25519:

- La clave pública está en claro: cualquiera sella con ella una contraseña (X25519 efímera,
  HKDF-SHA256 y AES-GCM). Solo la privada abre el sello.
- La clave privada se guarda cifrada con una clave derivada de la contraseña del Acedor
  (scrypt + AES-GCM). Solo se descifra al entrar el Acedor y vive en memoria hasta cerrar su
  sesión (`AdminKey`).

Si el Acedor olvida su contraseña se reinicia (`reset`): sus claves y todos los sellos se
marcan como borrados y las contraseñas dejan de poder verse. Las contraseñas de los perfiles
(sus hash, en `profile_credentials`) siguen funcionando.

Ni las contraseñas ni la clave privada se escriben en el registro.
"""
import base64
import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from jarvis_assistant.core.database import Database, to_db

_VERSION = "v1"
_SALT_BYTES = 16
_NONCE_BYTES = 12
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32, "maxmem": 64 * 1024 * 1024}
_PRIVATE_AAD = b"jarvis/acedor/clave-privada"
_SEAL_INFO = b"jarvis/acedor/credencial"

_RAW = serialization.Encoding.Raw
_RAW_PUBLIC = serialization.PublicFormat.Raw
_RAW_PRIVATE = serialization.PrivateFormat.Raw


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text, validate=True)


def _password_key(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)


def _public_bytes(key: X25519PublicKey) -> bytes:
    return key.public_bytes(_RAW, _RAW_PUBLIC)


def generate_keys(password: str) -> tuple[str, str]:
    """Par nuevo: (clave pública, clave privada cifrada con `password`)."""
    private = X25519PrivateKey.generate()
    return _b64(_public_bytes(private.public_key())), _encrypt_private(private, password)


def _encrypt_private(private: X25519PrivateKey, password: str) -> str:
    raw = private.private_bytes(_RAW, _RAW_PRIVATE, serialization.NoEncryption())
    salt, nonce = secrets.token_bytes(_SALT_BYTES), secrets.token_bytes(_NONCE_BYTES)
    sealed = AESGCM(_password_key(password, salt)).encrypt(nonce, raw, _PRIVATE_AAD)
    return "$".join((_VERSION, _b64(salt), _b64(nonce), _b64(sealed)))


def decrypt_private(encrypted: str, password: str) -> X25519PrivateKey | None:
    """La clave privada, o None si la contraseña no es la del Acedor."""
    try:
        version, salt, nonce, sealed = encrypted.split("$")
        if version != _VERSION:
            return None
        raw = AESGCM(_password_key(password, _unb64(salt))).decrypt(
            _unb64(nonce), _unb64(sealed), _PRIVATE_AAD
        )
    except (ValueError, InvalidTag):
        return None
    return X25519PrivateKey.from_private_bytes(raw)


def rewrap_private(encrypted: str, current: str, new: str) -> str | None:
    """La misma clave privada, cifrada con la contraseña nueva; None si `current` no vale."""
    private = decrypt_private(encrypted, current)
    return None if private is None else _encrypt_private(private, new)


def _seal_key(shared: bytes, ephemeral: bytes, recipient: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_SEAL_INFO + ephemeral + recipient
    ).derive(shared)


def seal(public_key: str, secret: str) -> str:
    """Sella `secret` para el dueño de `public_key`."""
    recipient = X25519PublicKey.from_public_bytes(_unb64(public_key))
    ephemeral = X25519PrivateKey.generate()
    ephemeral_public = _public_bytes(ephemeral.public_key())
    key = _seal_key(ephemeral.exchange(recipient), ephemeral_public, _unb64(public_key))
    nonce = secrets.token_bytes(_NONCE_BYTES)
    sealed = AESGCM(key).encrypt(nonce, secret.encode("utf-8"), ephemeral_public)
    return "$".join((_VERSION, _b64(ephemeral_public), _b64(nonce), _b64(sealed)))


class AdminKey:
    """La clave privada del Acedor, descifrada. Solo existe durante su sesión."""

    def __init__(self, private: X25519PrivateKey) -> None:
        self._private = private
        self._public = _public_bytes(private.public_key())

    def __repr__(self) -> str:
        return "AdminKey(<oculta>)"

    def open(self, sealed: str) -> str | None:
        """El secreto sellado, o None si no es para esta clave o está dañado."""
        try:
            version, ephemeral, nonce, data = sealed.split("$")
            if version != _VERSION:
                return None
            ephemeral_public = _unb64(ephemeral)
            shared = self._private.exchange(X25519PublicKey.from_public_bytes(ephemeral_public))
            key = _seal_key(shared, ephemeral_public, self._public)
            plain = AESGCM(key).decrypt(_unb64(nonce), _unb64(data), ephemeral_public)
        except (ValueError, InvalidTag):
            return None
        return plain.decode("utf-8")


class CredentialCustody:
    """Tablas `admin_keys` y `credential_escrow`."""

    def __init__(self, db: Database, now: Callable[[], datetime]) -> None:
        self._db = db
        self._now = now

    # --- Claves del Acedor -------------------------------------------------------------------

    def _keys(self) -> tuple[int, str, str] | None:
        row = self._db.conn.execute(
            "SELECT id, public_key, private_key FROM admin_keys WHERE is_deleted = 0"
            " ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return None if row is None else (row["id"], row["public_key"], row["private_key"])

    @property
    def active(self) -> bool:
        return self._keys() is not None

    def public_key(self) -> str | None:
        keys = self._keys()
        return None if keys is None else keys[1]

    def private_key(self) -> str | None:
        """La clave privada cifrada (para cambiar la contraseña del Acedor)."""
        keys = self._keys()
        return None if keys is None else keys[2]

    def install(self, public_key: str, private_key: str) -> None:
        """Claves nuevas del Acedor; las anteriores y sus sellos dejan de valer."""
        now = to_db(self._now())
        with self._db.transaction() as conn:
            if self.public_key() != public_key:
                conn.execute("UPDATE admin_keys SET is_deleted = 1 WHERE is_deleted = 0")
                conn.execute(
                    "INSERT INTO admin_keys (public_key, private_key, created_at)"
                    " VALUES (?, ?, ?)",
                    (public_key, private_key, now),
                )
                conn.execute(
                    "UPDATE credential_escrow SET is_deleted = 1, updated_at = ?"
                    " WHERE is_deleted = 0",
                    (now,),
                )
            else:  # misma clave, otra contraseña del Acedor
                conn.execute(
                    "UPDATE admin_keys SET private_key = ? WHERE is_deleted = 0", (private_key,)
                )

    def unlock(self, password: str) -> AdminKey | None:
        encrypted = self.private_key()
        if encrypted is None:
            return None
        private = decrypt_private(encrypted, password)
        return None if private is None else AdminKey(private)

    def reset(self) -> None:
        """El Acedor olvida su contraseña: claves y sellos dejan de valer."""
        now = to_db(self._now())
        with self._db.transaction() as conn:
            conn.execute("UPDATE admin_keys SET is_deleted = 1 WHERE is_deleted = 0")
            conn.execute(
                "UPDATE credential_escrow SET is_deleted = 1, updated_at = ?"
                " WHERE is_deleted = 0",
                (now,),
            )

    # --- Sellos ------------------------------------------------------------------------------

    def seal(self, secret: str) -> str | None:
        """`secret` sellado para el Acedor; None si no hay Acedor activo."""
        public_key = self.public_key()
        return None if public_key is None else seal(public_key, secret)

    def has(self, profile_id: str) -> bool:
        return self.sealed(profile_id) is not None

    def sealed(self, profile_id: str) -> str | None:
        row = self._db.conn.execute(
            "SELECT sealed FROM credential_escrow WHERE profile_id = ? AND is_deleted = 0",
            (profile_id,),
        ).fetchone()
        return None if row is None else row["sealed"]

    def store_sealed(self, profile_id: str, sealed: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO credential_escrow (profile_id, sealed, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT (profile_id) DO UPDATE SET sealed = excluded.sealed,"
                " updated_at = excluded.updated_at, is_deleted = 0",
                (profile_id, sealed, to_db(self._now())),
            )

    def store(self, profile_id: str, secret: str) -> None:
        """Sella y guarda la contraseña de un perfil, si hay Acedor activo."""
        sealed = self.seal(secret)
        if sealed is not None:
            self.store_sealed(profile_id, sealed)

    def discard(self, profile_id: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE credential_escrow SET is_deleted = 1, updated_at = ?"
                " WHERE profile_id = ? AND is_deleted = 0",
                (to_db(self._now()), profile_id),
            )

    def reveal(self, key: AdminKey, profile_ids: list[str]) -> dict[str, str | None]:
        """La contraseña de cada perfil, o None si no está sellada (todavía)."""
        return {
            profile_id: None if (sealed := self.sealed(profile_id)) is None else key.open(sealed)
            for profile_id in profile_ids
        }
