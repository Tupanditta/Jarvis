"""Catálogo único de frases del asistente (catalogo-intenciones.md, sección 5; RES-27).

No hay generación libre de texto: cada frase es un identificador y una lista de plantillas
(variantes). Cada vez que se dice una frase se usa la siguiente variante de su lista; al llegar
al final se vuelve a la primera. Para añadir una variante basta con añadir otra cadena a la
lista; todas las variantes de una frase deben usar los mismos parámetros. Las frases de cada
módulo de acción se añaden con su módulo. El asistente trata al usuario de usted y le llama
«señor», con un tono cercano, como quien le conoce, pero sin dar por sabidos datos suyos.
"""
import string
from collections.abc import Sequence

from jarvis_assistant.core.action_api import Phrase

PHRASES: dict[str, list[str]] = {
    "ciclo.apertura": [
        "Bienvenido de nuevo, señor. Ya lo tengo todo listo. ¿Qué tenemos hoy?",
        "Me alegra verle otra vez por aquí, señor. ¿Por dónde quiere que empecemos?",
        "Aquí estoy, señor, como siempre. Usted dirá qué hacemos hoy.",
    ],
    # Al entrar en un perfil protegido con su contraseña (sustituye a «ciclo.apertura»).
    "ciclo.apertura_protegida": [
        "Identidad confirmada. Ha accedido a un entorno de trabajo protegido con privilegios"
        " avanzados. Tiene acceso a protocolos y funciones confidenciales. ¿En qué vamos a"
        " trabajar, señor?",
    ],
    "ciclo.escucha": [
        "Dígame, señor. Soy todo oídos.",
        "Aquí me tiene, señor.",
        "Usted dirá, señor.",
        "De vuelta con usted, señor. ¿Qué necesita?",
    ],
    "ciclo.reposo": [
        "Muy bien, señor. Me quedo por aquí, por si me necesita.",
        "Entendido, señor. Estaré atento.",
        "Le dejo tranquilo, señor. Ya sabe dónde encontrarme.",
        "Como quiera, señor. Aquí sigo para lo que haga falta.",
        "Perfecto, señor. Llámeme cuando quiera.",
    ],
    "ciclo.cierre": [
        "Buenas noches, señor. Cierro la sesión. Descanse, que se lo ha ganado.",
        "Hasta la próxima, señor. Dejo la sesión cerrada. Que descanse.",
        "Por hoy es suficiente, señor. Cierro la sesión. Buenas noches.",
        "Sesión cerrada, señor. Da gusto trabajar con usted.",
        "Que descanse, señor. Aquí le espero cuando vuelva.",
    ],
    "general.cancelado": [
        "Sin problema, señor. Lo dejamos estar.",
        "Entendido, señor. Queda cancelado.",
        "Como prefiera, señor. No sigo con eso.",
        "Cancelado, señor. No he tocado nada.",
        "Tranquilo, señor. Lo dejamos aquí.",
    ],
    "general.operacion_cancelada": [
        "Operación cancelada, señor. Todo sigue como estaba.",
        "Entendido, señor. Paro la operación.",
        "Listo, señor. La he detenido.",
        "Ya está, señor. No sigo con ese proceso.",
        "Sin problema, señor. La operación queda cancelada.",
    ],
    "general.no_entendido": [
        "Perdone, señor, no le he seguido. ¿Me lo repite?",
        "Creo que no le he entendido bien, señor. ¿Lo intentamos otra vez?",
        "Esa se me ha escapado, señor. ¿Me lo dice de otra forma?",
        "Disculpe, señor, no lo he captado. ¿Puede repetirlo?",
        "Me he perdido, señor. ¿Me lo vuelve a decir?",
    ],
    "general.error": [
        "Vaya, señor. Algo ha fallado.",
        "Lo siento, señor. Esto no ha salido como esperaba.",
        "Me temo que ha habido un problema, señor. No he podido terminar.",
        "Disculpe, señor. No he conseguido hacerlo.",
        "Algo se ha torcido, señor. Si quiere, lo intentamos de nuevo.",
    ],
    "general.nada_que_repetir": [
        "Aún no le he dicho nada que pueda repetir, señor.",
        "Todavía no tengo nada que repetirle, señor.",
        "No tengo ninguna respuesta anterior a mano, señor.",
        "Me temo que no hay nada que repetir todavía, señor.",
        "No hay nada anterior que repetir, señor.",
    ],
    "general.ayuda": [
        "Claro, señor. Esto es lo que puedo hacer por usted.",
        "Por supuesto, señor. Le enseño las órdenes que conozco.",
        "Con mucho gusto, señor. Aquí tiene todo lo que sé hacer.",
        "Cómo no, señor. Estas son mis órdenes.",
        "Encantado, señor. Eche un vistazo a lo que puedo hacer.",
    ],
    # Presentación («preséntate»): una sola frase, con una sola variante, siempre en primera
    # persona y sin palabras en inglés, para que la voz la lea seguida y sin pausas entre
    # partes. `presentacion` cuando la configuración da el nombre del usuario; si no,
    # `presentacion.anonima`. Las dos dicen lo mismo salvo de quién es el asistente.
    "presentacion": [
        "Permítame presentarme, señor. Soy Jarvis, el asistente personal de {nombre}."
        " Soy una aplicación de escritorio y funciono por completo en su equipo."
        " Leo las órdenes que me escribe, las ejecuto y le respondo de viva voz y en pantalla."
        " No uso inteligencia artificial generativa, ni modelos de lenguaje, ni internet,"
        " así que ningún dato sale de su equipo."
        " Reconozco sus órdenes por patrones, y por eso a la misma orden respondo siempre igual."
        " Cuento con estos módulos: {modulos}."
        " Si escribe ayuda, le enseño todas mis órdenes.",
    ],
    "presentacion.anonima": [
        "Permítame presentarme, señor. Soy Jarvis, su asistente personal."
        " Soy una aplicación de escritorio y funciono por completo en su equipo."
        " Leo las órdenes que me escribe, las ejecuto y le respondo de viva voz y en pantalla."
        " No uso inteligencia artificial generativa, ni modelos de lenguaje, ni internet,"
        " así que ningún dato sale de su equipo."
        " Reconozco sus órdenes por patrones, y por eso a la misma orden respondo siempre igual."
        " Cuento con estos módulos: {modulos}."
        " Si escribe ayuda, le enseño todas mis órdenes.",
    ],
    "general.indice_invalido": [
        "Me temo que no hay ningún elemento {n}, señor.",
        "No encuentro el número {n}, señor. ¿Puede revisarlo?",
        "El {n} no corresponde a nada, señor.",
        "Ese número no me cuadra, señor. No hay ningún elemento {n}.",
        "No tengo un resultado {n}, señor. Eche un vistazo al índice.",
    ],
    "general.no_disponible": [
        "Lo siento, señor. Eso todavía no lo sé hacer.",
        "Me temo que esa función aún no está disponible, señor.",
        "Eso se me escapa por ahora, señor.",
        "Todavía no puedo ayudarle con eso, señor.",
        "Esa opción aún no la tengo, señor. Disculpe.",
    ],
    "config.error": [
        "Señor, algo no cuadra en {archivo}. Sigo con la última configuración válida.",
        "La configuración de {archivo} tiene un problema, señor. Me quedo con la anterior.",
        "No he podido cargar bien {archivo}, señor. De momento sigo como estaba.",
        "Hay un error en {archivo}, señor. Por si acaso, conservo la última versión válida.",
        "Señor, {archivo} no es válido. Sigo usando la configuración anterior.",
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
        "Hecho, señor. La sesión se llama ahora {nombre}.",
        "Desde ahora, esta sesión es {nombre}, señor.",
        "Le he puesto {nombre} a la sesión, señor.",
    ],
    "sesion.importante": [
        "Entendido, señor. Esta sesión queda marcada como importante.",
        "Hecho, señor. La marco como importante.",
        "Anotado, señor. Esta sesión es importante.",
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
        "Listo, señor. Ya tiene {tipo} {nombre} en {carpeta}.",
        "Hecho, señor. He creado {tipo} {nombre} en {carpeta}.",
        "Ya está, señor: {tipo} {nombre}, en {carpeta}.",
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
        "{comando} ha terminado bien, señor.",
        "Listo, señor. {comando} ha ido sin problemas.",
        "Todo en orden, señor. {comando} ha terminado.",
        "{comando} ya está, señor. Sin errores.",
    ],
    "comandos.fallo": [
        "Vaya, señor. {comando} no ha terminado bien.",
        "{comando} ha dado un error, señor.",
        "Me temo que {comando} ha fallado, señor.",
        "Lo siento, señor. {comando} no ha podido terminar.",
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
        "Deme un momento, señor. Aún estoy con otro comando.",
        "Estoy terminando otro comando, señor.",
        "Un segundo, señor. Todavía estoy con la orden anterior.",
        "Hay otra operación en marcha, señor. Enseguida estoy con usted.",
    ],
    "comandos.consola": [
        "Le abro una terminal, señor.",
        "Ahora mismo le abro una terminal, señor.",
        "Terminal en camino, señor.",
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
    "busqueda.ofrecer_abrir": [
        "¿Quiere que lo abra, señor?",
        "¿Se lo abro, señor?",
        "¿Desea que lo abra ahora, señor?",
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
    # --- Recordatorio ------------------------------------------------------------------------
    "recordatorio.cuando": [
        "¿Cuándo quiere que se lo recuerde, señor?",
        "¿Para cuándo se lo apunto, señor?",
    ],
    "recordatorio.mas": [
        "¿Le añado otro aviso o una fecha límite, señor?",
        "¿Quiere otro aviso, o le pongo una fecha límite, señor?",
    ],
    "recordatorio.creado": [
        "Apuntado, señor. Se lo recordaré {fecha}.",
        "Hecho, señor. No se me olvidará: se lo recuerdo {fecha}.",
    ],
    "recordatorio.vacio": [
        "Perdone, señor, ¿qué es lo que quiere que le recuerde?",
        "No me ha quedado claro qué debo recordarle, señor.",
    ],
    "recordatorio.limite_anterior": [
        "La fecha límite no puede ser anterior a un aviso, señor.",
        "Esa fecha límite queda antes de uno de los avisos, señor.",
    ],
    "recordatorio.max_avisos": [
        "No se pueden añadir más avisos, señor.",
        "Ese recordatorio ya tiene todos los avisos posibles, señor.",
    ],
    "recordatorio.aviso_uno": [
        "Señor, tengo un recordatorio para usted.",
        "Perdone que le interrumpa, señor. Tiene un recordatorio.",
    ],
    "recordatorio.aviso_varios": [
        "Señor, tengo {n} recordatorios para usted.",
        "Perdone que le interrumpa, señor. Tiene {n} recordatorios.",
    ],
    # Tras el aviso: se ofrece dictarlos. Con un sí, se dicen seguidos, cada uno con su
    # muletilla; al rotar las variantes, dos seguidos no empiezan igual.
    "recordatorio.ofrecer_uno": [
        "¿Quiere que se lo lea, señor?",
        "¿Se lo dicto, señor?",
        "¿Le digo qué es, señor?",
    ],
    "recordatorio.ofrecer_varios": [
        "¿Quiere que se los dicte, señor?",
        "¿Se los voy leyendo, señor?",
        "¿Le digo cuáles son, señor?",
    ],
    "recordatorio.no_dictar": [
        "Como quiera, señor. Lo tiene todo en el panel.",
        "De acuerdo, señor. Ahí lo tiene, en el panel, para cuando quiera.",
    ],
    "recordatorio.dictado_unico": [
        "Dice así: {texto}.",
        "Es este, señor: {texto}.",
        "Se lo leo: {texto}.",
    ],
    "recordatorio.dictado_primero": [
        "El primero: {texto}.",
        "Empiezo por este: {texto}.",
        "Para empezar: {texto}.",
        "En primer lugar: {texto}.",
    ],
    "recordatorio.dictado_siguiente": [
        "El siguiente: {texto}.",
        "También está este: {texto}.",
        "Luego tiene este otro: {texto}.",
        "Además: {texto}.",
        "Otro más: {texto}.",
    ],
    "recordatorio.dictado_ultimo": [
        "Y por último: {texto}.",
        "Y el último: {texto}.",
        "Para terminar: {texto}.",
        "Y ya para acabar: {texto}.",
    ],
    "recordatorio.dictado_vencido": [
        "Venció {fecha}.",
        "Su fecha límite era {fecha}.",
    ],
    "recordatorio.vencido": [
        "El recordatorio {n} ha vencido, señor. Su fecha límite era {fecha}.",
        "Señor, el recordatorio {n} ha vencido. La fecha límite era {fecha}.",
    ],
    "recordatorio.lista": [
        "Tiene {recordatorios}, señor.",
        "Aquí tiene sus recordatorios, señor: {recordatorios}.",
    ],
    "recordatorio.ninguno": [
        "No tiene ningún recordatorio, señor. Todo despejado.",
        "Nada pendiente, señor. No hay recordatorios.",
    ],
    "recordatorio.lectura": [
        "{texto}",
    ],
    "recordatorio.lectura_vencido": [
        "{texto} Venció {fecha}.",
    ],
    "recordatorio.activar": [
        "Escriba confirmar recordatorios y el número, señor.",
        "Para confirmarlo, escriba confirmar recordatorios y el número, señor.",
    ],
    "recordatorio.confirmado": [
        "Recordatorio {n} confirmado, señor.",
        "He confirmado el recordatorio {n}, señor.",
    ],
    "recordatorio.pospuesto": [
        "De acuerdo, señor. Se lo vuelvo a recordar dentro de {duracion}.",
        "Pospuesto, señor. Le aviso otra vez dentro de {duracion}.",
    ],
    "recordatorio.sin_aviso": [
        "Ese recordatorio aún no ha avisado, señor.",
        "Ese recordatorio todavía no le ha avisado, señor.",
    ],
    "recordatorio.limite_pospuesto": [
        "Fecha límite cambiada a {fecha}, señor.",
        "He movido la fecha límite a {fecha}, señor.",
    ],
    "recordatorio.limite_vencido": [
        "La fecha límite ya ha vencido y no se puede posponer, señor.",
        "Ese recordatorio ya ha vencido, señor. No se puede posponer.",
    ],
    "recordatorio.sin_limite": [
        "Ese recordatorio no tiene fecha límite, señor.",
    ],
    "recordatorio.confirmar_eliminar": [
        "¿Elimino el recordatorio {n}, señor?",
        "¿Quiere que elimine el recordatorio {n}, señor?",
    ],
    "recordatorio.eliminado": [
        "Recordatorio {n} eliminado, señor.",
        "He eliminado el recordatorio {n}, señor.",
    ],
    # {n} de `protocolos.con_errores` y `protocolos.lista` ya es un recuento: «1 error».
    "protocolos.inicio": [
        "Vamos allá, señor. Inicio el protocolo {nombre}.",
        "Muy bien, señor. Pongo en marcha el protocolo {nombre}.",
    ],
    "protocolos.completado": [
        "Protocolo {nombre} completado, señor. Todo en orden.",
        "Listo, señor. El protocolo {nombre} ha terminado sin errores.",
    ],
    "protocolos.con_errores": [
        "Protocolo {nombre} terminado con {n}, señor.",
        "El protocolo {nombre} ha terminado con {n}, señor.",
    ],
    "protocolos.lista": [
        "Hay {n}, señor.",
        "Tiene {n} disponibles, señor.",
    ],
    # --- Perfiles protegidos ---
    "seguridad.desafio": [
        "Esta área está protegida por un nivel de seguridad superior. Introduzca la clave"
        " correcta para obtener acceso.",
    ],
    "seguridad.denegado": [
        "Clave incorrecta. Acceso denegado.",
    ],
    "seguridad.intrusion": [
        "Alerta de seguridad, señor. Alguien intentó acceder a este entorno sin autorización"
        " {cuando}. Introdujo una clave incorrecta {intentos} veces seguidas.",
    ],
    "seguridad.intrusiones": [
        "Alerta de seguridad, señor. Ha habido {n} intentos de acceso no autorizado a este"
        " entorno desde su última visita. El último, {cuando}. Tiene los detalles en pantalla.",
    ],
    "protocolos.ninguno": [
        "No hay ningún protocolo definido, señor.",
        "Todavía no tiene protocolos, señor. Puede definirlos en la configuración.",
    ],
}

LIFECYCLE_IDS = ("ciclo.apertura", "ciclo.escucha", "ciclo.reposo", "ciclo.cierre")

# Frases sin parámetros que se sintetizan al arrancar, además de las del ciclo de vida.
PRELOADED_IDS = (
    *LIFECYCLE_IDS,
    "ciclo.apertura_protegida",
    "seguridad.desafio",
    "seguridad.denegado",
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


def enumeration(items: Sequence[str]) -> str:
    """Lista dicha en voz alta: «a», «a y b», «a, b y c»."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} y {items[-1]}"


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
