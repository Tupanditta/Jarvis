"""Catálogo único de frases del asistente (catalogo-intenciones.md, sección 5; RES-27).

No hay generación libre de texto: cada frase es un identificador y una lista de plantillas
(variantes). Cada vez que se dice una frase se usa la siguiente variante de su lista; al llegar
al final se vuelve a la primera. Para añadir una variante basta con añadir otra cadena a la
lista; todas las variantes de una frase deben usar los mismos parámetros. Las frases de cada
módulo de acción se añaden con su módulo. El asistente trata al usuario de usted.
"""
import string

from jarvis_assistant.core.action_api import Phrase

PHRASES: dict[str, list[str]] = {
    "ciclo.apertura": [
        (
            "Es un placer tenerle de nuevo por aquí, señor. La sesión está iniciada y todo está "
            "listo. ¿En qué puedo ayudarle?"
        ),
    ],
    "ciclo.escucha": ["Le escucho, señor."],
    "ciclo.reposo": ["Permaneceré a su disposición, señor."],
    "ciclo.cierre": ["Buenas noches, señor. Procedo a cerrar la sesión. Que descanse."],
    "general.cancelado": ["De acuerdo, señor. He cancelado la acción."],
    "general.operacion_cancelada": ["La operación ha sido cancelada correctamente, señor."],
    "general.no_entendido": ["Disculpe, señor. No he conseguido entenderle. ¿Podría repetirlo?"],
    "general.error": ["Lo lamento, señor. Se ha producido un error."],
    "general.nada_que_repetir": ["No hay ningún mensaje anterior que pueda repetir, señor."],
    "general.ayuda": ["Por supuesto, señor. Estas son las órdenes que tengo disponibles."],
    "general.indice_invalido": ["Disculpe, señor. No existe ningún elemento con el número {n}."],
    "general.no_disponible": ["Lo siento, señor. Esta función no está disponible en el sistema."],
    "config.error": [
        (
            "He detectado un problema en la configuración de {archivo}, señor. Continuaré "
            "utilizando la última configuración válida."
        ),
    ],
    "entidad.numero": ["No he conseguido identificar el número indicado, señor."],
    "entidad.duracion": ["No he conseguido interpretar la duración, señor."],
    "entidad.fecha": ["No he conseguido identificar la fecha indicada, señor."],
    "entidad.fecha_pasada": [
        "Esa fecha ya ha quedado atrás, señor. Indíqueme una fecha posterior.",
    ],
    "entidad.nombre": ["El nombre indicado no parece válido, señor."],
    "entidad.no_encontrado": ["No he podido encontrar {nombre}, señor."],
    "ruta.no_existe": ["La carpeta {nombre} no existe, señor."],
    "ruta.no_es_carpeta": ["El elemento {nombre} no es una carpeta, señor."],
    "ruta.gestor_fallo": [
        "No he podido abrir el gestor de archivos, señor. Disculpe las molestias.",
    ],
    # Historial
    "historial.mostrado": ["Hay {sesiones} en el historial, señor."],
    "historial.actividades": ["La sesión {nombre} tiene {actividades}, señor."],
    "historial.no_existe": ["No existe la sesión {id}, señor."],
    # Comandos
    "comandos.cd": ["Directorio cambiado a {carpeta}, señor."],
    "comandos.ls": ["Hay {carpetas} y {archivos}, señor."],
    "comandos.pwd": ["Se encuentra en {ruta}, señor."],
    "comandos.arbol": ["El árbol tiene {carpetas} y {archivos}, señor."],
    "comandos.arbol_recortado": [
        (
            "El árbol tiene {carpetas} y {archivos}, señor. Se muestra solo una parte."
        ),
    ],
    "comandos.ejecutando": ["Ejecutando {comando}, señor."],
    "comandos.ok": ["{comando} ha terminado correctamente, señor."],
    "comandos.fallo": ["{comando} ha fallado, señor."],
    "comandos.no_permitido": ["Ese comando no está permitido, señor."],
    "comandos.no_encontrado": ["No encuentro el programa {nombre}, señor."],
    "comandos.tiempo": ["El comando ha tardado demasiado, señor. Lo he detenido."],
    "comandos.ocupado": ["Ya hay un comando en ejecución, señor."],
    "comandos.consola": ["Abriendo una terminal, señor."],
    # Apertura y Búsqueda
    "apertura.abriendo": ["Abriendo {nombre}, señor."],
    "apertura.fallo": ["No he podido abrir {nombre}, señor."],
    "apertura.sin_edge": ["Microsoft Edge no está instalado, señor."],
    "apertura.ventana_cerrada": ["Esa ventana ya no está abierta, señor."],
    "busqueda.ninguno": ["No he encontrado nada para {consulta}, señor."],
    "busqueda.uno": ["He encontrado {nombre} en {carpeta}, señor."],
    "busqueda.varios": [
        (
            "He encontrado {n} resultados, señor. El primero es {nombre}, en {carpeta}."
        ),
    ],
    "busqueda.limitada": ["La búsqueda se ha limitado a sus carpetas, señor."],
    "busqueda.instalar": ["Instale Everything para buscar en todo el disco, señor."],
    "busqueda.no_existe": ["Ese archivo ya no existe, señor."],
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


def count(n: int, singular: str, plural: str) -> str:
    """Recuento con singular y plural: «1 carpeta», «3 carpetas»."""
    return f"{n} {singular if n == 1 else plural}"


def parameters(phrase_id: str) -> tuple[str, ...]:
    """Nombres de los parámetros de la plantilla de `phrase_id` (los de su primera variante)."""
    return _fields(_variants(phrase_id)[0])


def variants(phrase_id: str) -> tuple[str, ...]:
    """Todas las plantillas de `phrase_id`, en el orden en que se usan."""
    return tuple(_variants(phrase_id))


def render(phrase: Phrase) -> str:
    """Texto de la frase con sus parámetros, en la variante que toca decir ahora."""
    templates = _variants(phrase.id)
    template = templates[_turn.get(phrase.id, 0) % len(templates)]
    try:
        return template.format(**phrase.params)
    except KeyError as missing:
        raise PhraseError(f"A la frase {phrase.id!r} le falta el parámetro {missing}") from None


def advance(phrase_id: str) -> None:
    """Pasa a la siguiente variante de `phrase_id`; tras la última vuelve a la primera."""
    templates = _variants(phrase_id)
    _turn[phrase_id] = (_turn.get(phrase_id, 0) + 1) % len(templates)


def reset_rotation() -> None:
    """Vuelve todas las frases a su primera variante."""
    _turn.clear()


# Variante que toca decir de cada frase. Solo se guarda en memoria: al arrancar, la primera.
_turn: dict[str, int] = {}


def _fields(template: str) -> tuple[str, ...]:
    return tuple(name for _, name, _, _ in string.Formatter().parse(template) if name)


def _variants(phrase_id: str) -> list[str]:
    try:
        templates = PHRASES[phrase_id]
    except KeyError:
        raise PhraseError(f"La frase {phrase_id!r} no está en el catálogo") from None
    if not templates:
        raise PhraseError(f"La frase {phrase_id!r} no tiene ninguna variante")
    return templates
