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
        "Es un placer tenerle de nuevo por aquí, señor. Todo está listo. ¿En qué puedo ayudarle?",
        "Sesión iniciada, señor. Cuando quiera, podemos empezar. ¿Cuál es nuestra primera tarea?",
        "Qué alegría tenerle de vuelta, señor. Estoy a su disposición. ¿Por dónde empezamos?",
    ],
    "ciclo.escucha": [
        "Le escucho, señor.",
        "Dígame, señor.",
        "Adelante, señor. Estoy escuchando.",
        "Hola de nuevo, señor.",
    ],
    "ciclo.reposo": [
        "Permaneceré a su disposición, señor.",
        "De acuerdo, señor. Quedo atento.",
        "Muy bien, señor. Aquí estaré cuando me necesite.",
        "Ha sido un placer, señor. Me mantengo a la espera.",
        "Perfecto, señor. Puede llamarme cuando quiera.",
    ],
    "ciclo.cierre": [
        "Buenas noches, señor. Cierro la sesión. Que descanse.",
        "Hasta luego, señor. La sesión queda cerrada. Que descanse.",
        "De acuerdo, señor. Apago la sesión por ahora. Buenas noches.",
        "Sesión cerrada, señor. Ha sido un placer ayudarle.",
        "Que descanse, señor. Estaré aquí cuando vuelva.",
    ],
    "general.cancelado": [
        "De acuerdo, señor. He cancelado la acción.",
        "Entendido, señor. Lo dejo cancelado.",
        "Muy bien, señor. No continuaré con esa acción.",
        "Cancelado, señor. No se ha realizado ningún cambio.",
        "Sin problema, señor. La acción queda anulada.",
    ],
    "general.operacion_cancelada": [
        "La operación ha sido cancelada correctamente, señor.",
        "De acuerdo, señor. La operación queda cancelada.",
        "Listo, señor. He detenido la operación.",
        "Ya está, señor. No continuaré con ese proceso.",
        "Operación cancelada, señor. Todo queda como estaba.",
    ],
    "general.no_entendido": [
        "Disculpe, señor. No he conseguido entenderle. ¿Podría repetirlo?",
        "No estoy seguro de haberle entendido, señor. ¿Puede intentarlo de nuevo?",
        "Perdón, señor. Esa orden no me ha quedado clara.",
        "No he captado bien lo que necesita, señor. ¿Me lo repite?",
        "Creo que se me ha escapado algo, señor. ¿Puede decirlo de otra manera?",
    ],
    "general.error": [
        "Lo lamento, señor. Se ha producido un error.",
        "Disculpe, señor. Algo no ha salido como esperaba.",
        "Ha ocurrido un problema, señor. No he podido completar la operación.",
        "Lo siento, señor. La operación no se ha podido realizar.",
        "Parece que he encontrado un inconveniente, señor. Puede intentarlo de nuevo.",
    ],
    "general.nada_que_repetir": [
        "No hay ningún mensaje anterior que pueda repetir, señor.",
        "Todavía no tengo nada que repetir, señor.",
        "No encuentro una respuesta anterior para repetir, señor.",
        "Aún no le he dado ninguna respuesta que pueda repetir, señor.",
        "No hay una respuesta previa disponible, señor.",
    ],
    "general.ayuda": [
        "Por supuesto, señor. Estas son las órdenes que tengo disponibles.",
        "Claro que sí, señor. Le muestro lo que puedo hacer.",
        "Será un placer ayudarle, señor. Estas son mis opciones.",
        "Por supuesto, señor. Aquí tiene las funciones que conozco.",
        "Con mucho gusto, señor. Le explico las órdenes disponibles.",
    ],
    "general.indice_invalido": [
        "Disculpe, señor. No existe ningún elemento con el número {n}.",
        "No encuentro ningún elemento con el índice {n}, señor.",
        "El número {n} no corresponde a ningún resultado, señor.",
        "Ese índice no es válido, señor. No hay ningún elemento {n}.",
        "No hay un resultado número {n}, señor. Revise el índice indicado.",
    ],
    "general.no_disponible": [
        "Lo siento, señor. Esta función no está disponible en el sistema.",
        "Disculpe, señor. Esa función todavía no está disponible.",
        "No puedo ofrecerle esa función ahora mismo, señor.",
        "Esa opción no está disponible por el momento, señor.",
        "Aún no puedo hacer eso, señor. Disculpe las molestias.",
    ],
    "config.error": [
        "He detectado un problema en la configuración de {archivo}, señor. Usaré la última válida.",
        "La configuración de {archivo} tiene un problema, señor. Mantendré la anterior.",
        "No he podido cargar correctamente {archivo}, señor. Continuaré con la configuración previa.",
        "Hay un error en {archivo}, señor. Para evitar problemas, conservaré la última versión válida.",
        "La configuración de {archivo} no es válida, señor. Seguiré usando la configuración anterior.",
    ],
    "entidad.numero": [
        "No he conseguido identificar el número indicado, señor.",
        "No he reconocido ese número, señor. ¿Puede repetirlo?",
        "Necesito que me indique un número más claro, señor.",
        "No logro saber qué número quiere decir, señor.",
        "Ese número no me ha quedado claro, señor.",
    ],
    "entidad.duracion": [
        "No he conseguido interpretar la duración, señor.",
        "No he entendido cuánto tiempo desea, señor.",
        "La duración no me ha quedado clara, señor. ¿Puede repetirla?",
        "Necesito una duración más concreta, señor.",
        "No he podido identificar el tiempo indicado, señor.",
    ],
    "entidad.fecha": [
        "No he conseguido identificar la fecha indicada, señor.",
        "No he entendido qué fecha desea, señor.",
        "La fecha no me ha quedado clara, señor. ¿Puede repetirla?",
        "Necesito una fecha más concreta, señor.",
        "No he podido reconocer la fecha que ha indicado, señor.",
    ],
    "entidad.fecha_pasada": [
        "Esa fecha ya ha quedado atrás, señor. Indíqueme una fecha posterior.",
        "Esa fecha ya pasó, señor. ¿Me indica otra más adelante?",
        "No puedo usar una fecha pasada, señor. Dígame una posterior.",
        "La fecha indicada ya no está disponible, señor. Necesito una futura.",
        "Esa fecha pertenece al pasado, señor. Pruebe con una posterior.",
    ],
    "entidad.nombre": [
        "El nombre indicado no parece válido, señor.",
        "Ese nombre no es válido, señor. ¿Puede probar con otro?",
        "No puedo usar ese nombre, señor. Necesito uno distinto.",
        "El nombre no me sirve tal como está, señor.",
        "Disculpe, señor. Ese nombre no cumple los requisitos.",
    ],
    "entidad.no_encontrado": [
        "No he podido encontrar {nombre}, señor.",
        "No encuentro {nombre}, señor.",
        "No aparece {nombre} por aquí, señor.",
        "He buscado {nombre}, pero no lo he localizado, señor.",
        "No he dado con {nombre}, señor. ¿Quiere probar con otro nombre?",
    ],
    "ruta.no_existe": [
        "La carpeta {nombre} no existe, señor.",
        "No encuentro la carpeta {nombre}, señor.",
        "La ruta {nombre} no parece existir, señor.",
        "No he localizado la carpeta {nombre}, señor.",
        "Esa carpeta, {nombre}, no está disponible, señor.",
    ],
    "ruta.no_es_carpeta": [
        "El elemento {nombre} no es una carpeta, señor.",
        "{nombre} existe, pero no es una carpeta, señor.",
        "No puedo usar {nombre} como carpeta, señor.",
        "El elemento {nombre} no corresponde a una carpeta, señor.",
        "He encontrado {nombre}, pero es otro tipo de elemento, señor.",
    ],
    "ruta.gestor_fallo": [
        "No he podido abrir el gestor de archivos, señor. Disculpe las molestias.",
        "El gestor de archivos no se ha podido abrir, señor.",
        "He intentado abrir el gestor de archivos, pero ha fallado, señor.",
        "No consigo iniciar el gestor de archivos, señor. Puede intentarlo de nuevo.",
        "Ha habido un problema al abrir el gestor de archivos, señor.",
    ],
    # Historial
    "historial.mostrado": [
        "Hay {sesiones} en el historial, señor.",
        "He encontrado {sesiones} en su historial, señor.",
        "Su historial contiene {sesiones}, señor.",
        "Tiene {sesiones} registradas en el historial, señor.",
        "Aquí tiene {sesiones} de su historial, señor.",
    ],
    "historial.actividades": [
        "La sesión {nombre} tiene {actividades}, señor.",
        "En la sesión {nombre} hay {actividades}, señor.",
        "He encontrado {actividades} en la sesión {nombre}, señor.",
        "La sesión {nombre} reúne {actividades}, señor.",
        "Estas son las {actividades} de la sesión {nombre}, señor.",
    ],
    "historial.no_existe": [
        "No existe la sesión {id}, señor.",
        "No encuentro una sesión con el número {id}, señor.",
        "La sesión {id} no aparece en el historial, señor.",
        "No he localizado la sesión {id}, señor.",
        "No hay ninguna sesión registrada con el número {id}, señor.",
    ],
    "historial.es_actual": [
        "No se puede eliminar la sesión actual, señor.",
        "La sesión en curso no se puede eliminar, señor.",
        "Disculpe, señor. No puedo eliminar la sesión en la que estamos.",
    ],
    "historial.confirmar_eliminar": [
        "¿Elimino la sesión {id}, {nombre}, señor?",
        "¿Quiere que elimine la sesión {id}, {nombre}, señor?",
        "¿Confirma que elimino la sesión {id}, {nombre}, señor?",
    ],
    "historial.eliminada": [
        "Sesión {id} eliminada, señor.",
        "He eliminado la sesión {id}, señor.",
        "La sesión {id} ya no aparece en el historial, señor.",
    ],
    # Sesión
    "sesion.nombrada": [
        "Sesión renombrada a {nombre}, señor.",
        "A partir de ahora, esta sesión se llama {nombre}, señor.",
        "He llamado a la sesión {nombre}, señor.",
    ],
    "sesion.importante": [
        "Sesión marcada como importante, señor.",
        "Entendido, señor. Esta sesión queda marcada como importante.",
        "He marcado la sesión como importante, señor.",
    ],
    "sesion.no_importante": [
        "Sesión marcada como no importante, señor.",
        "De acuerdo, señor. La sesión ya no es importante.",
        "He quitado la importancia a la sesión, señor.",
    ],
    "sesion.desbordamiento": [
        "Se incorpora una nueva sesión importante, señor. La sesión {nombre} deja de serlo"
        " y se eliminará al cerrar.",
        "Ya hay diez sesiones importantes, señor. La sesión {nombre} deja de serlo y se"
        " eliminará al cerrar esta.",
    ],
    "sesion.proponer_nombre": [
        "¿Quiere llamar a esta sesión {nombre}, señor?",
        "¿Le pongo a esta sesión el nombre {nombre}, señor?",
    ],
    # Creación
    "creacion.creado": [
        "He creado {tipo} {nombre} en {carpeta}, señor.",
        "Listo, señor. Ya tiene {tipo} {nombre} en {carpeta}.",
        "Hecho, señor. He creado {tipo} {nombre} en {carpeta}.",
    ],
    "creacion.colision": [
        "Ya existe {nombre}, señor. Escriba otro nombre o cancelar.",
        "{nombre} ya existe, señor. Indíqueme otro nombre o escriba cancelar.",
        "Ya hay algo llamado {nombre}, señor. Escriba otro nombre o cancelar.",
    ],
    "creacion.fallo": [
        "No he podido crear {nombre}, señor.",
        "Lo siento, señor. No ha sido posible crear {nombre}.",
        "Disculpe, señor. Algo ha impedido crear {nombre}.",
    ],
    # Comandos
    "comandos.cd": [
        "Directorio cambiado a {carpeta}, señor.",
        "Ya está en {carpeta}, señor.",
        "He cambiado el directorio a {carpeta}, señor.",
        "Ahora trabajaremos desde {carpeta}, señor.",
        "Listo, señor. El directorio actual es {carpeta}.",
    ],
    "comandos.ls": [
        "He listado {carpeta}: tiene {carpetas} y {archivos}, señor.",
        "En {carpeta} hay {carpetas} y {archivos}, señor.",
        "La carpeta {carpeta} contiene {carpetas} y {archivos}, señor.",
    ],
    "comandos.pwd": [
        "Se encuentra en {ruta}, señor.",
        "El directorio actual es {ruta}, señor.",
        "Estamos trabajando en {ruta}, señor.",
        "Su ubicación actual es {ruta}, señor.",
    ],
    "comandos.arbol": [
        "He recorrido el árbol de {carpeta}: contiene {carpetas} y {archivos}, señor.",
        "El árbol de {carpeta} reúne {carpetas} y {archivos}, señor.",
        "Hay {carpetas} y {archivos} en el árbol de {carpeta}, señor.",
        "El recorrido de {carpeta} ha encontrado {carpetas} y {archivos}, señor.",
    ],
    "comandos.arbol_recortado": [
        "He recorrido el árbol de {carpeta}, señor, pero la vista está limitada:"
        " hay {carpetas} y {archivos}.",
        "El árbol de {carpeta} contiene {carpetas} y {archivos}, señor."
        " La salida se ha recortado.",
        "En {carpeta} hay {carpetas} y {archivos}, señor. Le muestro solo el fragmento permitido.",
        "El árbol de {carpeta} es demasiado grande, señor. Aquí tiene una parte con {carpetas}"
        " y {archivos}.",
    ],
    "comandos.ejecutando": [
        "Ejecutando {comando}, señor.",
        "Voy a ejecutar {comando}, señor.",
        "Pongo {comando} en marcha, señor.",
        "Ya estoy ejecutando {comando}, señor.",
    ],
    "comandos.ok": [
        "{comando} ha terminado correctamente, señor.",
        "Listo, señor. {comando} ha finalizado sin problemas.",
        "Todo correcto, señor. {comando} se ha completado.",
        "{comando} ya ha terminado, señor. No se han producido errores.",
    ],
    "comandos.fallo": [
        "No se ha podido completar {comando}, señor.",
        "{comando} ha terminado con un error, señor.",
        "Ha surgido un problema al ejecutar {comando}, señor.",
        "Lo siento, señor. {comando} no ha podido finalizar correctamente.",
    ],
    "comandos.no_permitido": [
        "Ese comando no lo tengo permitido, señor.",
        "No puedo ejecutar ese comando, señor.",
        "Por seguridad, no puedo ejecutar esa orden, señor.",
        "No tengo autorizado ese comando, señor.",
    ],
    "comandos.no_encontrado": [
        "No he localizado el programa {nombre}, señor.",
        "El programa {nombre} no está disponible, señor.",
        "No puedo encontrar {nombre} en el sistema, señor.",
    ],
    "comandos.tiempo": [
        "El comando ha tardado demasiado, señor. Lo he detenido.",
        "La operación no terminaba, señor, así que la he detenido.",
        "Ha pasado demasiado tiempo, señor. He parado el comando.",
        "El comando se ha demorado más de lo permitido, señor.",
    ],
    "comandos.ocupado": [
        "Ya hay un comando en ejecución, señor.",
        "Estoy ocupado con otro comando, señor.",
        "Un momento, señor. Todavía estoy ejecutando otra orden.",
        "Hay otra operación en curso, señor. Espere un momento.",
    ],
    "comandos.consola": [
        "Abriendo una terminal, señor.",
        "Ahora abro una terminal, señor.",
        "Terminal abriendose, señor.",
    ],
    # Apertura y Búsqueda
    "apertura.abriendo": [
        "Abriendo {nombre}, señor.",
        "Voy a abrir {nombre}, señor.",
        "Ya estoy iniciando {nombre}, señor.",
    ],
    "apertura.fallo": [
        "No he podido abrir {nombre}, señor.",
        "Ha habido un problema al abrir {nombre}, señor.",
        "No consigo iniciar {nombre}, señor.",
    ],
    "apertura.sin_edge": [
        "Necesito Microsoft Edge para hacer eso, señor.",
        "No puedo abrir esa página porque falta Microsoft Edge, señor.",
    ],
    "apertura.ventana_cerrada": [
        "Esa ventana ya no está abierta, señor.",
        "La ventana ya se ha cerrado, señor.",
        "No encuentro esa ventana abierta, señor.",
    ],
    "busqueda.ninguno": [
        "La búsqueda de {consulta} no ha dado resultados, señor.",
        "No aparece nada relacionado con {consulta}, señor.",
        "No he localizado ningún resultado para {consulta}, señor.",
    ],
    "busqueda.uno": [
        "He buscado {consulta} y he localizado {nombre} dentro de {carpeta}, señor.",
        "Buscando {consulta}, encontré {nombre}; está en {carpeta}, señor.",
        "La búsqueda de {consulta} ha dado un resultado, señor: {nombre}, en {carpeta}.",
    ],
    "busqueda.varios": [
        "La búsqueda de {consulta} ha dado {n} resultados, señor. El primero está en {carpeta}:"
        " {nombre}.",
        "He localizado {n} coincidencias con {consulta}, señor. La primera es {nombre},"
        " en {carpeta}.",
        "Tengo {n} resultados para {consulta}, señor. El primero es {nombre}, en {carpeta}.",
    ],
    "busqueda.limitada": [
        "La búsqueda se ha limitado a sus carpetas, señor.",
        "Solo he buscado dentro de sus carpetas, señor.",
        "La búsqueda está restringida a sus carpetas, señor.",
    ],
    "busqueda.instalar": [
        "Instale Everything para buscar en todo el disco, señor.",
    ],
    "busqueda.no_existe": [
        "Ese archivo ya no existe, señor.",
        "No encuentro ese archivo porque ya no existe, señor.",
        "Ese archivo ya no está disponible, señor.",
        "No he podido localizar el archivo; parece que fue eliminado, señor.",
    ],
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
