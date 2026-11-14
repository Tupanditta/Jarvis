"""Elección del dispositivo de entrada y de su API de audio (captura-audio.md). Lógica pura.

En Windows un mismo micrófono aparece una vez por cada API y no todas se comportan igual.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

EXCLUDED_API = "Windows WDM-KS"
WINDOWS_API_PREFERENCE = ("MME", "Windows WASAPI", "Windows DirectSound")


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    hostapi: str
    channels: int
    samplerate: float
    is_api_default: bool  # es la entrada predeterminada de su API


@dataclass(frozen=True)
class DeviceChoice:
    """Dispositivo elegido. Sin `device`, se usa el predeterminado del sistema."""

    device: InputDevice | None
    warning: str | None = None


def from_sounddevice(
    devices: Sequence[Mapping[str, object]], hostapis: Sequence[Mapping[str, object]]
) -> list[InputDevice]:
    """Convierte las listas de `sounddevice.query_devices` y `query_hostapis`."""
    result = []
    for position, device in enumerate(devices):
        api = hostapis[int(device["hostapi"])]  # type: ignore[call-overload]
        index = int(device.get("index", position))  # type: ignore[call-overload]
        result.append(
            InputDevice(
                index=index,
                name=str(device["name"]),
                hostapi=str(api["name"]),
                channels=int(device["max_input_channels"]),  # type: ignore[call-overload]
                samplerate=float(device["default_samplerate"]),  # type: ignore[arg-type]
                is_api_default=api.get("default_input_device") == index,
            )
        )
    return result


def select_input_device(
    devices: Sequence[InputDevice],
    *,
    wanted_name: str = "",
    wanted_hostapi: str = "",
    api_preference: Sequence[str] = WINDOWS_API_PREFERENCE,
) -> DeviceChoice:
    usable = [d for d in devices if d.channels > 0 and d.hostapi != EXCLUDED_API]
    if wanted_name:
        named = [d for d in usable if wanted_name.casefold() in d.name.casefold()]
    else:
        named = [d for d in usable if d.is_api_default]
    if wanted_hostapi:
        candidates = [d for d in named if d.hostapi.casefold() == wanted_hostapi.casefold()]
    else:
        candidates = sorted(named, key=lambda d: _api_rank(d.hostapi, api_preference))
    if candidates:
        return DeviceChoice(candidates[0])
    if not wanted_name and not wanted_hostapi:
        return DeviceChoice(None)
    available = ", ".join(f"{d.name} [{d.hostapi}]" for d in usable) or "ninguna"
    wanted = f"dispositivo {wanted_name!r}, API {wanted_hostapi!r}"
    return DeviceChoice(
        None,
        f"No hay ninguna entrada para {wanted}; se usa la predeterminada del sistema. "
        f"Entradas disponibles: {available}",
    )


def _api_rank(hostapi: str, preference: Sequence[str]) -> int:
    return preference.index(hostapi) if hostapi in preference else len(preference)
