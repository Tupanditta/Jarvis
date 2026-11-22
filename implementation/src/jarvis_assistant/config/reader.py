"""Lectura validada de tablas TOML, común a todos los archivos de configuración.

Cada archivo tiene su módulo con sus `dataclass` y su función `parse(reader)`. Este módulo
solo sabe leer claves comprobando su tipo y anotar las que sobran.
"""
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MISSING = object()
REQUIRED = object()


@dataclass(frozen=True)
class ConfigError:
    """Problema de un archivo de configuración.

    Con `warning` el archivo se ha cargado igualmente (clave desconocida). Sin él, o bien el
    archivo entero se ha sustituido por su configuración anterior, o bien (protocolos) se ha
    descartado el elemento que indica `key`.
    """

    file: str
    key: str
    reason: str
    warning: bool = False


class InvalidError(Exception):
    """Valor inválido que invalida el archivo (o el elemento) que lo contiene."""

    def __init__(self, key: str, reason: str) -> None:
        super().__init__(f"{key}: {reason}")
        self.key = key
        self.reason = reason


def read_toml(path: Path) -> dict[str, Any]:
    """Contenido de `path`; un archivo ausente equivale a uno vacío."""
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        return {}
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise InvalidError("", f"sintaxis TOML inválida: {error}") from error
    except OSError as error:
        raise InvalidError("", f"no se puede leer: {error}") from error


class Reader:
    """Lee las claves de una tabla TOML comprobando su tipo y anota las que sobran."""

    def __init__(
        self, data: Mapping[str, Any], prefix: str, file: str, issues: list[ConfigError]
    ) -> None:
        self._data = data
        self._prefix = prefix
        self._file = file
        self._issues = issues
        self._seen: set[str] = set()

    def key(self, name: str) -> str:
        return f"{self._prefix}.{name}" if self._prefix else name

    def has(self, name: str) -> bool:
        return name in self._data

    def _take(self, name: str, default: object) -> object:
        self._seen.add(name)
        value = self._data.get(name, MISSING)
        if value is MISSING and default is REQUIRED:
            raise InvalidError(self.key(name), "falta; es obligatoria")
        return value

    def text(
        self,
        name: str,
        default: object = REQUIRED,
        *,
        choices: frozenset[str] | None = None,
        non_empty: bool = False,
    ) -> Any:
        value = self._take(name, default)
        if value is MISSING:
            return default
        if not isinstance(value, str):
            raise InvalidError(self.key(name), "debe ser un texto")
        if choices is not None and value not in choices:
            raise InvalidError(self.key(name), "debe ser uno de: " + ", ".join(sorted(choices)))
        if non_empty and not value.strip():
            raise InvalidError(self.key(name), "no puede estar vacío")
        return value

    def boolean(self, name: str, default: object = REQUIRED) -> Any:
        value = self._take(name, default)
        if value is MISSING:
            return default
        if not isinstance(value, bool):
            raise InvalidError(self.key(name), "debe ser un booleano (true o false)")
        return value

    def integer(
        self, name: str, default: object = REQUIRED, bounds: tuple[float, float] | None = None
    ) -> Any:
        value = self._take(name, default)
        if value is MISSING:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidError(self.key(name), "debe ser un entero")
        self._check_bounds(name, value, bounds)
        return value

    def number(
        self, name: str, default: object = REQUIRED, bounds: tuple[float, float] | None = None
    ) -> Any:
        value = self._take(name, default)
        if value is MISSING:
            return default
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise InvalidError(self.key(name), "debe ser un número")
        self._check_bounds(name, value, bounds)
        return float(value)

    def _check_bounds(self, name: str, value: float, bounds: tuple[float, float] | None) -> None:
        if bounds is not None and not bounds[0] <= value <= bounds[1]:
            raise InvalidError(self.key(name), f"debe estar entre {bounds[0]:g} y {bounds[1]:g}")

    def texts(self, name: str, default: object = (), *, non_empty: bool = False) -> Any:
        value = self._take(name, default)
        if value is MISSING:
            return default
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InvalidError(self.key(name), "debe ser una lista de textos")
        if non_empty and (not value or not all(item.strip() for item in value)):
            raise InvalidError(self.key(name), "no puede estar vacía ni tener textos vacíos")
        return tuple(value)

    def table(self, name: str) -> "Reader":
        """Subtabla `name`; una tabla ausente equivale a una vacía."""
        value = self._take(name, None)
        if value is MISSING:
            value = {}
        if not isinstance(value, dict):
            raise InvalidError(self.key(name), "debe ser una tabla")
        return Reader(value, self.key(name), self._file, self._issues)

    def tables(self, name: str, default: object = None) -> "list[Reader] | None":
        """Lista de tablas `name`, o None si la clave no está."""
        value = self._take(name, default)
        if value is MISSING:
            return None
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise InvalidError(self.key(name), "debe ser una lista de tablas")
        return [
            Reader(item, f"{self.key(name)}[{index}]", self._file, self._issues)
            for index, item in enumerate(value)
        ]

    def items(self) -> list[tuple[str, Any]]:
        """Todas las claves de la tabla, para las tablas de contenido libre."""
        self._seen.update(self._data)
        return list(self._data.items())

    def error(self, key: str, reason: str) -> None:
        """Anota un error que descarta un elemento sin invalidar el archivo."""
        self._issues.append(ConfigError(self._file, key, reason))

    def warn(self, key: str, reason: str) -> None:
        """Anota un aviso: el archivo se carga igualmente."""
        self._issues.append(ConfigError(self._file, key, reason, warning=True))

    def close(self) -> None:
        """Avisa de las claves que nadie ha leído."""
        for name in self._data:
            if name not in self._seen:
                self.warn(self.key(name), "clave desconocida")


def text_table(reader: Reader, name: str) -> dict[str, str]:
    """Tabla de contenido libre cuyos valores son textos no vacíos."""
    table = reader.table(name)
    result = {}
    for key, value in table.items():
        if not isinstance(value, str) or not value.strip():
            raise InvalidError(table.key(key), "debe ser un texto no vacío")
        result[key] = value
    return result
