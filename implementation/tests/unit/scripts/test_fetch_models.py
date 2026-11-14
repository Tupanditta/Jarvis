"""Pruebas de scripts/fetch_models.py (T-0.9, RES-46): sin red, con descarga inyectable.

- ``ModelFile``: ``url``, ``relative_path`` (con ``/``, relativa a models/) y ``sha256``.
- ``MANIFEST``: los modelos de RES-46 más la ficha de licencia de la voz.
- ``fetch(manifest, models_dir, download) -> list[str]``: deja cada archivo verificado en su
  ruta, sin volver a descargar los que ya están y son correctos, y devuelve las rutas
  exigidas que siguen faltando.
- Suma errónea: ``ChecksumMismatchError`` sin dejar el archivo ni restos parciales.
"""
import dataclasses
import hashlib
import re
from pathlib import Path

import pytest

BUENAS_NOCHES = "openwakeword/buenas_noches_jarvis.onnx"

RUTAS_SECCION_6 = {
    "openwakeword/hey_jarvis_v0.1.onnx",
    "openwakeword/silero_vad.onnx",
    "openwakeword/melspectrogram.onnx",
    "openwakeword/embedding_model.onnx",
    "faster-whisper-small/model.bin",
    "faster-whisper-small/config.json",
    "faster-whisper-small/tokenizer.json",
    "faster-whisper-small/vocabulary.txt",
    "piper/es_ES-davefx-medium.onnx",
    "piper/es_ES-davefx-medium.onnx.json",
}

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
SRC_DIR = Path(__file__).resolve().parents[3] / "src" / "jarvis_assistant"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bytes_for(url: str) -> bytes:
    return f"contenido-de-prueba:{url}".encode()


def _fake_download(url: str) -> bytes:
    return _bytes_for(url)


def _manifest_con_sumas_de_prueba(fm):
    """MANIFEST real con las sumas sustituidas por las de los bytes de prueba."""
    return [dataclasses.replace(e, sha256=_sha(_bytes_for(e.url))) for e in fm.MANIFEST]


@pytest.fixture
def fm():
    import fetch_models
    return fetch_models


def _entry(fm, relative_path="piper/x.bin", url="https://ejemplo.invalid/x", data=None):
    data = _bytes_for(url) if data is None else data
    return fm.ModelFile(url=url, relative_path=relative_path, sha256=_sha(data))


def _files_under(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


# --- Manifiesto (D-36, §6) ---------------------------------------------------------------

def test_manifiesto_contiene_las_rutas_de_la_seccion_6_mas_la_ficha_de_la_voz(fm):
    rutas = {e.relative_path for e in fm.MANIFEST}

    assert rutas >= RUTAS_SECCION_6
    fichas = rutas - RUTAS_SECCION_6
    assert len(fichas) == 1
    assert next(iter(fichas)).startswith("piper/")


def test_manifiesto_cubre_los_modelos_que_exige_el_arranque(fm):
    from jarvis_assistant import paths

    exigidas = {ruta.as_posix() for ruta in paths.required_models()}

    assert exigidas <= {e.relative_path for e in fm.MANIFEST}


def test_entradas_del_manifiesto_tienen_url_https_y_sha256_valido(fm):
    for e in fm.MANIFEST:
        assert e.url.startswith("https://"), e.relative_path
        assert re.fullmatch(r"[0-9a-f]{64}", e.sha256), e.relative_path


def test_manifiesto_no_incluye_buenas_noches_jarvis(fm):
    nombres = {Path(e.relative_path).name for e in fm.MANIFEST}

    assert "buenas_noches_jarvis.onnx" not in nombres


# --- fetch -------------------------------------------------------------------------------

def test_fetch_escribe_cada_archivo_en_su_ruta(fm, tmp_path):
    manifest = _manifest_con_sumas_de_prueba(fm)

    fm.fetch(manifest, tmp_path, _fake_download)

    for e in manifest:
        assert (tmp_path / e.relative_path).read_bytes() == _bytes_for(e.url), e.relative_path


def test_fetch_descarga_cada_url_del_manifiesto_una_vez(fm, tmp_path):
    manifest = _manifest_con_sumas_de_prueba(fm)
    pedidas = []

    def download(url):
        pedidas.append(url)
        return _bytes_for(url)

    fm.fetch(manifest, tmp_path, download)

    assert sorted(pedidas) == sorted(e.url for e in manifest)


def test_fetch_completo_no_deja_nada_sin_instalar(fm, tmp_path):
    manifest = _manifest_con_sumas_de_prueba(fm)

    faltan = fm.fetch(manifest, tmp_path, _fake_download)

    assert faltan == []


def test_fetch_no_vuelve_a_descargar_lo_que_ya_esta_y_es_correcto(fm, tmp_path):
    manifest = _manifest_con_sumas_de_prueba(fm)
    fm.fetch(manifest, tmp_path, _fake_download)
    pedidas = []

    def download(url):
        pedidas.append(url)
        return _bytes_for(url)

    assert fm.fetch(manifest, tmp_path, download) == []
    assert pedidas == []


def test_fetch_sustituye_un_archivo_existente_con_suma_erronea(fm, tmp_path):
    entry = _entry(fm, "piper/x.bin")
    destino = tmp_path / "piper" / "x.bin"
    destino.parent.mkdir(parents=True)
    destino.write_bytes(b"descarga interrumpida")

    fm.fetch([entry], tmp_path, _fake_download)

    assert destino.read_bytes() == _bytes_for(entry.url)


def test_main_informa_de_cada_archivo_y_termina_bien(fm, tmp_path, monkeypatch, capsys):
    manifest = _manifest_con_sumas_de_prueba(fm)
    monkeypatch.setattr(fm, "MANIFEST", manifest)
    monkeypatch.setattr(fm, "download_https", _fake_download)

    assert fm.main([str(tmp_path)]) == 0
    salida = capsys.readouterr().out
    assert salida.count("descargado") == len(manifest)
    assert "Modelos completos" in salida

    assert fm.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.count("ya instalado") == len(manifest)


def test_main_termina_con_error_si_falta_un_modelo(fm, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fm, "MANIFEST", [_entry(fm, "openwakeword/silero_vad.onnx")])
    monkeypatch.setattr(fm, "download_https", _fake_download)

    assert fm.main([str(tmp_path)]) == 1
    assert "Falta: piper/es_ES-davefx-medium.onnx" in capsys.readouterr().err


def test_main_termina_con_error_si_una_suma_no_coincide(fm, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fm, "MANIFEST", [_entry(fm, data=b"otros bytes")])
    monkeypatch.setattr(fm, "download_https", _fake_download)

    assert fm.main([str(tmp_path)]) == 1
    assert "SHA-256" in capsys.readouterr().err


def test_fetch_no_crea_buenas_noches_jarvis(fm, tmp_path):
    manifest = _manifest_con_sumas_de_prueba(fm)

    fm.fetch(manifest, tmp_path, _fake_download)

    assert not (tmp_path / BUENAS_NOCHES).exists()


def test_fetch_informa_de_los_archivos_de_la_seccion_6_no_descargados(fm, tmp_path):
    manifest = [_entry(fm, "openwakeword/silero_vad.onnx")]

    faltan = {Path(f).as_posix() for f in fm.fetch(manifest, tmp_path, _fake_download)}

    assert faltan == (RUTAS_SECCION_6 - {"openwakeword/silero_vad.onnx"})


def test_fetch_crea_los_directorios_intermedios(fm, tmp_path):
    destino = tmp_path / "aun_no_existe"
    manifest = [_entry(fm, "faster-whisper-small/model.bin")]

    fm.fetch(manifest, destino, _fake_download)

    assert (destino / "faster-whisper-small" / "model.bin").is_file()


# --- Verificación SHA-256 ----------------------------------------------------------------

def test_fetch_rechaza_una_suma_erronea(fm, tmp_path):
    erronea = dataclasses.replace(_entry(fm), sha256=_sha(b"otra cosa"))

    with pytest.raises(ValueError):
        fm.fetch([erronea], tmp_path, _fake_download)


def test_fetch_con_suma_erronea_no_deja_archivos_parciales(fm, tmp_path):
    erronea = dataclasses.replace(_entry(fm, "piper/x.bin"), sha256=_sha(b"otra cosa"))

    with pytest.raises(ValueError):
        fm.fetch([erronea], tmp_path, _fake_download)

    assert _files_under(tmp_path) == []


def test_fetch_con_suma_erronea_conserva_los_archivos_anteriores_correctos(fm, tmp_path):
    buena = _entry(fm, "openwakeword/silero_vad.onnx", url="https://ejemplo.invalid/a")
    mala = dataclasses.replace(
        _entry(fm, "piper/x.bin", url="https://ejemplo.invalid/b"), sha256=_sha(b"otra cosa")
    )

    with pytest.raises(ValueError):
        fm.fetch([buena, mala], tmp_path, _fake_download)

    assert _files_under(tmp_path) == [tmp_path / "openwakeword" / "silero_vad.onnx"]


# --- Seguridad: rutas del manifiesto y esquema de la URL (T-33, D-36) ---------------------

@pytest.mark.parametrize("ruta", ["../fuera.bin", "piper/../../fuera.bin", "/absoluta.bin"])
def test_fetch_rechaza_rutas_con_punto_punto_o_absolutas_sin_escribir_fuera(fm, tmp_path, ruta):
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    with pytest.raises(ValueError):
        fm.fetch([_entry(fm, ruta)], models_dir, _fake_download)

    assert _files_under(tmp_path) == []


@pytest.mark.parametrize(
    "url", ["http://ejemplo.invalid/x", "file:///etc/passwd", "ftp://ejemplo.invalid/x"]
)
def test_download_https_rechaza_esquemas_distintos_de_https_sin_abrir_conexion(
    fm, monkeypatch, url
):
    conexiones = []
    monkeypatch.setattr(
        fm.urllib.request, "urlopen", lambda *args, **kwargs: conexiones.append(args)
    )

    with pytest.raises(ValueError):
        fm.download_https(url)

    assert conexiones == []


# --- Aislamiento -------------------------------------------------------------------------

def test_ningun_modulo_de_jarvis_assistant_importa_fetch_models():
    importadores = [
        p.name for p in SRC_DIR.rglob("*.py") if "fetch_models" in p.read_text(encoding="utf-8")
    ]

    assert importadores == []


def test_importar_el_script_no_descarga_ni_escribe(fm, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    import importlib
    importlib.reload(fm)

    assert _files_under(tmp_path) == []
