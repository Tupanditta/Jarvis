"""`places.toml` (lugares con nombre) y `aliases.toml` (sustituciones al normalizar)."""
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from jarvis_assistant.config.reader import Reader, text_table


def parse_places(reader: Reader) -> Mapping[str, Path]:
    places = text_table(reader, "places")
    return MappingProxyType({name: Path(value).expanduser() for name, value in places.items()})


def parse_aliases(reader: Reader) -> Mapping[str, str]:
    return MappingProxyType(text_table(reader, "aliases"))
