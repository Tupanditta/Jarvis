"""Micrófono, palabra de activación y VAD con bibliotecas falsas (captura-audio.md)."""
import logging
from types import SimpleNamespace

import numpy as np
import pytest

from jarvis_assistant.audio_capture.microphone import Microphone, apply_gain, resample_to_16k
from jarvis_assistant.audio_capture.telemetry import SignalTelemetry, dbfs, level_of
from jarvis_assistant.audio_capture.types import MicrophoneError
from jarvis_assistant.audio_capture.vad import SileroVad
from jarvis_assistant.audio_capture.wakeword import MODEL_NAME, OpenWakeWordDetector
from jarvis_assistant.config import AudioSettings

# --- Micrófono -------------------------------------------------------------------------------


class FakeStream:
    def __init__(self, library, **kwargs):
        self.kwargs = kwargs
        self.active = False
        self.closed = False
        if kwargs["samplerate"] in library.unsupported_rates:
            raise RuntimeError("Invalid sample rate")
        library.streams.append(self)

    def start(self):
        self.active = True

    def stop(self):
        self.active = False

    def close(self):
        self.closed = True

    def push(self, samples):
        self.kwargs["callback"](np.asarray(samples, dtype=np.int16).reshape(-1, 1), 0, None, None)


class FakeSoundDevice:
    def __init__(self, native_rate=48000.0, unsupported_rates=()):
        self.unsupported_rates = set(unsupported_rates)
        self.streams = []
        self.terminated = self.initialized = 0
        self.devices = [
            {"name": "Mic", "hostapi": 0, "max_input_channels": 1,
             "default_samplerate": native_rate},
        ]
        self.hostapis = [{"name": "MME", "default_input_device": 0}]

    def query_devices(self):
        return self.devices

    def query_hostapis(self):
        return self.hostapis

    def InputStream(self, **kwargs):
        return FakeStream(self, **kwargs)

    def _terminate(self):
        self.terminated += 1

    def _initialize(self):
        self.initialized += 1


def test_abre_a_16_khz_y_entrega_los_bloques_del_callback(caplog):
    caplog.set_level(logging.INFO)
    sd = FakeSoundDevice()
    microphone = Microphone(AudioSettings(), sd)
    microphone.open()
    stream = sd.streams[0]
    assert stream.kwargs["samplerate"] == 16000
    assert stream.kwargs["blocksize"] == 1280
    assert stream.kwargs["device"] == 0
    assert stream.kwargs["channels"] == 1
    stream.push(np.arange(1280))
    block = microphone.read(0.01)
    assert block.shape == (1280,)
    assert block[5] == 5
    assert "16 kHz directos" in caplog.text and "MME" in caplog.text


def test_si_no_admite_16_khz_abre_a_la_frecuencia_nativa_y_remuestrea(caplog):
    caplog.set_level(logging.INFO)
    sd = FakeSoundDevice(native_rate=48000.0, unsupported_rates={16000})
    microphone = Microphone(AudioSettings(), sd)
    microphone.open()
    stream = sd.streams[0]
    assert stream.kwargs["samplerate"] == 48000
    assert stream.kwargs["blocksize"] == 3840
    t = np.arange(3840) / 48000
    stream.push(np.round(8000 * np.sin(2 * np.pi * 440 * t)))
    block = microphone.read(0.01)
    assert block.shape == (1280,) and block.dtype == np.int16
    assert 7000 < np.abs(block[100:1100]).max() <= 8200
    assert "con remuestreo" in caplog.text


def test_el_remuestreo_filtra_lo_que_no_cabe_en_16_khz():
    t = np.arange(3840) / 48000
    ultrasound = np.round(8000 * np.sin(2 * np.pi * 15000 * t))
    assert np.abs(resample_to_16k(ultrasound, 48000)[100:1100]).max() < 400


def test_la_cola_llena_descarta_lo_mas_antiguo():
    sd = FakeSoundDevice()
    microphone = Microphone(AudioSettings(), sd)
    microphone.open()
    for value in range(27):  # la cola guarda 2 s: 25 bloques
        sd.streams[0].push(np.full(1280, value))
    assert microphone.read(0.01)[0] == 2
    assert microphone.take_dropped() == 2
    assert microphone.take_dropped() == 0


def test_error_al_abrir_y_flujo_que_deja_de_entregar():
    sd = FakeSoundDevice(native_rate=16000.0, unsupported_rates={16000})
    microphone = Microphone(AudioSettings(), sd)
    with pytest.raises(MicrophoneError):
        microphone.open()
    with pytest.raises(MicrophoneError):
        microphone.read(0.01)

    sd = FakeSoundDevice()
    microphone = Microphone(AudioSettings(), sd)
    microphone.open()
    assert microphone.read(0.01) is None
    sd.streams[0].active = False
    with pytest.raises(MicrophoneError):
        microphone.read(0.01)
    microphone.close()
    assert sd.streams[0].closed


def test_dispositivo_pedido_inexistente_avisa_una_sola_vez(caplog):
    sd = FakeSoundDevice()
    microphone = Microphone(AudioSettings(input_device="Yeti"), sd)
    microphone.open()
    microphone.close()
    microphone.open()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and "Yeti" in warnings[0].getMessage()
    assert sd.streams[0].kwargs["device"] is None


def test_refresh_reinicia_portaudio():
    sd = FakeSoundDevice()
    Microphone(AudioSettings(), sd).refresh()
    assert (sd.terminated, sd.initialized) == (1, 1)


def test_ganancia_y_niveles():
    block = np.array([100, -100, 30000, -30000], dtype=np.int16)
    assert apply_gain(block, 1.0) is block
    assert apply_gain(block, 2.0).tolist() == [200, -200, 32767, -32768]
    assert apply_gain(block, 0.5).tolist() == [50, -50, 15000, -15000]
    assert dbfs(0) == -120.0
    assert dbfs(32767) == 0.0
    assert level_of(np.zeros(1280, dtype=np.int16)) == 0.0
    assert level_of(np.full(1280, 32767, dtype=np.int16)) == 1.0
    assert 0 < level_of(np.full(1280, 1000, dtype=np.int16)) < 1


def test_telemetria_escribe_una_linea_cada_cinco_segundos(caplog):
    caplog.set_level(logging.DEBUG)
    telemetry = SignalTelemetry()
    block = np.full(1280, 3277, dtype=np.int16)
    lines = [telemetry.add(block, now=index * 0.08, dropped=0) for index in range(130)]
    reported = [line for line in lines if line]
    assert len(reported) == 2
    assert "pico -20.0 dBFS" in reported[0] and "RMS -20.0 dBFS" in reported[0]
    assert "12.7 bloques/s" in reported[0]


# --- Palabra de activación -------------------------------------------------------------------


class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.resets = 0

    def predict(self, block):
        return {MODEL_NAME: np.float32(0.25)}

    def reset(self):
        self.resets += 1


def factory(calls, fail_with_verifier=False):
    def build(**kwargs):
        calls.append(kwargs)
        if fail_with_verifier and "custom_verifier_models" in kwargs:
            raise ValueError("pickle incompatible")
        return FakeModel(**kwargs)

    return build


def test_sin_verificador_solo_el_modelo_preentrenado_local(tmp_path):
    calls = []
    detector = OpenWakeWordDetector(
        tmp_path, verifier_path=tmp_path / "v.pkl", model_factory=factory(calls)
    )
    detector.load()
    (kwargs,) = calls
    assert "custom_verifier_models" not in kwargs
    assert kwargs["inference_framework"] == "onnx"
    assert kwargs["wakeword_models"] == [str(tmp_path / "openwakeword" / f"{MODEL_NAME}.onnx")]
    assert kwargs["melspec_model_path"].endswith("melspectrogram.onnx")
    assert kwargs["embedding_model_path"].endswith("embedding_model.onnx")
    assert not detector.verifier_active
    assert detector.predict(np.zeros(1280, dtype=np.int16)) == pytest.approx(0.25)
    assert isinstance(detector.predict(np.zeros(1280, dtype=np.int16)), float)


def test_verificador_presente_y_activado_se_pasa_con_la_puerta(tmp_path):
    verifier = tmp_path / "v.pkl"
    verifier.write_bytes(b"x")
    calls = []
    detector = OpenWakeWordDetector(
        tmp_path, verifier_path=verifier, verifier_gate=0.3, model_factory=factory(calls)
    )
    detector.load()
    (kwargs,) = calls
    assert kwargs["custom_verifier_models"] == {MODEL_NAME: str(verifier)}
    assert kwargs["custom_verifier_threshold"] == 0.3
    assert detector.verifier_active


def test_verificador_desactivado_no_se_carga(tmp_path):
    verifier = tmp_path / "v.pkl"
    verifier.write_bytes(b"x")
    calls = []
    detector = OpenWakeWordDetector(
        tmp_path, verifier_path=verifier, use_verifier=False, model_factory=factory(calls)
    )
    detector.load()
    assert "custom_verifier_models" not in calls[0]
    assert not detector.verifier_active


def test_verificador_ilegible_aviso_y_arranque_normal(tmp_path, caplog):
    verifier = tmp_path / "v.pkl"
    verifier.write_bytes(b"x")
    calls = []
    detector = OpenWakeWordDetector(
        tmp_path, verifier_path=verifier, model_factory=factory(calls, fail_with_verifier=True)
    )
    detector.load()
    assert len(calls) == 2 and "custom_verifier_models" not in calls[1]
    assert not detector.verifier_active
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and "verificador" in warnings[0].getMessage()
    detector.reset()


def test_vad_usa_el_modelo_local_y_dos_tramas_por_bloque(tmp_path):
    seen = {}

    def build(path):
        seen["path"] = path
        return SimpleNamespace(
            predict=lambda block, frame_size: seen.update(frame=frame_size) or np.float32(0.7),
            reset_states=lambda: seen.update(reset=True),
        )

    vad = SileroVad(tmp_path, build)
    vad.load()
    assert vad.predict(np.zeros(1280, dtype=np.int16)) == pytest.approx(0.7)
    vad.reset()
    assert seen == {
        "path": str(tmp_path / "openwakeword" / "silero_vad.onnx"), "frame": 640, "reset": True,
    }
