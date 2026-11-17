"""`profiles.toml`: perfiles de usuario.

Un perfil da el nombre del usuario (el que dice «preséntate») y la plantilla de pantalla que
se usa al abrir sesión. Se elige en la pantalla dormida, antes de abrir la sesión.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from jarvis_assistant.config.ids import is_valid_id
from jarvis_assistant.config.reader import InvalidError, Reader

DEFAULT_PROFILE_ID = "predeterminado"
DEFAULT_PROFILE_NAME = "Predeterminado"


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    user_name: str = ""  # para «preséntate»; vacío: no lo dice
    layout: str = ""  # id de la plantilla; vacío: la de fábrica


def default_profile(user_name: str = "") -> Profile:
    """El perfil que se usa cuando `profiles.toml` no define ninguno (migración desde
    `user.name`)."""
    return Profile(DEFAULT_PROFILE_ID, DEFAULT_PROFILE_NAME, user_name.strip())


def _parse_profile(item: Reader) -> Profile:
    profile_id = item.text("id", non_empty=True)
    if not is_valid_id(profile_id):
        raise InvalidError(item.key("id"), "solo minúsculas, números, - y _")
    profile = Profile(
        id=profile_id,
        name=item.text("name", non_empty=True).strip(),
        user_name=item.text("user_name", "").strip(),
        layout=item.text("layout", "").strip(),
    )
    item.close()
    return profile


def parse_profiles(reader: Reader) -> tuple[Profile, ...]:
    """Un perfil no válido se descarta con un error; los demás se cargan."""
    profiles: list[Profile] = []
    ids: set[str] = set()
    names: set[str] = set()
    for item in reader.tables("profiles") or []:
        try:
            profile = _parse_profile(item)
            if profile.id in ids:
                raise InvalidError(item.key("id"), f"el id «{profile.id}» está repetido")
            if profile.name.casefold() in names:
                raise InvalidError(item.key("name"), f"el nombre «{profile.name}» está repetido")
        except InvalidError as invalid:
            reader.error(invalid.key, invalid.reason)
            continue
        ids.add(profile.id)
        names.add(profile.name.casefold())
        profiles.append(profile)
    return tuple(profiles)


def dump_profiles(document: Any, profiles: Sequence[Profile]) -> None:
    """Sustituye la lista `[[profiles]]` de un documento `tomlkit`; conserva los comentarios."""
    import tomlkit

    if "profiles" in document:
        del document["profiles"]
    if not profiles:
        return
    array = tomlkit.aot()
    for profile in profiles:
        table = tomlkit.table()
        table["id"] = profile.id
        table["name"] = profile.name
        table["user_name"] = profile.user_name
        table["layout"] = profile.layout
        array.append(table)
    document["profiles"] = array
