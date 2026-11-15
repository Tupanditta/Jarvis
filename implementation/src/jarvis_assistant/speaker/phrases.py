"""Catálogo único de frases del asistente (catalogo-intenciones.md, sección 5; RES-27).

No hay generación libre de texto: cada frase es un identificador y una plantilla. Las frases
de cada módulo de acción se añaden con su módulo. El asistente trata al usuario de usted.
"""
import string

from jarvis_assistant.core.action_api import Phrase

PHRASES: dict[str, str] = {
    "ciclo.apertura": "Es un placer tenerle de nuevo por aquí, señor. La sesión está iniciada y todo está listo. ¿En qué puedo ayudarle?",
    "ciclo.escucha": "Le escucho, señor.",
    "ciclo.reposo": "Permaneceré a su disposición, señor.",
    "ciclo.cierre": "Buenas noches, señor. Procedo a cerrar la sesión. Que descanse.",
    "general.cancelado": "De acuerdo, señor. He cancelado la acción.",
    "general.operacion_cancelada": "La operación ha sido cancelada correctamente, señor.",
    "general.no_entendido": "Disculpe, señor. No he conseguido entenderle. ¿Podría repetirlo?",
    "general.error": "Lo lamento, señor. Se ha producido un error.",
    "general.nada_que_repetir": "No hay ningún mensaje anterior que pueda repetir, señor.",
    "general.ayuda": "Por supuesto, señor. Estas son las órdenes que tengo disponibles.",
    "general.indice_invalido": "Disculpe, señor. No existe ningún elemento con el número {n}.",
    "general.no_disponible": "Lo siento, señor. Esta función no está disponible en el sistema.",
    "config.error": "He detectado un problema en la configuración de {archivo}, señor. Continuaré utilizando la última configuración válida.",
    "entidad.numero": "No he conseguido identificar el número indicado, señor.",
    "entidad.duracion": "No he conseguido interpretar la duración, señor.",
    "entidad.fecha": "No he conseguido identificar la fecha indicada, señor.",
    "entidad.fecha_pasada": "Esa fecha ya ha quedado atrás, señor. Indíqueme una fecha posterior.",
    "entidad.nombre": "El nombre indicado no parece válido, señor.",
    "entidad.no_encontrado": "No he podido encontrar {nombre}, señor.",
    "ruta.no_existe": "La carpeta {nombre} no existe, señor.",
    "ruta.no_es_carpeta": "El elemento {nombre} no es una carpeta, señor.",
    "ruta.gestor_fallo": "No he podido abrir el gestor de archivos, señor. Disculpe las molestias."
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
