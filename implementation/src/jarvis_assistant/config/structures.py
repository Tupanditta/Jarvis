"""`structures.toml`: estructuras de carpetas predefinidas (RF-97)."""
from dataclasses import dataclass

from jarvis_assistant.config.reader import REQUIRED, Reader


@dataclass(frozen=True)
class StructureDef:
    name: str
    folders: tuple[str, ...]


def parse_structures(reader: Reader) -> tuple[StructureDef, ...]:
    structures = []
    for item in reader.tables("structures") or []:
        structures.append(
            StructureDef(
                name=item.text("name", non_empty=True),
                folders=item.texts("folders", REQUIRED, non_empty=True),
            )
        )
        item.close()
    return tuple(structures)
