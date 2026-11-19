"""Escritura del catálogo y de los binarios permitidos (`config.writer.save_launchers`)."""
from pathlib import Path

import pytest

from jarvis_assistant import config as cfg
from jarvis_assistant.config.writer import WriteError, save_launchers

APPS = (cfg.AppEntry("Editor", "C:/editor.exe", ("el editor",), ("--nuevo",)),)
PAGES = (cfg.PageEntry("Docs", "https://example.com/docs"),)


def write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def loaded(directory: Path) -> cfg.Config:
    config, errors = cfg.load(directory)
    assert [error for error in errors if not error.warning] == []
    return config


def test_guarda_el_catalogo_y_conserva_comentarios_y_demas_claves(tmp_path):
    write(tmp_path, "catalog.toml", "# Mío\ndiscover_installed_apps = false\n")
    save_launchers(tmp_path, cfg.Catalog(apps=APPS, pages=PAGES))
    text = (tmp_path / "catalog.toml").read_text(encoding="utf-8")
    assert text.startswith("# Mío")
    catalog = loaded(tmp_path).catalog
    assert (catalog.apps, catalog.pages) == (APPS, PAGES)
    assert catalog.discover_installed_apps is False
    assert not (tmp_path / "commands.toml").exists()  # lo que no se pide no se toca


def test_guarda_los_binarios_con_su_tiempo_maximo(tmp_path):
    binaries = (cfg.Binary("git", "git", ("guit",)), cfg.Binary("cargo", "C:/cargo.exe", (), 90))
    save_launchers(tmp_path, binaries=binaries)
    assert loaded(tmp_path).binaries == binaries
    assert not (tmp_path / "catalog.toml").exists()


def test_sin_binarios_no_vuelven_los_de_fabrica(tmp_path):
    save_launchers(tmp_path, binaries=())
    assert loaded(tmp_path).binaries == ()


def test_un_archivo_con_errores_no_se_sobrescribe(tmp_path):
    broken = '[[pages]]\nname = "X"\nurl = "ftp://x"\n'
    write(tmp_path, "catalog.toml", broken)
    with pytest.raises(WriteError) as raised:
        save_launchers(tmp_path, cfg.Catalog(apps=APPS))
    assert raised.value.file == "catalog.toml"
    assert (tmp_path / "catalog.toml").read_text(encoding="utf-8") == broken


def test_un_resultado_no_valido_no_se_escribe(tmp_path):
    repeated = (cfg.Binary("git", "git"), cfg.Binary("Git", "git2"))
    with pytest.raises(WriteError) as raised:
        save_launchers(tmp_path, binaries=repeated)
    assert raised.value.file == "commands.toml"
    assert not (tmp_path / "commands.toml").exists()
