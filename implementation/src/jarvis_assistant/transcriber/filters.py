"""Filtro de resultados del transcriptor: con ruido o silencio, Whisper inventa texto."""
from collections.abc import Sequence

from jarvis_assistant.intent_router.normalizer import normalize

# Frases que el modelo produce sin que nadie las diga, ya normalizadas.
SPURIOUS_PHRASES = frozenset(
    {
        "subtitulos realizados por la comunidad de amara.org",
        "subtitulos por la comunidad de amara.org",
        "subtitulado por la comunidad de amara.org",
        "subtitulos en español",
        "gracias por ver el video",
        "gracias por ver",
        "suscribete",
        "suscribete al canal",
        "hasta la proxima",
    }
)
_ECHO_TERMS = 3


def is_spurious(text: str) -> bool:
    return normalize(text) in SPURIOUS_PHRASES


def echoes_vocabulary(text: str, terms: Sequence[str]) -> bool:
    """El texto reproduce la indicación: tres o más términos seguidos y en el mismo orden."""
    normalized = f" {normalize(text)} "
    words = [normalize(term) for term in terms]
    words = [word for word in words if word]
    return any(
        f" {' '.join(words[index : index + _ECHO_TERMS])} " in normalized
        for index in range(len(words) - _ECHO_TERMS + 1)
    )


def filter_transcript(text: str, terms: Sequence[str] = ()) -> str:
    """El texto recortado, o vacío si es espurio o un eco de la indicación de vocabulario."""
    cleaned = " ".join(text.split())
    if not cleaned or is_spurious(cleaned) or echoes_vocabulary(cleaned, terms):
        return ""
    return cleaned
