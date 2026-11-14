"""Catálogo único de frases del asistente (catalogo-intenciones.md, sección 5; RES-27).

No hay generación libre de texto: cada frase es un identificador y una plantilla. Las frases
de cada módulo de acción se añaden con su módulo. El asistente trata al usuario de usted.
"""
import string

from jarvis_assistant.core.action_api import Phrase

PHRASES: dict[str, str] = {
    "ciclo.apertura": "Sesión iniciada. Le escucho.",
    "ciclo.escucha": "Le escucho.",
    "ciclo.reposo": "A su disposición.",
    "ciclo.cierre": "Buenas noches. Sesión cerrada.",
    "general.cancelado": "Cancelado.",
    "general.operacion_cancelada": "Operación cancelada.",
    "general.no_entendido": "No le he entendido.",
    "general.error": "Ha ocurrido un error.",
    "general.nada_que_repetir": "No hay nada que repetir.",
    "general.ayuda": "Estas son las órdenes disponibles.",
    "general.indice_invalido": "No hay ningún elemento {n}.",
    "general.no_disponible": "No está disponible en este sistema.",
    "config.error": "Hay un error en la configuración de {archivo}. Uso la anterior.",
    "entidad.numero": "No he entendido el número.",
    "entidad.duracion": "No he entendido la duración.",
    "entidad.fecha": "No he entendido la fecha.",
    "entidad.fecha_pasada": "Esa fecha ya ha pasado.",
    "entidad.nombre": "Ese nombre no es válido.",
    "entidad.no_encontrado": "No encuentro {nombre}.",
    "ruta.no_existe": "La carpeta {nombre} no existe.",
    "ruta.no_es_carpeta": "{nombre} no es una carpeta.",
    "ruta.gestor_fallo": "No he podido abrir el gestor de archivos.",
}

LIFECYCLE_IDS = ("ciclo.apertura", "ciclo.escucha", "ciclo.reposo", "ciclo.cierre")

# Frases sin parámetros que se sintetizan al arrancar, además de las del ciclo de vida.
PRELOADED_IDS = (
    *LIFECYCLE_IDS,
    "general.cancelado",
    "general.operacion_cancelada",
    "general.no_entendido",
    "general.error",
)


class PhraseError(Exception):
    """La frase no está en el catálogo o le falta un parámetro."""


def parameters(phrase_id: str) -> tuple[str, ...]:
    """Nombres de los parámetros de la plantilla de `phrase_id`."""
    template = _template(phrase_id)
    return tuple(name for _, name, _, _ in string.Formatter().parse(template) if name)


def render(phrase: Phrase) -> str:
    """Texto de la frase con sus parámetros."""
    template = _template(phrase.id)
    try:
        return template.format(**phrase.params)
    except KeyError as missing:
        raise PhraseError(f"A la frase {phrase.id!r} le falta el parámetro {missing}") from None


def _template(phrase_id: str) -> str:
    try:
        return PHRASES[phrase_id]
    except KeyError:
        raise PhraseError(f"La frase {phrase_id!r} no está en el catálogo") from None
