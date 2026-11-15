"""Carpetas de datos, configuración, registro y modelos (T-0.4)."""
from pathlib import Path

from fakes.platform import FakePlatform
from jarvis_assistant import paths


def test_la_raiz_de_la_aplicacion_es_implementation():
    assert (paths.app_root() / "pyproject.toml").is_file()


def test_los_modelos_estan_en_models_bajo_la_raiz():
    assert paths.models_dir() == paths.app_root() / "models"


def test_las_carpetas_del_usuario_vienen_del_adaptador(tmp_path):
    platform = FakePlatform(tmp_path)
    app_paths = paths.AppPaths.from_platform(platform)
    assert app_paths.data_dir == platform.data_dir()
    assert app_paths.config_dir == platform.config_dir()
    assert app_paths.log_dir == platform.log_dir()
    assert app_paths.models_dir == paths.models_dir()


def test_ensure_crea_las_carpetas_del_usuario_y_no_la_de_modelos(tmp_path):
    app_paths = paths.AppPaths(
        data_dir=tmp_path / "d" / "data",
        config_dir=tmp_path / "c" / "config",
        log_dir=tmp_path / "d" / "logs",
        models_dir=tmp_path / "models",
    )
    app_paths.ensure()
    app_paths.ensure()
    assert app_paths.data_dir.is_dir()
    assert app_paths.config_dir.is_dir()
    assert app_paths.log_dir.is_dir()
    assert not app_paths.models_dir.exists()


def test_los_archivos_del_usuario_estan_en_la_carpeta_de_datos(tmp_path):
    app_paths = paths.AppPaths(tmp_path / "data", tmp_path / "cfg", tmp_path / "log", tmp_path)
    assert app_paths.db_path == tmp_path / "data" / "jarvis.db"


def test_los_modelos_exigidos_son_solo_los_de_la_voz():
    assert set(paths.required_models()) == {
        Path("piper/es_ES-davefx-medium.onnx"),
        Path("piper/es_ES-davefx-medium.onnx.json"),
    }


def test_los_modelos_exigidos_siguen_a_la_configuracion():
    required = paths.required_models(voice="es_ES-otra-medium")
    assert Path("piper/es_ES-otra-medium.onnx") in required
    assert not any("davefx" in str(path) for path in required)


def test_missing_models_lista_los_que_faltan(tmp_path):
    required = paths.required_models()
    for relative in required[1:]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")
    assert paths.missing_models(tmp_path) == [required[0]]
