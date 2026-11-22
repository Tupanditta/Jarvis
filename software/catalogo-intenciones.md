# Catálogo de intenciones y frases

Todo lo que el asistente entiende, escrito por el usuario, y todo lo que dice. Es la referencia para escribir los `intents()` de cada módulo y el catálogo de `speaker/phrases.py`. La mecánica de coincidencia está en [enrutador-intenciones.md](Modulos/Infraestructura/enrutador-intenciones.md).

Convenciones: los patrones se escriben con tildes y se normalizan al registrarlos; `{hueco}` es una entidad; cada línea de la columna «Patrones» es un patrón distinto. Añadir sinónimos es añadir patrones: no cambia nada más.

## 1. Frases de activación y control

| Frase | Mecanismo | Válida en | Efecto |
|---|---|---|---|
| «Hey Jarvis» · «Jarvis» | Frase de activación escrita: frase completa, similitud ≥ 80 ⚙ | Todos los estados | Dormido: abre sesión. Reposo: pasa a escucha. Escucha o espera: reinicia la cuenta de inactividad; si el asistente habla, lo interrumpe. |
| «Gracias Jarvis» | Frase completa, similitud ≥ 80 | Escucha, espera | Pasa a reposo. |
| «Buenas noches Jarvis» | Frase completa, similitud ≥ 80 (≥ 85 en reposo) | Escucha, espera, reposo | Cierra la sesión. |
| «Cancelar» · «Cancela» · «Olvídalo» · «Déjalo» | Frase completa, similitud ≥ 80 | Escucha, espera | Cancela la orden o el diálogo en curso. |

## 2. Intenciones del núcleo

Módulo interno `nucleo`. No pertenecen a ningún módulo de acción.

| Intención | Patrones | Respuesta |
|---|---|---|
| `nucleo.ayuda` | ayuda · qué puedes hacer · qué sabes hacer | Activa el panel de ayuda. «Estas son las órdenes disponibles.» |
| `nucleo.repetir` | repite · repítelo · puedes repetir | Repite la última respuesta. Si no hay: «No hay nada que repetir.» |
| `nucleo.presentate` | preséntate · quién eres | Se presenta, siempre en primera persona, con una sola frase de una sola variante y sin palabras en inglés: quién es (con `user.name` si está configurado), cómo funciona, en qué se basa (sin IA generativa, modelos de lenguaje ni internet), sus módulos (los títulos del registro de la ayuda) y que escribiendo «ayuda» se ven todas las órdenes. Sin panel. |
| `nucleo.mostrar_pantalla` | muestra la pantalla · pantalla completa | Pantalla de sesión al frente. Sin voz. |
| `nucleo.ocultar_pantalla` | oculta la pantalla · minimiza la pantalla | Minimiza la pantalla de sesión. Sin voz. |
| `nucleo.apartar_ventana` | aparta {ventana} · aparta la ventana de {ventana} | `ventana: CATALOG` (títulos de las ventanas flotantes, que da la interfaz). Aparta esa ventana a un borde si está abierta ([Interfaz](Interfaz/README.md), «Ventanas apartadas»). Sin voz. Si no hay ninguna con ese nombre: «No encuentro {nombre}.» |
| `nucleo.apartar_ventanas` | aparta módulos · aparta los módulos · aparta todas las ventanas | Aparta todas las ventanas abiertas. Sin voz. |
| `nucleo.desapartar_ventana` | desaparta {ventana} · desaparta la ventana de {ventana} | `ventana: CATALOG`, como en `nucleo.apartar_ventana`. Devuelve esa ventana a su sitio si está apartada. Sin voz. Si no hay ninguna con ese nombre: «No encuentro {nombre}.» |
| `nucleo.desapartar_ventanas` | desaparta módulos · desaparta los módulos · desaparta todas las ventanas | Devuelve a su sitio todas las ventanas apartadas. Sin voz. |

## 3. Intenciones de los módulos de acción

### Sesión

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `sesion.nombrar` | llama a la sesión {nombre} · nombra la sesión {nombre} · ponle a la sesión el nombre {nombre} | `nombre: TEXT` | «Llama a la sesión práctica de redes» |
| `sesion.marcar_importante` | marca la sesión como importante · sesión importante · esta sesión es importante | — | «Marca la sesión como importante» |
| `sesion.desmarcar_importante` | marca la sesión como no importante · la sesión no es importante · quita la importancia | — | «La sesión no es importante» |

### Historial

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `historial.mostrar` | muestra el historial · historial de sesiones · enséñame el historial | — | «Muestra el historial» |
| `historial.actividades` | actividades de la sesión {id} · muestra las actividades de la sesión {id} · qué hice en la sesión {id} · actividades de esta sesión · qué he hecho | `id: INTEGER` (opcional) | «Actividades de la sesión doce» |
| `historial.eliminar` | elimina sesiones · borra sesiones · elimina sesiones del historial · borra sesiones del historial · elimina la sesión {id} · borra la sesión {id} | `id: INTEGER` (opcional; sin él, pregunta cuáles con `SESSION_IDS`) | «Elimina la sesión doce» · «Elimina sesiones» |

### Comandos

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `comandos.cd` | ve a {ruta} · ve {ruta} · entra en {ruta} · cambia a la carpeta {ruta} · cd {ruta} | `ruta: DIR_PATH` | «Ve a proyectos barra jarvis» · «Ve atrás» |
| `comandos.ls` | lista · lista el directorio · qué hay aquí · ls | — | «Qué hay aquí» |
| `comandos.pwd` | dónde estoy · directorio actual · en qué carpeta estoy | — | «Dónde estoy» |
| `comandos.arbol` | árbol · muestra el árbol · árbol de {ruta} · muestra el árbol de {ruta} · mapa de {ruta} | `ruta: DIR_PATH` (opcional) | «Árbol de documentos» |
| `comandos.clear` | limpia · limpia la consola · clear | — | «Limpia la consola» |
| `comandos.ejecutar` | ejecuta {comando} · lanza el comando {comando} · corre {comando} | `comando: COMMAND_LINE` | «Ejecuta git status» · «Ejecuta gcc main punto c» |
| `comandos.abrir_consola` | abre una consola · abre la consola · abre una terminal · abre la terminal | — | «Abre una terminal» |

### Apertura de Aplicaciones y Páginas

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `apertura.abrir` | abre {objetivo} · abrir {objetivo} · lanza {objetivo} · inicia {objetivo} | `objetivo: CATALOG` (aplicaciones y páginas) | «Abre Visual Studio Code» · «Abre GitHub» |
| `apertura.abrir_carpeta` | abre la carpeta {ruta} · muestra la carpeta {ruta} · abre esta carpeta · abre la carpeta actual | `ruta: DIR_PATH` (opcional) | «Abre la carpeta descargas» |
| `apertura.traer_al_frente` | trae al frente {objetivo} · pon delante {objetivo} · vuelve a {objetivo} | `objetivo: CATALOG` (elementos abiertos) | «Trae al frente GitHub» |

### Búsqueda

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `busqueda.buscar` (ambos) | busca {consulta} · encuentra {consulta} | `consulta: TEXT` | «Busca presupuesto» |
| `busqueda.buscar` (archivos) | busca el archivo {consulta} · busca archivos {consulta} · encuentra el archivo {consulta} | `consulta: TEXT` | «Busca el archivo factura enero» |
| `busqueda.buscar` (carpetas) | busca la carpeta {consulta} · busca carpetas {consulta} · encuentra la carpeta {consulta} | `consulta: TEXT` | «Busca la carpeta prácticas» |
| `busqueda.abrir_resultado` | abre el resultado {n} · abre el resultado número {n} | `n: INTEGER` | «Abre el resultado dos» |
| `busqueda.abrir_ubicacion` | abre la carpeta del resultado {n} · dónde está el resultado {n} | `n: INTEGER` | «Abre la carpeta del resultado dos» |

### Creación

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `creacion.crear_archivo` | crea el archivo {nombre} · crea un archivo llamado {nombre} · crea el archivo {nombre} en {ruta} · crea un archivo llamado {nombre} en {ruta} | `nombre: NEW_NAME`, `ruta: DIR_PATH` | «Crea el archivo notas punto txt en documentos» |
| `creacion.crear_carpeta` | crea la carpeta {nombre} · crea una carpeta llamada {nombre} · crea la carpeta {nombre} en {ruta} · crea una carpeta llamada {nombre} en {ruta} | `nombre: NEW_NAME`, `ruta: DIR_PATH` | «Crea la carpeta apuntes» |
| `creacion.crear_arbol` | crea las carpetas {arbol} · crea las carpetas {arbol} en {ruta} · crea el árbol {arbol} | `arbol: NEW_PATH`, `ruta: DIR_PATH` | «Crea las carpetas backend barra src barra modelos» |
| `creacion.crear_estructura` | crea la estructura {estructura} llamada {nombre} · crea la estructura {estructura} llamada {nombre} en {ruta} | `estructura: CATALOG`, `nombre: NEW_NAME`, `ruta: DIR_PATH` | «Crea la estructura proyecto python llamada analizador» |

Si el nombre de `crear_carpeta` contiene «barra», se trata como `crear_arbol`.

### Recordatorio

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `recordatorio.crear` | recuérdame {texto} · recuérdame que {texto} · crea un recordatorio {texto} · crea un recordatorio para {texto} | `texto: TEXT` | «Recuérdame que tengo que llamar a Ana mañana a las nueve» |
| `recordatorio.mostrar` | recordatorios · muestra los recordatorios · qué recordatorios tengo | — | «Muestra los recordatorios» |
| `recordatorio.leer` | lee el recordatorio {n} · recordatorio {n} · lee el {n} | `n: INTEGER` | «Lee el recordatorio uno» |
| `recordatorio.dictar` | léeme los recordatorios · lee los recordatorios · díctame los recordatorios · dicta los recordatorios | — | «Léeme los recordatorios» |
| `recordatorio.confirmar` | confirmar recordatorios {n} · confirmar recordatorio {n} · confirmar recordatorios | `n: INTEGER` (opcional) | «Confirmar recordatorios dos» |
| `recordatorio.posponer` | posponer · pospón · más tarde · posponer {duracion} · pospón {duracion} · pospón el recordatorio {n} · pospón el recordatorio {n} durante {duracion} | `n: INTEGER`, `duracion: DURATION` (opcionales) | «Posponer media hora» |
| `recordatorio.posponer_limite` | pospón la fecha límite del recordatorio {n} hasta {fecha} · cambia la fecha límite del recordatorio {n} hasta {fecha} | `n: INTEGER`, `fecha: DATETIME` | «Pospón la fecha límite del recordatorio uno hasta el viernes a las diez» |
| `recordatorio.eliminar` | elimina el recordatorio {n} · borra el recordatorio {n} | `n: INTEGER` | «Elimina el recordatorio tres» |

### Protocolos

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `protocolos.ejecutar` | protocolo {protocolo} · ejecuta el protocolo {protocolo} · inicia el protocolo {protocolo} · activa el protocolo {protocolo} | `protocolo: CATALOG` | «Protocolo modo trabajo» |
| `protocolos.listar` | muestra los protocolos · qué protocolos hay | — | «Qué protocolos hay» |

`recordatorio.dictar` también la pone en la cola el propio módulo tras un aviso de recordatorios, con los avisados: entonces pregunta antes si los dicta ([recordatorio.md](Modulos/Accion/recordatorio.md)).

### Catálogo

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `catalogo.ver` | muestra el catálogo · ver el catálogo · ver catálogo · enseña el catálogo | — | «Muestra el catálogo» |
| `catalogo.añadir` | añade al catálogo · añadir al catálogo · nueva entrada del catálogo | — (los datos se escriben en la ventana) | «Añade al catálogo» |
| `catalogo.eliminar` | elimina {entrada} del catálogo · quita {entrada} del catálogo · borra {entrada} del catálogo | `entrada: CATALOG` (nombres y alias de aplicaciones, páginas y comandos del catálogo) | «Quita GitHub del catálogo» |

### Módulos del Acedor

Solo los usa el Acedor ([perfiles-protegidos.md](Modulos/Accion/perfiles-protegidos.md)). En cualquier otra sesión no salen en la ayuda y, si se escriben, la tarea queda en `error` con `permisos.denegado`.

| Intención | Patrones | Entidades | Ejemplo |
|---|---|---|---|
| `permisos.conceder` | da permiso de {modulo} a {perfil} · concede {modulo} a {perfil} · permite {modulo} a {perfil} · autoriza {modulo} a {perfil} | `modulo: CATALOG` (módulos y medidores restringibles), `perfil: CATALOG` (perfiles) | «Da permiso de comandos a Trabajo» |
| `permisos.restringir` | quita permiso de {modulo} a {perfil} · restringe {modulo} a {perfil} · prohibe {modulo} a {perfil} · quita {modulo} a {perfil} | Igual que `permisos.conceder` | «Quita permiso de comandos a Casa» |
| `permisos.ver` | muestra los permisos · ver permisos · permisos de los perfiles | — | «Muestra los permisos» |
| `credenciales.ver` | muestra las contraseñas · ver contraseñas · muestra las credenciales · contraseñas de los perfiles | — | «Muestra las contraseñas» |
| `perfiles.eliminar` | elimina el perfil {perfil} · borra el perfil {perfil} · quita el perfil {perfil} | `perfil: CATALOG` (perfiles eliminables) | «Elimina el perfil Casa» |
| `perfiles.ver` | muestra los perfiles · ver perfiles · lista los perfiles | — | «Muestra los perfiles» |

## 4. Respuestas a un diálogo

| Tipo esperado | Respuestas válidas |
|---|---|
| `BOOLEAN` | Sí: sí · vale · de acuerdo · confirmo · adelante · correcto · hazlo. No: no · negativo · mejor no · no lo hagas. |
| `NEW_FILENAME` | Cualquier nombre válido («informe dos punto txt»). |
| `DATETIME` | Una expresión de fecha y hora («mañana a las nueve»). |
| `REMINDER_ACTION` | otro aviso {fecha} · fecha límite {fecha} · no · nada más · listo. |
| `SESSION_IDS` | Identificadores de sesión separados por comas o un intervalo: «1, 3, 5» · «1-5». |

La contraseña de un perfil protegido no es una respuesta de diálogo: se escribe en su propia caja y no pasa por el enrutador ([perfiles-protegidos.md](Modulos/Accion/perfiles-protegidos.md)).

Las frases de control de la sección 1 valen en cualquier diálogo.

## 5. Catálogo de frases del asistente

Identificador y texto de `speaker/phrases.py`. `{…}` son parámetros; los formateadores dicen fechas, duraciones y plurales de forma natural.

### Ciclo de vida y generales

| Identificador | Texto |
|---|---|
| `ciclo.apertura` | Sesión iniciada. Le escucho. |
| `ciclo.apertura_protegida` | Identidad confirmada. Ha accedido a un entorno de trabajo protegido con privilegios avanzados. Tiene acceso a protocolos y funciones confidenciales. ¿En qué vamos a trabajar, señor? (Sustituye a `ciclo.apertura` al entrar con contraseña.) |
| `ciclo.escucha` | Le escucho. |
| `ciclo.reposo` | A su disposición. |
| `ciclo.cierre` | Buenas noches. Sesión cerrada. |
| `general.cancelado` | Cancelado. |
| `general.operacion_cancelada` | Operación cancelada. |
| `general.no_entendido` | No le he entendido. |
| `general.error` | Ha ocurrido un error. |
| `general.nada_que_repetir` | No hay nada que repetir. |
| `general.ayuda` | Estas son las órdenes disponibles. |
| `presentacion` | Soy Jarvis, el asistente personal de {nombre}: aplicación de escritorio local, sin IA generativa, modelos de lenguaje ni internet. Cuento con estos módulos: {modulos}. Si escribe ayuda, le enseño todas mis órdenes. |
| `presentacion.anonima` | Igual que `presentacion`, pero «su asistente personal», sin {nombre}. |
| `general.indice_invalido` | No hay ningún elemento {n}. |
| `general.no_disponible` | No está disponible en este sistema. |
| `config.error` | Hay un error en la configuración de {archivo}. Uso la anterior. |
| `entidad.numero` | No he entendido el número. |
| `entidad.duracion` | No he entendido la duración. |
| `entidad.fecha` | No he entendido la fecha. |
| `entidad.fecha_pasada` | Esa fecha ya ha pasado. |
| `entidad.nombre` | Ese nombre no es válido. |
| `entidad.no_encontrado` | No encuentro {nombre}. |
| `ruta.no_existe` | La carpeta {nombre} no existe. |
| `ruta.no_es_carpeta` | {nombre} no es una carpeta. |
| `ruta.gestor_fallo` | No he podido abrir el gestor de archivos. |

### Sesión e Historial

| Identificador | Texto |
|---|---|
| `sesion.nombrada` | Sesión renombrada a {nombre}. |
| `sesion.importante` | Sesión marcada como importante. |
| `sesion.no_importante` | Sesión marcada como no importante. |
| `sesion.desbordamiento` | Se incorpora una nueva sesión importante. La sesión {nombre} deja de serlo y se eliminará al cerrar. |
| `sesion.proponer_nombre` | ¿Quiere llamar a esta sesión {nombre}? |
| `historial.mostrado` | Hay {n} sesiones en el historial. |
| `historial.actividades` | La sesión {nombre} tiene {n} actividades. |
| `historial.no_existe` | No existe la sesión {id}. |
| `historial.es_actual` | No se puede eliminar la sesión actual. |
| `historial.confirmar_eliminar` | ¿Elimino la sesión {id}, {nombre}? |
| `historial.eliminada` | Sesión {id} eliminada. |
| `historial.cuales_eliminar` | ¿Qué sesiones elimino, señor? Puede decirme, por ejemplo, 1, 3, 5 o 1-5. |
| `historial.nada_que_eliminar` | No hay sesiones que eliminar, señor. Solo está la actual. |
| `historial.aviso_importantes` | Atención, señor: hay importancia marcada en {sesiones}. |
| `historial.confirmar_eliminar_varias` | ¿Elimino las sesiones {sesiones}, señor? |
| `historial.eliminadas` | Sesiones {sesiones} eliminadas, señor. |

### Comandos

| Identificador | Texto |
|---|---|
| `comandos.cd` | Directorio cambiado a {carpeta}. |
| `comandos.ls` | En {carpeta} hay {carpetas} y {archivos}. |
| `comandos.pwd` | Está en {ruta}. |
| `comandos.arbol` | El árbol de {carpeta} tiene {carpetas} y {archivos}. |
| `comandos.arbol_recortado` | El árbol de {carpeta} tiene {carpetas} y {archivos}. Se muestra solo una parte. |
| `comandos.limpio` | *(sin voz)* |
| `comandos.ejecutando` | Ejecutando {comando}. |
| `comandos.ok` | {comando} ha terminado correctamente. |
| `comandos.fallo` | {comando} ha fallado. |
| `comandos.no_permitido` | Ese comando no está permitido. |
| `comandos.no_encontrado` | No encuentro el programa {nombre}. |
| `comandos.tiempo` | El comando ha tardado demasiado. |
| `comandos.ocupado` | Ya hay un comando en ejecución. |
| `comandos.consola` | Abriendo una terminal. |

### Apertura y Búsqueda

| Identificador | Texto |
|---|---|
| `apertura.abriendo` | Abriendo {nombre}. |
| `apertura.fallo` | No he podido abrir {nombre}. |
| `apertura.sin_edge` | Microsoft Edge no está instalado. |
| `apertura.ventana_cerrada` | Esa ventana ya no está abierta. |
| `busqueda.ninguno` | No he encontrado nada para {consulta}. |
| `busqueda.uno` | He buscado {consulta} y he encontrado {nombre} en {carpeta}. |
| `busqueda.varios` | La búsqueda de {consulta} ha dado {n} resultados. El primero es {nombre}, en {carpeta}. |
| `busqueda.limitada` | Búsqueda limitada a sus carpetas. |
| `busqueda.instalar` | Instale Everything para buscar en todo el disco. |
| `busqueda.no_existe` | Ese archivo ya no existe. |
| `busqueda.ofrecer_abrir` | ¿Quiere que lo abra, señor? |

### Creación

| Identificador | Texto |
|---|---|
| `creacion.creado` | He creado {tipo} {nombre} en {carpeta}. ({tipo}: «el archivo», «la carpeta», «las carpetas», «la estructura».) |
| `creacion.colision` | Ya existe {nombre}. Escriba otro nombre o cancelar. |
| `creacion.fallo` | No he podido crear {nombre}. |

### Recordatorio

| Identificador | Texto |
|---|---|
| `recordatorio.cuando` | ¿Cuándo quiere que se lo recuerde? |
| `recordatorio.mas` | ¿Quiere añadir otro aviso o una fecha límite? |
| `recordatorio.creado` | Recordatorio creado para {fecha}. |
| `recordatorio.vacio` | No he entendido qué quiere que le recuerde. |
| `recordatorio.limite_anterior` | La fecha límite no puede ser anterior a un aviso. |
| `recordatorio.max_avisos` | No se pueden añadir más avisos. |
| `recordatorio.aviso_uno` | Tiene un recordatorio. |
| `recordatorio.aviso_varios` | Tiene {n} recordatorios. |
| `recordatorio.vencido` | El recordatorio {n} ha vencido. Su fecha límite era {fecha}. |
| `recordatorio.lista` | Tiene {n} recordatorios. |
| `recordatorio.ninguno` | No tiene recordatorios. |
| `recordatorio.lectura` | {texto} |
| `recordatorio.lectura_vencido` | {texto} Venció {fecha}. |
| `recordatorio.ofrecer_uno` | ¿Quiere que se lo lea, señor? |
| `recordatorio.ofrecer_varios` | ¿Quiere que se los dicte, señor? |
| `recordatorio.no_dictar` | Como quiera, señor. Lo tiene todo en el panel. |
| `recordatorio.dictado_unico` | Dice así: {texto}. |
| `recordatorio.dictado_primero` | El primero: {texto}. |
| `recordatorio.dictado_siguiente` | El siguiente: {texto}. |
| `recordatorio.dictado_ultimo` | Y por último: {texto}. |
| `recordatorio.dictado_vencido` | Venció {fecha}. |
| `recordatorio.activar` | Escriba confirmar recordatorios y el número. |
| `recordatorio.confirmado` | Recordatorio {n} confirmado. |
| `recordatorio.pospuesto` | Pospuesto. Le avisaré dentro de {duracion}. |
| `recordatorio.sin_aviso` | Ese recordatorio aún no ha avisado. |
| `recordatorio.limite_pospuesto` | Fecha límite cambiada a {fecha}. |
| `recordatorio.limite_vencido` | La fecha límite ya ha vencido y no se puede posponer. |
| `recordatorio.sin_limite` | Ese recordatorio no tiene fecha límite. |
| `recordatorio.confirmar_eliminar` | ¿Elimino el recordatorio {n}? |
| `recordatorio.eliminado` | Recordatorio {n} eliminado. |

### Protocolos

| Identificador | Texto |
|---|---|
| `protocolos.inicio` | Iniciando el protocolo {nombre}. |
| `protocolos.completado` | Protocolo {nombre} completado. |
| `protocolos.con_errores` | Protocolo {nombre} terminado con {n}. ({n} es el recuento: «1 error», «3 errores».) |
| `protocolos.lista` | Hay {n}. ({n}: «1 protocolo», «2 protocolos».) |
| `protocolos.ninguno` | No hay ningún protocolo definido. |

### Catálogo

| Identificador | Texto |
|---|---|
| `catalogo.mostrado` | Aquí tiene el catálogo, señor. |
| `catalogo.usar_ventana` | Complete los datos en la ventana del catálogo, señor. |
| `catalogo.anadido` | Hecho, señor. {nombre} ya está en el catálogo. |
| `catalogo.no_valido` | No puedo añadirlo, señor. Tiene el motivo en la ventana del catálogo. |
| `catalogo.confirmar` | ¿Elimino {nombre} del catálogo, señor? |
| `catalogo.eliminado` | {nombre} eliminado del catálogo, señor. |
| `catalogo.no_encontrado` | No encuentro eso en el catálogo, señor. |
| `catalogo.no_guardado` | No he podido guardar el catálogo, señor. |

### Perfiles protegidos y aviso de intrusión

Se dicen en la pantalla dormida sin despertar al asistente, salvo los avisos de intrusión, que se dicen tras la frase de apertura.

| Identificador | Texto |
|---|---|
| `seguridad.desafio` | Esta área está protegida por un nivel de seguridad superior. Introduzca la clave correcta para obtener acceso. |
| `seguridad.denegado` | Clave incorrecta. Acceso denegado. (La misma en todos los fallos, también en el tercero.) |
| `seguridad.intrusion` | Alerta de seguridad, señor. Alguien intentó acceder a este entorno sin autorización {cuando}. Introdujo una clave incorrecta {intentos} veces seguidas. |
| `seguridad.intrusiones` | Alerta de seguridad, señor. Ha habido {n} intentos de acceso no autorizado a este entorno desde su última visita. El último, {cuando}. Tiene los detalles en pantalla. |
| `seguridad.intrusion_acedor` | Alerta de seguridad, señor. Ha habido {n} intentos de acceso no autorizado a los perfiles desde su última visita. El último, {cuando}. Tiene los detalles en pantalla. |

### Permisos, Credenciales y Perfiles

| Identificador | Texto |
|---|---|
| `permisos.denegado` | No tiene autorización para usar {modulo} en este entorno, señor. (Cualquier módulo restringido al perfil.) |
| `permisos.solo_acedor` | Esa función solo está al alcance del Acedor, señor. |
| `permisos.no_encontrado` | No encuentro ese perfil o ese módulo, señor. |
| `permisos.concedido` | Hecho, señor. {perfil} ya puede usar {modulo}. |
| `permisos.restringido` | Hecho, señor. {perfil} ya no puede usar {modulo}. |
| `permisos.mostrados` | Aquí tiene los permisos de cada perfil, señor. |
| `credenciales.mostradas` | Aquí tiene las credenciales, señor. Están ocultas hasta que decida mostrarlas. |
| `credenciales.ninguna` | Ningún perfil tiene contraseña, señor. |
| `perfiles.mostrados` | Aquí tiene los perfiles, señor. |
| `perfiles.confirmar` | ¿Elimino el perfil {perfil}, señor? Se perderán sus recordatorios. |
| `perfiles.eliminado` | Perfil {perfil} eliminado, señor. |
| `perfiles.ultimo` | No puedo eliminar el último perfil, señor. |
| `perfiles.no_eliminado` | No he podido eliminar el perfil, señor. |

## 6. Juego de frases de prueba

Se implementa como prueba parametrizada del enrutador (RNF-11): texto escrito → intención y entidades esperadas. Debe incluir, como mínimo:

- **Un caso por cada patrón** de las secciones 2 y 3.
- **Variaciones de escritura** por intención: mayúsculas, signos («¿Dónde estoy?»), tildes ausentes, una errata en el texto fijo («avre la carpeta descargas», «recuerdame»), y alias («ce de proyectos»).
- **Entidades en otro idioma:** «abre Visual Studio Code», «ejecuta git status», «ve a Downloads».
- **Desambiguación por especificidad:** «abre la carpeta descargas» → `apertura.abrir_carpeta`; «abre una terminal» → `comandos.abrir_consola`; «abre la carpeta del resultado dos» → `busqueda.abrir_ubicacion`; «recuérdame que llame» → texto sin «que».
- **Frase de activación**, en todos los estados: «hey jarvis», «Hey, Jarvis.», «hey jarbis», «jarvis».
- **Frases de control:** «gracias jarvis», «gracias, Jarvis.», «grasias jarvis», «buenas noches jarvis».
- **Control negativo** (ninguna intención ni frase de control): «muchas gracias jarvis por todo», «buenas noches», «qué tiempo hace hoy», «jarvis abre el navegador», texto vacío, «abre» (hueco vacío).
- **Diálogo:** en `AWAITING_CONFIRMATION`, «abre GitHub» no se clasifica como intención: es una respuesta no válida.
- **Alcance por perfil:** las órdenes de un módulo no permitido se clasifican igual, sin buscar otra parecida de un módulo permitido; `run_task` las rechaza. Con `comandos` restringido, «ejecuta git status» → `comandos.ejecutar`, no `apertura.abrir` ni ninguna otra.
- **Desambiguación del catálogo:** «quita GitHub del catálogo» → `catalogo.eliminar`, no `permisos.restringir`.
