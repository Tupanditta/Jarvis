"""Lanzamiento de binarios de consola sin intérprete de órdenes (RNF-27).

Vive aquí porque depende del sistema: en Windows, la bandera que oculta la ventana de
consola. El módulo Comandos lo usa como lanzador por defecto.
"""
import asyncio
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

CREATE_NO_WINDOW = 0x08000000  # `subprocess.CREATE_NO_WINDOW`, que solo existe en Windows


async def launch_process(executable: str, args: Sequence[str], cwd: Path) -> Any:
    """Lanza el binario sin intérprete de órdenes. `FileNotFoundError` si no existe."""
    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(executable)
    # La aplicación no tiene consola: sin esta bandera, Windows abre una ventana para cada
    # binario de consola y se ve un instante. Su salida llega igual por las tuberías.
    flags = CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return await asyncio.create_subprocess_exec(
        resolved, *args, cwd=str(cwd),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        creationflags=flags,
    )  # fmt: skip
