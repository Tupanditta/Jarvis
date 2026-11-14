"""«Hey Jarvis» con el modelo preentrenado de `openwakeword` (captura-audio.md, AD-16).

La única adaptación admitida es el verificador personal: un archivo `pickle` que genera
`calibrate_wakeword.py` en el propio equipo y que solo se carga desde la carpeta de datos.
"""
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "hey_jarvis_v0.1"


def model_arguments(models_dir: Path) -> dict[str, Any]:
    """Argumentos de `openwakeword.Model` para usar solo los modelos de `models/`."""
    folder = models_dir / "openwakeword"
    return {
        "wakeword_models": [str(folder / f"{MODEL_NAME}.onnx")],
        "inference_framework": "onnx",
        "melspec_model_path": str(folder / "melspectrogram.onnx"),
        "embedding_model_path": str(folder / "embedding_model.onnx"),
    }


def _default_factory(**kwargs: Any) -> Any:
    from openwakeword.model import Model

    return Model(**kwargs)


class OpenWakeWordDetector:
    def __init__(
        self,
        models_dir: Path,
        *,
        verifier_path: Path | None = None,
        use_verifier: bool = True,
        verifier_gate: float = 0.2,
        model_factory: Callable[..., Any] = _default_factory,
    ) -> None:
        self._models_dir = models_dir
        self._verifier_path = verifier_path
        self._use_verifier = use_verifier
        self._verifier_gate = verifier_gate
        self._factory = model_factory
        self._model: Any = None
        self.verifier_active = False

    def load(self) -> None:
        arguments = model_arguments(self._models_dir)
        path = self._verifier_path
        if self._use_verifier and path is not None and path.is_file():
            try:
                self._model = self._factory(
                    custom_verifier_models={MODEL_NAME: str(path)},
                    custom_verifier_threshold=self._verifier_gate,
                    **arguments,
                )
                self.verifier_active = True
                logger.info("Verificador personal de «Hey Jarvis» cargado")
                return
            except Exception as error:
                logger.warning(
                    "El verificador personal no se puede cargar (%s); se sigue sin él", error
                )
        self._model = self._factory(**arguments)
        self.verifier_active = False

    @property
    def model(self) -> Any:
        """Modelo de `openwakeword` ya cargado; lo usa la calibración."""
        return self._model

    def predict(self, block: np.ndarray) -> float:
        return float(self._model.predict(block)[MODEL_NAME])

    def reset(self) -> None:
        if self._model is not None:
            self._model.reset()
