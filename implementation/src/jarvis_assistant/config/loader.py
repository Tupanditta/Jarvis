"""La configuración completa y su carga desde los archivos TOML (RNF-26, AD-11).

Toda clave ausente toma el valor predeterminado del código; un archivo ausente o vacío es
válido. Cada archivo se valida por separado: si uno es inválido se conserva su configuración
anterior (o la predeterminada en el arranque) y el error indica archivo, clave y motivo.

Añadir un archivo es añadir su módulo (`dataclass` y `parse`), su campo en `Config` y su fila
en `PARSERS`.
"""
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from jarvis_assistant.config.catalog import Catalog, parse_catalog
from jarvis_assistant.config.commands import DEFAULT_BINARIES, Binary, parse_binaries
from jarvis_assistant.config.layouts import FACTORY_LAYOUT, ScreenLayout, parse_layouts
from jarvis_assistant.config.places import parse_aliases, parse_places
from jarvis_assistant.config.profiles import Profile, default_profile, parse_profiles
from jarvis_assistant.config.protocols import ProtocolDef, parse_protocols
from jarvis_assistant.config.reader import ConfigError, InvalidError, Reader, read_toml
from jarvis_assistant.config.settings import Settings, parse_settings
from jarvis_assistant.config.structures import StructureDef, parse_structures

DEFAULTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "config_defaults"


@dataclass(frozen=True)
class Config:
    settings: Settings = field(default_factory=Settings)
    catalog: Catalog = field(default_factory=Catalog)
    places: Mapping[str, Path] = field(default_factory=lambda: MappingProxyType({}))
    binaries: tuple[Binary, ...] = DEFAULT_BINARIES
    aliases: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    protocols: tuple[ProtocolDef, ...] = ()
    structures: tuple[StructureDef, ...] = ()
    profiles: tuple[Profile, ...] = ()
    layouts: tuple[ScreenLayout, ...] = ()

    def all_profiles(self) -> tuple[Profile, ...]:
        """Los perfiles definidos o, si no hay ninguno, el predeterminado con `user.name`."""
        return self.profiles or (default_profile(self.settings.user.name),)

    def profile(self, profile_id: str | None) -> Profile:
        """El perfil con ese id o, si no existe, el primero."""
        profiles = self.all_profiles()
        return next((p for p in profiles if p.id == profile_id), profiles[0])

    def all_layouts(self) -> tuple[ScreenLayout, ...]:
        """La plantilla de fábrica y las definidas."""
        return (FACTORY_LAYOUT, *self.layouts)

    def layout(self, layout_id: str) -> ScreenLayout:
        """La plantilla con ese id o, si no existe o está vacío, la de fábrica."""
        return next((item for item in self.layouts if item.id == layout_id), FACTORY_LAYOUT)


Parser = Callable[[Reader], Any]

# Archivo, campo de `Config` y función que lo lee.
PARSERS: tuple[tuple[str, str, Parser], ...] = (
    ("settings.toml", "settings", parse_settings),
    ("catalog.toml", "catalog", parse_catalog),
    ("places.toml", "places", parse_places),
    ("commands.toml", "binaries", parse_binaries),
    ("aliases.toml", "aliases", parse_aliases),
    ("protocols.toml", "protocols", parse_protocols),
    ("structures.toml", "structures", parse_structures),
    ("profiles.toml", "profiles", parse_profiles),
    ("layouts.toml", "layouts", parse_layouts),
)

CONFIG_FILES = tuple(name for name, _attribute, _parse in PARSERS)
_PARSER_OF = {name: parse for name, _attribute, parse in PARSERS}


def default_config() -> Config:
    """Configuración con todos los valores predeterminados del código."""
    return Config()


def install_defaults(config_dir: Path) -> list[Path]:
    """Copia a `config_dir` los archivos predeterminados que falten (primer arranque).

    Nunca sobrescribe un archivo existente. Devuelve los archivos creados.
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for name in CONFIG_FILES:
        target = config_dir / name
        source = DEFAULTS_DIR / name
        if not target.exists() and source.exists():
            shutil.copyfile(source, target)
            created.append(target)
    return created


def parse_data(name: str, data: Mapping[str, Any]) -> tuple[Any, list[ConfigError]]:
    """Lee el contenido ya decodificado del archivo `name`. Lanza `InvalidError` si el archivo
    es inválido; los problemas que no lo invalidan vuelven en la lista.

    Es la misma regla para el asistente al cargar y para la ventana de configuración al
    validar antes de guardar."""
    issues: list[ConfigError] = []
    reader = Reader(data, "", name, issues)
    value = _PARSER_OF[name](reader)
    reader.close()
    return value, issues


def check(name: str, data: Mapping[str, Any]) -> list[ConfigError]:
    """Problemas del contenido de `name`, sin cargarlo. Vacía si es válido."""
    try:
        _value, issues = parse_data(name, data)
    except InvalidError as invalid:
        return [ConfigError(name, invalid.key, invalid.reason)]
    return issues


def load(config_dir: Path, *, previous: Config | None = None) -> tuple[Config, list[ConfigError]]:
    """Carga la configuración de `config_dir`.

    Un archivo inválido conserva la parte de `previous` que le corresponde (los valores
    predeterminados si no hay `previous`) y añade un `ConfigError` a la lista devuelta.
    """
    fallback = previous if previous is not None else default_config()
    values: dict[str, Any] = {}
    errors: list[ConfigError] = []
    for name, attribute, _parse in PARSERS:
        try:
            values[attribute], issues = parse_data(name, read_toml(config_dir / name))
        except InvalidError as invalid:
            values[attribute] = getattr(fallback, attribute)
            errors.append(ConfigError(name, invalid.key, invalid.reason))
        else:
            errors.extend(issues)
    config = Config(**values)
    return config, errors + _cross_file_problems(config)


def _cross_file_problems(config: Config) -> list[ConfigError]:
    """Referencias entre archivos: un perfil con una plantilla que no existe usa la de
    fábrica."""
    known = {layout.id for layout in config.layouts}
    return [
        ConfigError(
            "profiles.toml", f"profiles.{profile.id}.layout",
            f"la plantilla «{profile.layout}» no existe; se usa la de fábrica", warning=True,
        )
        for profile in config.profiles
        if profile.layout and profile.layout not in known
    ]  # fmt: skip
