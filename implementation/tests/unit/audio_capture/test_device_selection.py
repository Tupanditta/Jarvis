"""Elección de dispositivo y API con listas sin hardware (captura-audio.md)."""
from jarvis_assistant.audio_capture.device_selection import (
    InputDevice,
    from_sounddevice,
    select_input_device,
)


def device(index, name, api, *, channels=2, default=False):
    return InputDevice(index, name, api, channels, 48000.0, default)


DEVICES = [
    device(0, "Asignador de sonido Microsoft - Input", "MME"),
    device(1, "Micrófono (USB Audio)", "MME", default=True),
    device(2, "Varios micrófonos (Realtek)", "MME"),
    device(3, "Altavoces (Realtek)", "MME", channels=0),
    device(4, "Micrófono (USB Audio)", "Windows DirectSound", default=True),
    device(5, "Varios micrófonos (Realtek)", "Windows DirectSound"),
    device(6, "Micrófono (USB Audio)", "Windows WASAPI", default=True),
    device(7, "Varios micrófonos (Realtek)", "Windows WASAPI"),
    device(8, "Micrófono (USB Audio)", "Windows WDM-KS", default=True),
    device(9, "Varios micrófonos (Realtek)", "Windows WDM-KS"),
]


def without(api):
    return [d for d in DEVICES if d.hostapi != api]


def test_sin_ajustes_elige_el_predeterminado_por_orden_de_api():
    assert select_input_device(DEVICES).device.index == 1
    assert select_input_device(without("MME")).device.index == 6
    assert select_input_device(without("Windows WASAPI")[4:]).device.index == 4


def test_wdm_ks_se_descarta_siempre():
    only_ks = [d for d in DEVICES if d.hostapi == "Windows WDM-KS"]
    choice = select_input_device(only_ks)
    assert choice.device is None
    assert choice.warning is None
    forced = select_input_device(DEVICES, wanted_hostapi="Windows WDM-KS")
    assert forced.device is None
    assert "Windows WDM-KS" in forced.warning


def test_las_salidas_no_son_candidatas():
    choice = select_input_device(DEVICES, wanted_name="Altavoces")
    assert choice.device is None
    assert "Altavoces" in choice.warning


def test_nombre_pedido_por_parte_del_nombre_sin_distinguir_mayusculas():
    assert select_input_device(DEVICES, wanted_name="realtek").device.index == 2


def test_api_pedida():
    choice = select_input_device(DEVICES, wanted_hostapi="Windows WASAPI")
    assert choice.device.index == 6
    both = select_input_device(DEVICES, wanted_name="Realtek", wanted_hostapi="Windows WASAPI")
    assert both.device.index == 7


def test_lo_pedido_no_existe_cae_al_predeterminado_con_aviso():
    choice = select_input_device(DEVICES, wanted_name="Yeti", wanted_hostapi="ASIO")
    assert choice.device is None
    assert "Yeti" in choice.warning and "ASIO" in choice.warning
    assert "Micrófono (USB Audio) [MME]" in choice.warning
    assert "WDM-KS" not in choice.warning.replace("'ASIO'", "")


def test_sin_preferencia_de_api_gana_el_primero():
    choice = select_input_device(DEVICES[4:8], api_preference=())
    assert choice.device.index == 4


def test_conversion_desde_sounddevice():
    devices = [
        {"name": "Mic", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 44100.0},
        {"name": "Mic", "hostapi": 1, "max_input_channels": 2, "default_samplerate": 48000.0},
    ]
    hostapis = [
        {"name": "MME", "default_input_device": 0},
        {"name": "Windows WASAPI", "default_input_device": -1},
    ]
    converted = from_sounddevice(devices, hostapis)
    assert converted == [
        InputDevice(0, "Mic", "MME", 1, 44100.0, True),
        InputDevice(1, "Mic", "Windows WASAPI", 2, 48000.0, False),
    ]
