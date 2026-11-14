"""Rutas de datos, configuración, registro y modelos.

Las carpetas del usuario las decide el adaptador de plataforma; los modelos están siempre
en `models/`, junto al código (RES-46). Solo `AppPaths.ensure` crea carpetas.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DB_FILE_NAME = "jarvis.db"
VERIFIER_FILE_NAME = "wakeword_verifier.pkl"


class _UserDirs(Protocol):
    def data_dir(self) -> Path: ...
    def config_dir(self) -> Path: ...
    def log_dir(self) -> Path: ...


def app_root() -> Path:
    """Raíz de la aplicación (carpeta `implementation/`)."""
    return Path(__file__).resolve().parents[2]


def models_dir() -> Path:
    """Carpeta de los modelos descargados en la instalación."""
    return app_root() / "models"


@dataclass(frozen=True)
class AppPaths:
    """Carpetas que usa el proceso."""

    data_dir: Path
    config_dir: Path
    log_dir: Path
    models_dir: Path

    @classmethod
    def from_platform(cls, platform: _UserDirs) -> "AppPaths":
        return cls(
            data_dir=platform.data_dir(),
            config_dir=platform.config_dir(),
            log_dir=platform.log_dir(),
            models_dir=models_dir(),
        )

    def ensure(self) -> None:
        """Crea las carpetas del usuario. Los modelos no se crean: se instalan."""
        for directory in (self.data_dir, self.config_dir, self.log_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILE_NAME

    @property
    def verifier_path(self) -> Path:
        """Verificador personal de «Hey Jarvis»; lo genera `calibrate_wakeword.py`."""
        return self.data_dir / VERIFIER_FILE_NAME


def required_models(
    stt_model: str = "small", voice: str = "es_ES-davefx-medium"
) -> tuple[Path, ...]:
    """Archivos, relativos a `models/`, sin los que el proceso no arranca (RES-46)."""
    whisper = Path(f"faster-whisper-{stt_model}")
    return (
        Path("openwakeword/hey_jarvis_v0.1.onnx"),
        Path("openwakeword/melspectrogram.onnx"),
        Path("openwakeword/embedding_model.onnx"),
        Path("openwakeword/silero_vad.onnx"),
        whisper / "model.bin",
        whisper / "config.json",
        whisper / "tokenizer.json",
        whisper / "vocabulary.txt",
        Path(f"piper/{voice}.onnx"),
        Path(f"piper/{voice}.onnx.json"),
    )


def missing_models(
    directory: Path, stt_model: str = "small", voice: str = "es_ES-davefx-medium"
) -> list[Path]:
    """Modelos exigidos que no están en `directory`."""
    return [p for p in required_models(stt_model, voice) if not (directory / p).is_file()]
