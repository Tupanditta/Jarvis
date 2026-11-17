"""`commands.toml`: lista cerrada de binarios que se pueden ejecutar (RN-45)."""
from dataclasses import dataclass

from jarvis_assistant.config.reader import InvalidError, Reader


@dataclass(frozen=True)
class Binary:
    """Binario permitido (RN-45)."""

    name: str
    executable: str  # nombre en el PATH o ruta absoluta
    aliases: tuple[str, ...] = ()
    timeout_seconds: float | None = None  # None = commands.default_timeout_seconds


DEFAULT_BINARIES = tuple(
    Binary(name, name) for name in ("git", "gcc", "g++", "make", "python", "pip", "node", "npm")
)


def parse_binaries(reader: Reader) -> tuple[Binary, ...]:
    items = reader.tables("binaries")
    if items is None:
        return DEFAULT_BINARIES
    binaries = []
    names: set[str] = set()
    for item in items:
        name = item.text("name", non_empty=True)
        if name.casefold() in names:
            raise InvalidError(item.key("name"), f"el binario «{name}» está repetido")
        names.add(name.casefold())
        binaries.append(
            Binary(
                name=name,
                executable=item.text("executable", non_empty=True),
                aliases=item.texts("aliases"),
                timeout_seconds=item.number("timeout_seconds", None, (1, 3600)),
            )
        )
        item.close()
    return tuple(binaries)
