"""Varias órdenes en un mismo mensaje, separadas por `--`.

`lista -- abre github -- busca informe` son tres órdenes, en ese orden. El separador vale
suelto o pegado a la palabra anterior. Un `--` que empieza palabra (`git log --oneline`) es
una opción de un programa, no un separador.
"""
import re

_SEPARATOR = re.compile(r"(?<!\S)--+(?=\s|$)|(?<=[^\s-])--+")


def split_orders(text: str) -> list[str]:
    """Las órdenes del mensaje, en su orden y sin espacios alrededor. Las vacías se omiten."""
    return [part.strip() for part in _SEPARATOR.split(text) if part.strip()]
