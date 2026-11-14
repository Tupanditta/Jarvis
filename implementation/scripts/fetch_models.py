"""Descarga los modelos a ``models/`` y verifica su SHA-256 (RES-46, proceso.md).

Es la única operación del proyecto que usa la red y solo se ejecuta al instalar: no la importa
ningún módulo de ``jarvis_assistant``. Cada archivo se verifica antes de aparecer en su ruta
final; los que ya están y son correctos no se vuelven a descargar.

Uso, desde ``implementation/``:  python scripts/fetch_models.py [directorio_models]
"""
import hashlib
import os
import sys
import tempfile
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DOWNLOAD_TIMEOUT_SECONDS = 60
_HASH_BLOCK_BYTES = 1024 * 1024

_OPENWAKEWORD = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1"
_WHISPER = "https://huggingface.co/Systran/faster-whisper-small/resolve/main"
_PIPER = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium"


class ChecksumMismatchError(ValueError):
    """El contenido descargado no coincide con el SHA-256 del manifiesto."""


@dataclass(frozen=True)
class ModelFile:
    """Archivo de modelo: origen, ruta relativa a ``models/`` (con ``/``) y SHA-256 esperado."""

    url: str
    relative_path: str
    sha256: str


MANIFEST: tuple[ModelFile, ...] = (
    ModelFile(
        f"{_OPENWAKEWORD}/hey_jarvis_v0.1.onnx",
        "openwakeword/hey_jarvis_v0.1.onnx",
        "94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb",
    ),
    ModelFile(
        f"{_OPENWAKEWORD}/silero_vad.onnx",
        "openwakeword/silero_vad.onnx",
        "a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28",
    ),
    ModelFile(
        f"{_OPENWAKEWORD}/melspectrogram.onnx",
        "openwakeword/melspectrogram.onnx",
        "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",
    ),
    ModelFile(
        f"{_OPENWAKEWORD}/embedding_model.onnx",
        "openwakeword/embedding_model.onnx",
        "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",
    ),
    ModelFile(
        f"{_WHISPER}/model.bin",
        "faster-whisper-small/model.bin",
        "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
    ),
    ModelFile(
        f"{_WHISPER}/config.json",
        "faster-whisper-small/config.json",
        "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828",
    ),
    ModelFile(
        f"{_WHISPER}/tokenizer.json",
        "faster-whisper-small/tokenizer.json",
        "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
    ),
    ModelFile(
        f"{_WHISPER}/vocabulary.txt",
        "faster-whisper-small/vocabulary.txt",
        "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
    ),
    ModelFile(
        f"{_PIPER}/es_ES-davefx-medium.onnx",
        "piper/es_ES-davefx-medium.onnx",
        "6658b03b1a6c316ee4c265a9896abc1393353c2d9e1bca7d66c2c442e222a917",
    ),
    ModelFile(
        f"{_PIPER}/es_ES-davefx-medium.onnx.json",
        "piper/es_ES-davefx-medium.onnx.json",
        "0e0dda87c732f6f38771ff274a6380d9252f327dca77aa2963d5fbdf9ec54842",
    ),
    # Ficha de la voz (licencia CC0 del conjunto de datos).
    ModelFile(
        f"{_PIPER}/MODEL_CARD",
        "piper/MODEL_CARD.md",
        "420703b5d8ea239b729f13d83f31eea9bae5fcb89447de23ebc94aa8a4768f95",
    ),
)

# Modelos que deben existir en ``models/`` para arrancar (todo salvo la ficha de la voz).
REQUIRED_PATHS: tuple[str, ...] = tuple(
    entry.relative_path for entry in MANIFEST if entry.relative_path != "piper/MODEL_CARD.md"
)

Report = Callable[[str, str], None]


def _destination(models_dir: Path, relative_path: str) -> Path:
    """Ruta final dentro de ``models_dir``; rechaza rutas absolutas o con ``..``."""
    parts = PurePosixPath(relative_path).parts
    if not parts or PurePosixPath(relative_path).is_absolute() or ".." in parts:
        raise ValueError(f"Ruta relativa no válida en el manifiesto: {relative_path!r}")
    return models_dir.joinpath(*parts)


def _write_verified(entry: ModelFile, destination: Path, data: bytes) -> None:
    """Escribe ``data`` en ``destination`` solo si su SHA-256 coincide, sin dejar temporales."""
    if hashlib.sha256(data).hexdigest() != entry.sha256:
        raise ChecksumMismatchError(f"SHA-256 incorrecto para {entry.relative_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=destination.parent, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(data)
        os.replace(temp_name, destination)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def _is_installed(entry: ModelFile, destination: Path) -> bool:
    """Si ``destination`` ya existe con el SHA-256 del manifiesto."""
    if not destination.is_file():
        return False
    digest = hashlib.sha256()
    with destination.open("rb") as file:
        while block := file.read(_HASH_BLOCK_BYTES):
            digest.update(block)
    return digest.hexdigest() == entry.sha256


def fetch(
    manifest: Sequence[ModelFile],
    models_dir: Path,
    download: Callable[[str], bytes],
    report: Report = lambda _path, _status: None,
) -> list[str]:
    """Deja cada entrada del manifiesto, verificada, dentro de ``models_dir``.

    ``download(url)`` devuelve los bytes del recurso; no se llama para los archivos que ya
    están y son correctos. ``report(ruta, estado)`` informa de cada archivo. Lanza
    ``ChecksumMismatchError`` en la primera suma errónea (los archivos anteriores correctos
    se conservan). Devuelve las rutas exigidas que siguen ausentes.
    """
    models_dir = Path(models_dir)
    for entry in manifest:
        destination = _destination(models_dir, entry.relative_path)
        if _is_installed(entry, destination):
            report(entry.relative_path, "ya instalado")
            continue
        _write_verified(entry, destination, download(entry.url))
        report(entry.relative_path, "descargado")
    return [path for path in REQUIRED_PATHS if not (models_dir / path).is_file()]


def download_https(url: str) -> bytes:
    """Descarga ``url`` por HTTPS con tiempo límite; rechaza cualquier otro esquema."""
    if urlparse(url).scheme != "https":
        raise ValueError(f"Solo se admite https: {url}")
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return response.read()


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada de línea de comandos. Devuelve el código de salida."""
    args = list(sys.argv[1:] if argv is None else argv)
    models_dir = Path(args[0]) if args else DEFAULT_MODELS_DIR
    try:
        missing = fetch(
            MANIFEST, models_dir, download_https, lambda path, status: print(f"{path}: {status}")
        )
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if missing:
        for path in missing:
            print(f"Falta: {path}", file=sys.stderr)
        return 1
    print(f"Modelos completos en {models_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
