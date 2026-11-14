r"""Genera los WAV de prueba de tests/fixtures/audio/ (16 kHz mono int16, reproducible).

Voz: Piper es_ES-davefx-medium de models/piper/. Silencio y ruido: numpy con semilla fija.
No genera buenas_noches_jarvis.wav (opcional, DEF-30).
Uso: .\implementation\.venv\Scripts\python.exe implementation\scripts\make_fixture_audio.py
"""
import math
import wave
from pathlib import Path

import numpy
from piper import PiperVoice
from scipy.signal import resample_poly

TARGET_RATE = 16000
IMPLEMENTATION_DIR = Path(__file__).resolve().parents[1]
VOICE_PATH = IMPLEMENTATION_DIR / "models" / "piper" / "es_ES-davefx-medium.onnx"
VOICE_CONFIG_PATH = IMPLEMENTATION_DIR / "models" / "piper" / "es_ES-davefx-medium.onnx.json"
OUTPUT_DIR = IMPLEMENTATION_DIR / "tests" / "fixtures" / "audio"

EDGE_SILENCE_SECONDS = 0.5
NOISE_AMPLITUDE = 300  # int16, ruido blanco de bajo nivel (~ -40 dBFS)
CONTROL_SECONDS = 5
NOISE_SEED = 36

CONVERSATION_TEXT = "Hoy hace buen día, así que después de comer iremos a pasear por el parque."
LONG_TEXTS = [
    "Hoy por la mañana he repasado las tareas pendientes de la semana.",
    "Primero revisaré el correo, después prepararé el informe y por último ordenaré los documentos.",
    "Si queda tiempo, aprovecharé para leer un artículo sobre la historia de la astronomía.",
    "Mañana por la tarde tengo una reunión con el equipo para planificar el siguiente trimestre.",
]


def to_target_rate(pcm: numpy.ndarray, source_rate: int) -> numpy.ndarray:
    """Remuestrea PCM int16 a 16 kHz."""
    if source_rate == TARGET_RATE:
        return pcm
    divisor = math.gcd(TARGET_RATE, source_rate)
    resampled = resample_poly(pcm.astype(numpy.float64), TARGET_RATE // divisor, source_rate // divisor)
    return numpy.clip(numpy.round(resampled), -32768, 32767).astype(numpy.int16)


def speak(voice: PiperVoice, text: str) -> numpy.ndarray:
    """Sintetiza `text` y devuelve PCM int16 mono a 16 kHz."""
    chunks = [chunk.audio_int16_array for chunk in voice.synthesize(text)]
    return to_target_rate(numpy.concatenate(chunks), voice.config.sample_rate)


def silence(seconds: float) -> numpy.ndarray:
    return numpy.zeros(int(seconds * TARGET_RATE), numpy.int16)


def padded(pcm: numpy.ndarray) -> numpy.ndarray:
    """Añade silencio digital al inicio y al final."""
    edge = silence(EDGE_SILENCE_SECONDS)
    return numpy.concatenate([edge, pcm, edge])


def write_wav(name: str, pcm: numpy.ndarray) -> None:
    with wave.open(str(OUTPUT_DIR / name), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(TARGET_RATE)
        wav_file.writeframes(pcm.astype("<i2").tobytes())
    print(f"{name}: {len(pcm) / TARGET_RATE:.2f} s")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(VOICE_PATH, VOICE_CONFIG_PATH, use_cuda=False)

    write_wav("hey_jarvis.wav", padded(speak(voice, "Hey Jarvis")))
    write_wav("gracias_jarvis.wav", padded(speak(voice, "Gracias Jarvis")))
    write_wav("control_conversacion.wav", padded(speak(voice, CONVERSATION_TEXT)))
    write_wav(
        "control_muchas_gracias_jarvis_por_todo.wav",
        padded(speak(voice, "Muchas gracias Jarvis por todo")),
    )
    write_wav("control_silencio.wav", silence(CONTROL_SECONDS))
    noise = numpy.random.default_rng(NOISE_SEED).normal(0, NOISE_AMPLITUDE, CONTROL_SECONDS * TARGET_RATE)
    write_wav("control_ruido.wav", numpy.clip(noise, -32768, 32767).astype(numpy.int16))
    long_speech = numpy.concatenate([numpy.concatenate([speak(voice, t), silence(0.4)]) for t in LONG_TEXTS])
    write_wav("largo_stt.wav", padded(long_speech))


if __name__ == "__main__":
    main()
