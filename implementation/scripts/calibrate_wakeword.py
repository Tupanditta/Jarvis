"""Calibración de «Hey Jarvis» con la voz y el micrófono del usuario (captura-audio.md).

Abre el micrófono igual que el asistente (misma selección, misma ganancia). El audio solo
vive en memoria: no se escribe en disco, y la configuración no se modifica; el guion muestra
las líneas de `settings.toml` que recomienda.

    .\\.venv\\Scripts\\python.exe scripts\\calibrate_wakeword.py                    # medir
    .\\.venv\\Scripts\\python.exe scripts\\calibrate_wakeword.py --train-verifier   # verificador
"""
import argparse
import pickle
import sys
import time

import numpy as np

from jarvis_assistant import config as config_module
from jarvis_assistant.audio_capture.calibration import (
    blocks_of,
    collect_features,
    count_activations,
    recommend_gain,
    verdict,
    verified_scores,
    verifier_passes,
)
from jarvis_assistant.audio_capture.microphone import Microphone, apply_gain
from jarvis_assistant.audio_capture.segmenter import BLOCK_SECONDS
from jarvis_assistant.audio_capture.telemetry import dbfs, peak_of
from jarvis_assistant.audio_capture.wakeword import MODEL_NAME, OpenWakeWordDetector
from jarvis_assistant.main import create_platform
from jarvis_assistant.paths import AppPaths

REPETITION_SECONDS = 3.0
READING_TEXT = (
    "Lea en voz alta, con su voz normal, hasta que se le indique:\n"
    "  «El asistente escucha el micrófono de forma continua y solo responde cuando oye su\n"
    "  nombre. Todo el audio se procesa en este equipo y nunca se guarda en el disco. Para\n"
    "  abrir una sesión se dice la frase de activación; para dejarlo en reposo se le dan las\n"
    "  gracias, y para cerrar la sesión se le desean buenas noches. Mientras tanto se puede\n"
    "  seguir hablando con normalidad: una conversación no debería activarlo.»"
)


class Recorder:
    def __init__(self, microphone: Microphone, gain: float) -> None:
        self._microphone = microphone
        self._gain = gain

    def record(self, seconds: float) -> np.ndarray:
        """Graba en memoria, con la ganancia aplicada."""
        while self._microphone.read(0.0) is not None:  # se descarta lo acumulado
            pass
        blocks = []
        while len(blocks) * BLOCK_SECONDS < seconds:
            block = self._microphone.read(1.0)
            if block is not None:
                blocks.append(apply_gain(block, self._gain))
        return np.concatenate(blocks)

    def repetitions(self, count: int) -> list[np.ndarray]:
        clips = []
        for number in range(1, count + 1):
            print(f"  Diga «Hey Jarvis» ({number}/{count})... ", end="", flush=True)
            clip = self.record(REPETITION_SECONDS)
            clips.append(clip)
            print(f"pico {dbfs(peak_of(clip)):.1f} dBFS")
            time.sleep(0.3)
        return clips


def clip_score(detector: OpenWakeWordDetector, clip: np.ndarray) -> float:
    detector.reset()
    return max((detector.predict(block) for block in blocks_of(clip)), default=0.0)


def measure(recorder: Recorder, detector: OpenWakeWordDetector, audio) -> int:
    print("Guarde silencio 3 s para medir el ruido de fondo...")
    noise = recorder.record(3.0)
    print(f"  ruido de fondo: pico {dbfs(peak_of(noise)):.1f} dBFS\n")
    clips = recorder.repetitions(10)
    scores = [clip_score(detector, clip) for clip in clips]
    print()
    for number, score in enumerate(scores, 1):
        print(f"  repetición {number:2}: puntuación {score:.2f}")
    voice_peak = max(dbfs(peak_of(clip)) for clip in clips)
    result = verdict(scores, audio.wakeword_threshold)
    print(f"\nDetecciones con la configuración vigente: {result.detections} de 10.")

    gain = recommend_gain(voice_peak, audio.input_gain)
    if gain is not None:
        print(f"La voz llega baja ({voice_peak:.1f} dBFS). En settings.toml, sección [audio]:")
        print(f"input_gain = {gain}")
        print("Cambie la ganancia y repita la medida antes de tocar el umbral.")
    if result.kind == "ok":
        print("No hay que cambiar nada.")
    elif result.kind == "threshold":
        print("En settings.toml, sección [audio]:")
        print(f"wakeword_threshold = {result.threshold}")
    elif result.kind == "verifier":
        print("Entrene el verificador personal: calibrate_wakeword.py --train-verifier")
    else:
        print("Ninguna repetición llega a 0,2: el verificador personal no puede ayudar.")
        print("Pronuncie la frase a la inglesa («jei YAR-vis») y revise el micrófono con")
        print("scripts\\diagnose_mic.py.")
    return 0


def train(recorder: Recorder, detector: OpenWakeWordDetector, audio, verifier_path) -> int:
    from openwakeword.custom_verifier_model import train_verifier_model

    model = detector.model
    gate, threshold = audio.wakeword_verifier_gate, audio.wakeword_threshold
    print("Entrenamiento: 20 repeticiones. Varíe la distancia y la entonación.")
    positives = []
    for clip in recorder.repetitions(20):
        positives.extend(collect_features(model, MODEL_NAME, clip, gate))
    print(f"\n{READING_TEXT}\nGrabando 60 s de lectura...")
    reading = recorder.record(60.0)
    print("Ahora guarde silencio 20 s (ruido de fondo)...")
    noise = recorder.record(20.0)
    negatives = collect_features(model, MODEL_NAME, np.concatenate([reading, noise]), 0.0)
    if len(positives) < 10:
        print(f"Solo {len(positives)} ventanas superan la puerta ({gate}): no se puede entrenar.")
        print("Ejecute antes la medida (sin --train-verifier) y revise la ganancia.")
        return 1
    features = np.vstack([*positives, *negatives])
    labels = np.array([1] * len(positives) + [0] * len(negatives))
    verifier = train_verifier_model(features, labels)

    print("\nValidación: 10 repeticiones nuevas.")
    clips = recorder.repetitions(10)
    print("Y 30 s más de lectura del mismo texto...")
    control = recorder.record(30.0)
    with_verifier = sum(
        max(verified_scores(model, MODEL_NAME, verifier, clip, gate), default=0.0) >= threshold
        for clip in clips
    )
    without = sum(clip_score(detector, clip) >= threshold for clip in clips)
    false_activations = count_activations(
        verified_scores(model, MODEL_NAME, verifier, control, gate), threshold
    )
    print(f"\nDetección sin verificador: {without} de 10; con verificador: {with_verifier} de 10.")
    print(f"Activaciones durante la lectura: {false_activations}.")
    if not verifier_passes(with_verifier, false_activations):
        print("El verificador no pasa la validación: se descarta y no se guarda nada.")
        print("Repita el entrenamiento en un lugar más silencioso o revise la ganancia.")
        return 1
    verifier_path.parent.mkdir(parents=True, exist_ok=True)
    with open(verifier_path, "wb") as file:
        pickle.dump(verifier, file)
    print(f"Verificador guardado en {verifier_path}.")
    print("Se usará en el próximo arranque (audio.wakeword_verifier = true).")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Calibra «Hey Jarvis» con su voz")
    parser.add_argument("--train-verifier", action="store_true",
                        help="entrena y valida el verificador personal")
    args = parser.parse_args(argv)

    paths = AppPaths.from_platform(create_platform())
    config, _errors = config_module.load(paths.config_dir)
    audio = config.settings.audio
    detector = OpenWakeWordDetector(
        paths.models_dir,
        verifier_path=paths.verifier_path,
        use_verifier=audio.wakeword_verifier and not args.train_verifier,
        verifier_gate=audio.wakeword_verifier_gate,
    )
    detector.load()
    microphone = Microphone(audio)
    microphone.open()
    try:
        recorder = Recorder(microphone, audio.input_gain)
        if args.train_verifier:
            return train(recorder, detector, audio, paths.verifier_path)
        return measure(recorder, detector, audio)
    finally:
        microphone.close()


if __name__ == "__main__":
    sys.exit(main())
