"""Registro de diagnóstico: archivo rotativo y excepciones no capturadas (proceso.md).

Privacidad (RES-48): nunca se registra audio; el texto transcrito y el de los recordatorios
solo se escriben en nivel `DEBUG`. No se escribe en la consola.
"""
import asyncio
import logging
import logging.handlers
import sys
import threading
from pathlib import Path
from typing import Any

LOG_FILE_NAME = "jarvis.log"
MAX_LOG_BYTES = 1024 * 1024
LOG_BACKUP_COUNT = 4  # jarvis.log y 4 copias: 5 archivos de 1 MB
LOG_FORMAT = "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

_logger = logging.getLogger(__name__)
_handler: logging.handlers.RotatingFileHandler | None = None


def setup_logging(log_dir: Path, level: str = "INFO") -> logging.handlers.RotatingFileHandler:
    """Dirige el registro raíz a `log_dir/jarvis.log` y devuelve su manejador.

    Crea la carpeta si falta. Llamarla de nuevo sustituye al manejador anterior.
    """
    global _handler
    if level not in LEVELS:
        raise ValueError(f"Nivel de registro desconocido: {level!r}")
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if _handler is not None:
        root.removeHandler(_handler)
        _handler.close()
    _handler = logging.handlers.RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(_handler)
    root.setLevel(level)
    return _handler


def install_excepthooks() -> None:
    """Envía al registro las excepciones no capturadas del hilo principal y de los demás."""
    sys.excepthook = _log_uncaught
    threading.excepthook = _log_uncaught_in_thread


def install_asyncio_handler(loop: asyncio.AbstractEventLoop) -> None:
    """Envía al registro las excepciones no capturadas del bucle del núcleo."""
    loop.set_exception_handler(_log_asyncio_error)


def _log_uncaught(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    _logger.critical("Excepción no capturada", exc_info=(exc_type, exc_value, exc_traceback))


def _log_uncaught_in_thread(args: threading.ExceptHookArgs) -> None:
    if issubclass(args.exc_type, SystemExit):
        return
    thread_name = args.thread.name if args.thread else "desconocido"
    _logger.critical(
        "Excepción no capturada en el hilo %s",
        thread_name,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def _log_asyncio_error(_loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
    exception = context.get("exception")
    exc_info = (type(exception), exception, exception.__traceback__) if exception else None
    message = context.get("message", "sin mensaje")
    _logger.error("Error en el núcleo: %s", message, exc_info=exc_info)
