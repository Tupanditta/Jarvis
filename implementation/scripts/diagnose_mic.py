"""Diagnóstico del micrófono: qué entrada y qué API de audio usar (captura-audio.md).

Graba 5 s de cada entrada mientras usted dice «Hey Jarvis», mide el nivel, pasa el audio por
el modelo `hey_jarvis` y recomienda `audio.input_device` y `audio.input_hostapi`.
El audio solo vive en memoria: no se escribe en disco ni sale del equipo.

    .\\.venv\\Scripts\\python.exe scripts\\diagnose_mic.py
"""
import sys

import numpy as np

from jarvis_assistant import config as config_module
from jarvis_assistant.audio_capture.calibration import (
    InputResult,
    blocks_of,
    classify_input,
    recommend_input,
)
from jarvis_assistant.audio_capture.device_selection import EXCLUDED_API, from_sounddevice
from jarvis_assistant.audio_capture.microphone import apply_gain
from jarvis_assistant.audio_capture.telemetry import dbfs, peak_of
from jarvis_assistant.audio_capture.wakeword import OpenWakeWordDetector
from jarvis_assistant.main import create_platform
from jarvis_assistant.paths import AppPaths

SECONDS = 5
RATE = 16000


def record(sd, device, seconds: float) -> np.ndarray:
    """Graba a 16 kHz o, si el dispositivo no lo admite, a su frecuencia y remuestrea."""
    try:
        pcm = sd.rec(int(seconds * RATE), samplerate=RATE, channels=1, dtype="int16",
                     device=device.index)
        sd.wait()
        return pcm[:, 0]
    except Exception:
        from math import gcd

        from scipy.signal import resample_poly

        rate = round(device.samplerate)
        pcm = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype="int16",
                     device=device.index)
        sd.wait()
        divisor = gcd(RATE, rate)
        resampled = resample_poly(pcm[:, 0].astype(np.float64), RATE // divisor, rate // divisor)
        return np.clip(np.round(resampled), -32768, 32767).astype(np.int16)


def main() -> int:
    import sounddevice as sd

    paths = AppPaths.from_platform(create_platform())
    config, _errors = config_module.load(paths.config_dir)
    audio = config.settings.audio
    detector = OpenWakeWordDetector(paths.models_dir, use_verifier=False)
    detector.load()

    devices = [
        d for d in from_sounddevice(sd.query_devices(), sd.query_hostapis())
        if d.channels > 0 and d.hostapi != EXCLUDED_API
    ]
    if not devices:
        print("No hay ninguna entrada de audio.")
        return 1
    print(f"Se probarán {len(devices)} entradas, {SECONDS} s cada una.")
    print("Diga «Hey Jarvis» una o dos veces en cada grabación.\n")
    results = []
    for device in devices:
        input(f"[{device.hostapi}] {device.name}: pulse Intro y hable... ")
        try:
            pcm = apply_gain(record(sd, device, SECONDS), audio.input_gain)
        except Exception as error:
            print(f"   no se puede abrir: {error}")
            continue
        detector.reset()
        score = max((detector.predict(block) for block in blocks_of(pcm)), default=0.0)
        peak = peak_of(pcm)
        kind = classify_input(peak, score, audio.wakeword_threshold)
        results.append(InputResult(device.name, device.hostapi, peak, score, kind))
        print(f"   pico {dbfs(peak):6.1f} dBFS, «Hey Jarvis» {score:.2f}: {kind}")

    best = recommend_input(results)
    print()
    if best is None:
        print("Ninguna entrada entrega audio. Revise el micrófono y los permisos de Windows.")
        return 1
    print("Recomendación para settings.toml, sección [audio]:")
    print(f'input_device = "{best.name}"')
    print(f'input_hostapi = "{best.hostapi}"')
    if best.kind != "detecta":
        print("La entrada tiene señal pero no detecta: ejecute scripts\\calibrate_wakeword.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
