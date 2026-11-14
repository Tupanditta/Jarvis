"""Guiones de inicio automático, sobre un directorio temporal (proceso.md)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
POWERSHELL = shutil.which("powershell")

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or POWERSHELL is None, reason="requiere Windows PowerShell"
)


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    command = [
        POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPTS / script),
        *args,
    ]
    return subprocess.run(command, capture_output=True, text=True, timeout=25)


def fake_venv(tmp_path: Path) -> Path:
    venv = tmp_path / "venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "Scripts" / "pythonw.exe").write_bytes(b"")
    return venv


def test_instalar_y_desinstalar_son_idempotentes(tmp_path):
    startup = tmp_path / "Inicio"
    startup.mkdir()
    venv = fake_venv(tmp_path)
    shortcut = startup / "Jarvis.lnk"
    for _ in range(2):
        result = run("install_startup.ps1", "-StartupDir", str(startup), "-VenvDir", str(venv))
        assert result.returncode == 0, result.stderr
        assert shortcut.is_file()
    for _ in range(2):
        result = run("uninstall_startup.ps1", "-StartupDir", str(startup))
        assert result.returncode == 0, result.stderr
        assert not shortcut.exists()


def test_sin_pythonw_no_se_crea_nada(tmp_path):
    startup = tmp_path / "Inicio"
    startup.mkdir()
    result = run(
        "install_startup.ps1", "-StartupDir", str(startup), "-VenvDir", str(tmp_path / "no-venv")
    )
    assert result.returncode != 0
    assert list(startup.iterdir()) == []
