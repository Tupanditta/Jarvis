"""Entidad `COMMAND_LINE`: un binario de la lista permitida y sus argumentos (RN-45).

La primera palabra, tras los alias, debe ser un binario permitido. El resto son argumentos,
tal como se escribieron, con «guion» → `-`, «guion guion» → `--` y «punto» → `.`.
"""
from collections.abc import Sequence

from jarvis_assistant.config import Binary
from jarvis_assistant.core.action_api import CommandLine
from jarvis_assistant.intent_router.normalizer import Tokens, normalize

_SENTENCE_END = ".?!"


class NotAllowedError(ValueError):
    """La primera palabra no es un binario de la lista permitida."""


def parse(tokens: Tokens, start: int, end: int, binaries: Sequence[Binary]) -> CommandLine:
    """Comando de las palabras normalizadas `start` a `end` (sin incluir) de `tokens`."""
    words = tokens.words[start:end]
    best: tuple[int, Binary] | None = None
    for binary in binaries:
        for spelling in (binary.name, *binary.aliases):
            key = tuple(normalize(spelling).split())
            if key and words[: len(key)] == key and (best is None or len(key) > best[0]):
                best = (len(key), binary)
    if best is None:
        raise NotAllowedError(" ".join(words))
    size, binary = best
    first = tokens.sources[start + size - 1][1] + 1
    last = tokens.sources[end - 1][1]
    return CommandLine(
        name=binary.name,
        executable=binary.executable,
        args=_arguments(list(tokens.originals[first : last + 1])),
        timeout_seconds=binary.timeout_seconds,
    )


def _arguments(raw: list[str]) -> tuple[str, ...]:
    if raw and len(raw[-1]) > 1 and raw[-1][-1] in _SENTENCE_END:
        raw[-1] = raw[-1].rstrip(_SENTENCE_END) or raw[-1]  # punto final de la frase
    args: list[str] = []
    prefix = ""  # guiones pendientes de la palabra siguiente
    join = False  # un «punto» une la palabra siguiente con la anterior
    for index, word in enumerate(raw):
        key = word.lower()
        if key == "guion":
            prefix += "-"
        elif key == "punto":
            if args and not prefix and index + 1 < len(raw):
                join = True
            else:
                args.append(prefix + ".")
                prefix = ""
        elif join:
            args[-1] = f"{args[-1]}.{word}"
            join = False
        else:
            args.append(prefix + word)
            prefix = ""
    if prefix:
        args.append(prefix)
    return tuple(args)
