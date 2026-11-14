"""Registro de diagnóstico rotativo y excepciones no capturadas (T-0.8, proceso.md)."""
import asyncio
import logging
import logging.handlers
import re
import sys
import threading

import pytest

from jarvis_assistant.process import logging_setup
from jarvis_assistant.process.logging_setup import (
    install_asyncio_handler,
    install_excepthooks,
    setup_logging,
)

MIB = 1024 * 1024


@pytest.fixture(autouse=True)
def restore_logging():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    hooks = sys.excepthook, threading.excepthook
    yield
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(level)
    sys.excepthook, threading.excepthook = hooks


def read_log(log_dir) -> str:
    for handler in logging.getLogger().handlers:
        handler.flush()
    return (log_dir / "jarvis.log").read_text(encoding="utf-8")


def test_crea_jarvis_log_en_la_carpeta_del_registro_y_la_crea_si_falta(tmp_path):
    log_dir = tmp_path / "local" / "logs"
    setup_logging(log_dir)
    logging.getLogger("jarvis_assistant.prueba").info("arranque")
    assert "arranque" in read_log(log_dir)


def test_el_registro_rota_en_5_archivos_de_1_mb(tmp_path):
    handler = setup_logging(tmp_path)
    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    assert handler.maxBytes == MIB
    assert handler.backupCount == 4  # jarvis.log + 4 copias = 5 archivos


def test_al_superar_el_tamano_conserva_como_maximo_5_archivos(tmp_path):
    setup_logging(tmp_path)
    logger = logging.getLogger("jarvis_assistant.prueba")
    line = "x" * 1000
    for _ in range(7 * 1024):  # unos 7 MiB
        logger.info(line)
    files = sorted(path.name for path in tmp_path.iterdir())
    assert files == ["jarvis.log", "jarvis.log.1", "jarvis.log.2", "jarvis.log.3", "jarvis.log.4"]
    assert all(path.stat().st_size <= MIB + 2000 for path in tmp_path.iterdir())


def test_cada_linea_lleva_fecha_nivel_hilo_componente_y_mensaje(tmp_path):
    setup_logging(tmp_path)
    logging.getLogger("jarvis_assistant.core.fsm").warning("cambio de estado")
    line = read_log(tmp_path).splitlines()[-1]
    pattern = (
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} WARNING \[MainThread\] "
        r"jarvis_assistant\.core\.fsm: cambio de estado$"
    )
    assert re.match(pattern, line), line


def test_el_registro_se_escribe_en_utf8(tmp_path):
    setup_logging(tmp_path)
    logging.getLogger("jarvis_assistant.prueba").info("sesión «mañana»")
    assert "sesión «mañana»" in read_log(tmp_path)


def test_no_escribe_en_la_consola(tmp_path):
    before = set(logging.getLogger().handlers)
    handler = setup_logging(tmp_path)
    assert set(logging.getLogger().handlers) - before == {handler}


def test_con_el_nivel_predeterminado_no_se_registra_el_texto_transcrito(tmp_path):
    setup_logging(tmp_path)
    logger = logging.getLogger("jarvis_assistant.transcriber")
    logger.debug("texto transcrito: abre el bloc de notas")
    logger.info("transcripción en 0,4 s")
    content = read_log(tmp_path)
    assert "abre el bloc de notas" not in content  # RES-48
    assert "transcripción en 0,4 s" in content


def test_en_nivel_debug_se_registra_el_texto_transcrito(tmp_path):
    setup_logging(tmp_path, "DEBUG")
    logging.getLogger("jarvis_assistant.transcriber").debug("texto transcrito: hola")
    assert "texto transcrito: hola" in read_log(tmp_path)


def test_un_nivel_desconocido_es_un_error(tmp_path):
    with pytest.raises(ValueError):
        setup_logging(tmp_path, "TRACE")


def test_configurar_dos_veces_no_duplica_las_lineas(tmp_path):
    setup_logging(tmp_path)
    setup_logging(tmp_path, "DEBUG")
    logging.getLogger("jarvis_assistant.prueba").info("una sola vez")
    assert read_log(tmp_path).count("una sola vez") == 1


def test_una_excepcion_no_capturada_del_hilo_principal_llega_al_registro(tmp_path):
    setup_logging(tmp_path)
    install_excepthooks()
    try:
        raise RuntimeError("fallo principal")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())
    content = read_log(tmp_path)
    assert "CRITICAL" in content
    assert "RuntimeError: fallo principal" in content
    assert "Traceback" in content


def test_keyboard_interrupt_no_se_registra_como_fallo(tmp_path, monkeypatch):
    setup_logging(tmp_path)
    install_excepthooks()
    forwarded = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *args: forwarded.append(args[0]))
    sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
    assert forwarded == [KeyboardInterrupt]
    assert "CRITICAL" not in read_log(tmp_path)


def test_una_excepcion_no_capturada_de_otro_hilo_llega_al_registro(tmp_path):
    setup_logging(tmp_path)
    install_excepthooks()

    def boom():
        raise ValueError("fallo de audio")

    thread = threading.Thread(target=boom, name="audio")
    thread.start()
    thread.join()
    content = read_log(tmp_path)
    assert "hilo audio" in content
    assert "ValueError: fallo de audio" in content


async def test_una_excepcion_no_capturada_de_asyncio_llega_al_registro(tmp_path):
    setup_logging(tmp_path)
    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()
    install_asyncio_handler(loop)
    try:

        def boom():
            raise KeyError("fallo del núcleo")

        loop.call_soon(boom)
        await asyncio.sleep(0.01)
    finally:
        loop.set_exception_handler(previous)
    content = read_log(tmp_path)
    assert "ERROR" in content
    assert "KeyError: 'fallo del núcleo'" in content


def test_el_formato_no_incluye_datos_de_audio():
    assert "%(message)s" in logging_setup.LOG_FORMAT
