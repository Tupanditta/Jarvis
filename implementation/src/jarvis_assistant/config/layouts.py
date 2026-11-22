"""`layouts.toml`: plantillas de la pantalla de sesión.

Una plantilla dice qué ventanas flotantes se muestran al abrir sesión, dónde y con qué tamaño,
y dónde van la barra superior (selector de ventanas) y la inferior (caja de texto). Todo en
fracciones de la pantalla, para que valga en cualquier resolución.

Las ventanas se nombran por su id (`ui/workspace.py`, `WINDOWS`). Este módulo no conoce el
registro: una ventana que la plantilla no nombra toma su disposición de fábrica, y la interfaz
ignora las que ya no existen.

La plantilla dice también qué medidores (`METERS`) se ven al abrir sesión. Un medidor que no
nombra toma su valor de fábrica.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from jarvis_assistant.config.ids import is_valid_id
from jarvis_assistant.config.reader import InvalidError, Reader

FACTORY_LAYOUT_ID = "fabrica"
FACTORY_LAYOUT_NAME = "Fábrica"

MIN_WINDOW_FRACTION = 0.08  # igual que `ui/workspace.py`
MIN_INPUT_WIDTH = 0.1

_UNIT = (0.0, 1.0)
_WINDOW_SIZE = (MIN_WINDOW_FRACTION, 1.0)


@dataclass(frozen=True)
class MeterSpec:
    """Medidor de la pantalla de sesión. No es una ventana ni un módulo de acción, pero las
    plantillas dicen si se ve al abrir sesión y el Acedor puede restringirlo como un módulo
    (su id es el del permiso)."""

    id: str
    title: str
    shown: bool  # a la vista en la disposición de fábrica


METERS: tuple[MeterSpec, ...] = (
    MeterSpec("recursos", "Recursos", True),  # CPU y RAM del asistente
    MeterSpec("ruido", "Ruido", False),  # decibelios alrededor
)
METER_IDS = frozenset(meter.id for meter in METERS)


@dataclass(frozen=True)
class BarPosition:
    """Centro de una barra, en fracciones de la pantalla."""

    x: float
    y: float


@dataclass(frozen=True)
class WindowPlacement:
    """Disposición inicial de una ventana flotante."""

    open: bool
    x: float
    y: float
    width: float
    height: float
    order: int = 0  # apilado: la mayor queda encima


DEFAULT_DOCK = BarPosition(0.5, 0.032)
DEFAULT_INPUT = BarPosition(0.5, 0.935)
DEFAULT_INPUT_WIDTH = 0.235


@dataclass(frozen=True)
class ScreenLayout:
    id: str
    name: str
    dock: BarPosition = DEFAULT_DOCK
    input: BarPosition = DEFAULT_INPUT
    input_width: float = DEFAULT_INPUT_WIDTH
    windows: Mapping[str, WindowPlacement] = field(
        default_factory=lambda: MappingProxyType({})
    )
    meters: Mapping[str, bool] = field(  # id del medidor → a la vista al abrir sesión
        default_factory=lambda: MappingProxyType({})
    )

    def meter_shown(self, meter: MeterSpec) -> bool:
        return self.meters.get(meter.id, meter.shown)


# Siempre existe, no se edita ni se elimina. Sin ventanas: todas toman su disposición de
# fábrica del registro de la interfaz.
FACTORY_LAYOUT = ScreenLayout(FACTORY_LAYOUT_ID, FACTORY_LAYOUT_NAME)


def _parse_bar(reader: Reader, name: str, default: BarPosition) -> BarPosition:
    table = reader.table(name)
    bar = BarPosition(table.number("x", default.x, _UNIT), table.number("y", default.y, _UNIT))
    table.close()
    return bar


def _parse_layout(item: Reader) -> ScreenLayout:
    layout_id = item.text("id", non_empty=True)
    if not is_valid_id(layout_id):
        raise InvalidError(item.key("id"), "solo minúsculas, números, - y _")
    if layout_id == FACTORY_LAYOUT_ID:
        raise InvalidError(item.key("id"), f"«{FACTORY_LAYOUT_ID}» está reservado")
    name = item.text("name", non_empty=True).strip()
    dock = _parse_bar(item, "dock", DEFAULT_DOCK)
    input_table = item.table("input")
    bar_input = BarPosition(
        input_table.number("x", DEFAULT_INPUT.x, _UNIT),
        input_table.number("y", DEFAULT_INPUT.y, _UNIT),
    )
    input_width = input_table.number("width", DEFAULT_INPUT_WIDTH, (MIN_INPUT_WIDTH, 1.0))
    input_table.close()
    windows_table = item.table("windows")
    windows: dict[str, WindowPlacement] = {}
    for window_id, _value in windows_table.items():
        window = windows_table.table(window_id)
        windows[window_id] = WindowPlacement(
            open=window.boolean("open", False),
            x=window.number("x", 0.0, _UNIT),
            y=window.number("y", 0.0, _UNIT),
            width=window.number("width", 0.2, _WINDOW_SIZE),
            height=window.number("height", 0.3, _WINDOW_SIZE),
            order=window.integer("order", 0, (0, 1000)),
        )
        window.close()
    meters_table = item.table("meters")
    meters = {
        meter_id: meters_table.boolean(meter_id, False) for meter_id, _value in meters_table.items()
    }
    meters_table.close()
    item.close()
    return ScreenLayout(
        layout_id, name, dock, bar_input, input_width, MappingProxyType(windows),
        MappingProxyType(meters),
    )  # fmt: skip


def parse_layouts(reader: Reader) -> tuple[ScreenLayout, ...]:
    """Una plantilla no válida se descarta con un error; las demás se cargan."""
    layouts: list[ScreenLayout] = []
    ids: set[str] = set()
    names: set[str] = {FACTORY_LAYOUT_NAME.casefold()}
    for item in reader.tables("layouts") or []:
        try:
            layout = _parse_layout(item)
            if layout.id in ids:
                raise InvalidError(item.key("id"), f"el id «{layout.id}» está repetido")
            if layout.name.casefold() in names:
                raise InvalidError(item.key("name"), f"el nombre «{layout.name}» está repetido")
        except InvalidError as invalid:
            reader.error(invalid.key, invalid.reason)
            continue
        ids.add(layout.id)
        names.add(layout.name.casefold())
        layouts.append(layout)
    return tuple(layouts)


def dump_layouts(document: Any, layouts: Sequence[ScreenLayout]) -> None:
    """Sustituye la lista `[[layouts]]` de un documento `tomlkit`; conserva los comentarios."""
    import tomlkit

    if "layouts" in document:
        del document["layouts"]
    if not layouts:
        return
    array = tomlkit.aot()
    for layout in layouts:
        table = tomlkit.table()
        table["id"] = layout.id
        table["name"] = layout.name
        dock = tomlkit.table()
        dock["x"] = round(layout.dock.x, 4)
        dock["y"] = round(layout.dock.y, 4)
        table["dock"] = dock
        bar = tomlkit.table()
        bar["x"] = round(layout.input.x, 4)
        bar["y"] = round(layout.input.y, 4)
        bar["width"] = round(layout.input_width, 4)
        table["input"] = bar
        windows = tomlkit.table(is_super_table=True)
        for window_id, placement in layout.windows.items():
            window = tomlkit.table()
            window["open"] = placement.open
            window["x"] = round(placement.x, 4)
            window["y"] = round(placement.y, 4)
            window["width"] = round(placement.width, 4)
            window["height"] = round(placement.height, 4)
            window["order"] = placement.order
            windows[window_id] = window
        if layout.windows:
            table["windows"] = windows
        if layout.meters:
            meters = tomlkit.table()
            for meter_id, shown in layout.meters.items():
                meters[meter_id] = shown
            table["meters"] = meters
        array.append(table)
    document["layouts"] = array
