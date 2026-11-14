# Requisitos funcionales

Servicios que ofrece el asistente, agrupados por módulo. Todos están confirmados. Las políticas del dominio están en [reglas-negocio.md](../reglas-negocio.md) (`RN-XX`) y las condiciones técnicas en [restricciones.md](../restricciones.md) (`RES-XX`). Las frases exactas de cada orden y de cada respuesta están en [catalogo-intenciones.md](../catalogo-intenciones.md).

Columnas: **P** prioridad (A alta, M media, B baja); **F** fase del [plan](../plan-implementacion.md) en la que se construye; **Origen** según [README.md](../README.md).

## 1. Sesión

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-01 | Abrir una sesión nueva, con nombre e importancia por defecto (RN-02), cuando el usuario dice «Hey Jarvis» en modo dormido. Arrancar el proceso no abre sesión. Cada apertura crea una sesión distinta. Si «Hey Jarvis» se dice mientras aún se muestra la animación de cierre de la sesión anterior, la sesión nueva se abre al instante y la pantalla no se cierra. | A | 1 | Idea |
| RF-02 | Cerrar la sesión cuando el usuario dice «Buenas noches Jarvis» con la sesión abierta: en escucha y en espera, como orden transcrita; en reposo, mediante la escucha restringida de [captura-audio.md](../Modulos/Infraestructura/captura-audio.md), que solo acepta esa frase. Al cerrar se aplica RN-46. Cerrar no termina el proceso. | A | 1 | Idea, modificada |
| RF-03 | Permitir que el usuario fije el nombre de la sesión actual. | M | 4 | Idea |
| RF-04 | Permitir que el usuario marque la sesión actual como importante. | M | 4 | Idea |
| RF-05 | Permitir que el usuario marque la sesión actual como no importante. | M | 4 | Idea |
| RF-06 | Avisar por voz y en la interfaz del desbordamiento de sesiones importantes, indicando la sesión que sale (RN-08). | M | 4 | Idea |
| RF-07 | Eliminar, al cerrar la sesión actual, las sesiones marcadas por desbordamiento (RN-09). | M | 4 | Idea |
| RF-93 | Recuperar al arrancar las sesiones que quedaron abiertas por una terminación inesperada (RN-47). | M | 4 | Refuerzo |

## 2. Historial

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-08 | Mostrar las sesiones visibles del historial (RN-10) con su identificador, nombre, fecha e importancia, y decir cuántas hay. | A | 3 | Idea |
| RF-09 | Mostrar las actividades de una sesión indicada por su identificador, o de la actual si no se indica: módulo, descripción, estado y momento. | A | 3 | Idea |
| RF-10 | Registrar en la sesión actual cada tarea de cualquier módulo de acción, con módulo, descripción, estado (RN-01) y momento. El registro lo hace el núcleo, no cada módulo. | A | 3 | Idea |
| RF-11 | Permitir que el usuario pida eliminar una sesión diciendo su identificador numérico (RN-53). | M | 4 | Idea |
| RF-12 | Informar por voz cuando el identificador no existe o corresponde a la sesión actual (RN-11). | M | 4 | Idea |
| RF-13 | Mostrar la sesión que se va a eliminar y pedir confirmación (RN-11). | M | 4 | Idea |
| RF-14 | Eliminar la sesión cuando el usuario lo confirma (RN-12). | M | 4 | Idea |

## 3. Comandos

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-15 | Cambiar el directorio de trabajo con `cd <ruta>` (RN-14, RN-15, RN-42). | A | 3 | Idea |
| RF-16 | Mostrar la tarea `cd` como `completado` al cambiar y decir el nombre de la carpeta resultante; si la ruta es inválida, aplicar RN-41. | M | 3 | Idea |
| RF-17 | Listar con `ls` el contenido del directorio de trabajo, mostrarlo estructurado en el panel de comandos (carpetas primero, orden alfabético) y decir el recuento. | A | 3 | Idea |
| RF-18 | Limpiar con `clear` el contenido del panel de comandos. | M | 3 | Idea |
| RF-19 | Ejecutar binarios externos de la lista permitida (RN-45) en el directorio de trabajo, de forma asíncrona, capturando la salida estándar y la de errores y mostrando sus últimas 200 líneas en el panel de comandos. | A | 3 | Idea |
| RF-20 | Asignar a la tarea del binario el estado según su código de retorno (RN-16) y comunicar por voz el resultado al terminar, como aviso si tarda (RN-39). | A | 3 | Idea |
| RF-21 | Abrir la terminal del sistema en el directorio de trabajo cuando el usuario pide abrir una consola. Es una ventana externa, distinta del panel de comandos. | B | 3 | Idea |
| RF-59 | Generar el árbol de directorios de la carpeta indicada o, si no se indica, del directorio de trabajo (RN-40, RN-42); ruta inválida según RN-41. | B | 3 | Idea |
| RF-73 | Mostrar el árbol en el panel de comandos con sangría por nivel; si se recortó por el límite, añadir una última línea «… (árbol recortado)». | B | 3 | Idea |
| RF-74 | Decir un resumen del árbol con el número de carpetas y de archivos mostrados, añadiendo «Se muestra solo una parte» si se recortó. | B | 3 | Idea |
| RF-98 | Decir y mostrar el directorio de trabajo actual cuando el usuario lo pregunta. | B | 3 | Refuerzo |

## 4. Apertura de Aplicaciones y Páginas

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-22 | Lanzar las aplicaciones del catálogo y las aplicaciones instaladas descubiertas en el sistema (RN-49). | A | 3 | Idea |
| RF-23 | Abrir en Microsoft Edge una URL del catálogo (RN-17). | A | 3 | Idea |
| RF-24 | Mostrar en el panel de aperturas el estado (RN-01) de cada apertura. | M | 3 | Idea |
| RF-25 | Traer al frente, con un clic en el botón de su tarjeta o por voz, la ventana de una aplicación, página o carpeta abierta por el asistente. Si la ventana ya no existe, el botón se desactiva. | M | 3 | Idea |
| RF-58 | Abrir una carpeta en el gestor de archivos nativo (RN-42); ruta inválida o fallo del gestor según RN-41. | B | 3 | Idea |

## 5. Búsqueda de Archivos/Carpetas

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-26 | Buscar en disco archivos, carpetas o ambos, según indique el usuario, con la herramienta indexada; si no está disponible, con la búsqueda limitada de [busqueda.md](../Modulos/Accion/busqueda.md). | A | 3 | Idea |
| RF-27 | Decir el número de resultados y el nombre y la carpeta del primero. | A | 3 | Idea |
| RF-28 | Mostrar en el panel de búsqueda hasta 10 ⚙ resultados numerados con nombre, tipo y ruta. | M | 3 | Idea |
| RF-90 | Abrir un resultado por su número con la aplicación predeterminada, o abrir su carpeta contenedora. | M | 3 | Refuerzo |

## 6. Creación de Archivos/Carpetas

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-29 | Crear un archivo vacío con el nombre indicado, en la ubicación indicada o en el directorio de trabajo (RN-18, RN-54). | A | 4 | Idea |
| RF-30 | Crear una carpeta con el nombre y la ubicación indicados (RN-18, RN-54). | A | 4 | Idea |
| RF-31 | Crear un árbol de directorios: una ruta anidada dictada con «barra» entre niveles. | M | 4 | Idea |
| RF-97 | Crear una estructura de carpetas predefinida en la configuración, con el nombre de carpeta raíz que indique el usuario. | B | 4 | Refuerzo |
| RF-32 | Avisar por voz de una colisión de nombre y pedir otro nombre o la cancelación (RN-19). | A | 4 | Idea |
| RF-33 | Completar la creación en pausa con el nombre nuevo (RN-19). | A | 4 | Idea |
| RF-34 | Cancelar la creación en pausa cuando el usuario lo pide. | M | 4 | Idea |

## 7. Recordatorio

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-35 | Crear un recordatorio con una orden de voz, guardando el texto según RN-20. | A | 5 | Idea |
| RF-36 | Asignar de una a cinco fechas de aviso (RN-21): la primera, dicha en la misma orden o pedida a continuación; las demás, en el diálogo de creación. | A | 5 | Idea |
| RF-37 | Asignar de forma opcional una fecha límite en el diálogo de creación (RN-21). | A | 5 | Idea |
| RF-38 | Programar cada fecha de aviso y la fecha límite. | A | 5 | Idea |
| RF-39 | Mostrar, al notificar, el panel numerado (1…n) con los recordatorios `activo` y `vencido`. | A | 5 | Idea |
| RF-40 | Avisar por voz de que hay recordatorios (RN-23). | A | 5 | Idea |
| RF-41 | Disparar al abrir sesión las notificaciones que llegaron sin sesión abierta (RN-22), después de la frase de apertura. | A | 5 | Idea |
| RF-42 | Leer por voz el recordatorio cuyo índice elija el usuario (RN-24). | A | 5 | Idea |
| RF-43 | Confirmar un recordatorio con «Confirmar recordatorios [índice]» (RN-25, RN-26). | A | 5 | Idea |
| RF-44 | Activar el panel de recordatorios cuando el usuario dice «Confirmar recordatorios» sin que esté activo (RN-25), sin tomar el foco. | M | 5 | Idea |
| RF-45 | Posponer el aviso de un recordatorio (RN-27). | A | 5 | Idea |
| RF-46 | Decir, tras posponer, cuánto falta para el siguiente aviso. | M | 5 | Idea |
| RF-47 | Callar la lectura en curso al posponer: el usuario la interrumpe con «Hey Jarvis» (RN-48) y dice «posponer». | M | 5 | Idea |
| RF-48 | Posponer la fecha límite de un recordatorio (RN-28). | M | 5 | Idea |
| RF-49 | Autoconfirmar los recordatorios no atendidos (RN-29). | A | 5 | Idea |
| RF-50 | Eliminar un recordatorio sin fecha límite al completar sus avisos (RN-30). | M | 5 | Idea |
| RF-51 | Fuera del flujo de notificación: mostrar los recordatorios a petición del usuario y eliminar uno por su índice, con confirmación. No se editan. | B | 5 | Refuerzo |

## 8. Protocolos

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-52 | Ejecutar un protocolo de la configuración diciendo su nombre (RN-33). | A | 6 | Idea |
| RF-53 | Abrir, al iniciarlo, el panel del protocolo con todas sus tareas en `pendiente`. | A | 6 | Idea |
| RF-54 | Pedir confirmación para renombrar la sesión con el nombre del protocolo cuando el usuario no ha fijado el nombre (RN-04). | M | 6 | Idea |
| RF-55 | Marcar la sesión como importante al ejecutar un protocolo importante (RN-36). | M | 6 | Idea |
| RF-56 | Ejecutar las tareas en orden mediante la interfaz común de los módulos (RN-34, RN-35). | A | 6 | Idea |
| RF-57 | Actualizar en el panel el estado de cada tarea en cuanto cambia, y decir un resumen al terminar. | M | 6 | Idea |
| RF-99 | Mostrar los protocolos disponibles a petición del usuario. | B | 6 | Refuerzo |

## 9. Interacción por voz y diálogo

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-60 | Escuchar el micrófono de forma continua y pasar a escucha al detectar «Hey Jarvis», en dormido (abre sesión) y en reposo. En escucha o en espera, «Hey Jarvis» se ignora en silencio y reinicia la cuenta de silencio correspondiente. Durante una frase del ciclo de vida no se detecta (RN-48). | A | 1 | Idea |
| RF-61 | Capturar cada orden mientras escucha: termina tras 1 s ⚙ sin voz o al llegar a 15 s ⚙. | A | 1 | Idea |
| RF-62 | Transcribir a texto en español cada orden y cada respuesta (RNF-15). | A | 1 | Idea |
| RF-63 | Identificar la intención y sus entidades. | A | 1 | Idea |
| RF-64 | Ejecutar la acción del módulo que corresponde a la intención. | A | 3 | Idea |
| RF-65 | Ignorar en silencio las frases no reconocidas (RN-51). | M | 1 | Idea |
| RF-66 | Mantener diálogos de varios turnos (RN-37). | A | 4 | Idea |
| RF-67 | Formular por voz la pregunta del diálogo y mostrarla en la interfaz con las respuestas admitidas. | A | 4 | Idea |
| RF-68 | Cancelar la operación en pausa al vencer el tiempo de espera (RN-38). | M | 4 | Idea |
| RF-69 | Informar por voz del resultado de cada acción. | A | 3 | Idea |
| RF-70 | Detener la locución en curso (RN-48). | M | 3 | Idea |
| RF-84 | Cancelar la orden o el diálogo en curso con «cancelar» (RN-52). | M | 4 | Refuerzo |
| RF-85 | Interrumpir al asistente mientras habla con «Hey Jarvis» (RN-48). | M | 3 | Refuerzo |
| RF-92 | Mostrar, cuando el usuario pide ayuda, las órdenes disponibles con un ejemplo de cada una, generadas del registro de intenciones. | B | 3 | Refuerzo |
| RF-94 | Repetir la última respuesta cuando el usuario lo pide. | B | 3 | Refuerzo |

## 10. Interfaz y persistencia

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-71 | Mostrar el estado (RN-01) de todas las tareas, de todos los módulos, en el panel de actividad, y el estado del asistente (dormido, reposo, escucha, espera, procesando, hablando). | A | 2 | Idea |
| RF-72 | Conservar las sesiones, sus actividades y los recordatorios entre ejecuciones. | A | 3 | Idea |
| RF-87 | Mostrar el HUD flotante, siempre encima, sin bordes y sin foco, mientras la sesión está abierta y la pantalla de sesión no es la ventana activa. | A | 2 | Idea |
| RF-88 | Mostrar u ocultar la pantalla de sesión por voz. | B | 2 | Refuerzo |
| RF-89 | Mostrar subtítulos: el texto de la última orden transcrita y el de la última respuesta. | M | 2 | Refuerzo |

## 11. Ciclo de vida del asistente

| ID | El sistema debe… | P | F | Origen |
|---|---|---|---|---|
| RF-75 | Arrancar en modo dormido, sin sesión, sin ventanas visibles y atendiendo solo «Hey Jarvis». En Windows el proceso se inicia al entrar el usuario, sin consola, mediante un acceso directo en su carpeta Inicio. | A | 1 | Idea |
| RF-76 | Pasar a reposo, con la sesión abierta, cuando el usuario dice «Gracias Jarvis» en escucha o en espera (RN-43). Se reconoce como orden transcrita. | A | 1 | Idea |
| RF-77 | Volver al modo dormido, sin terminar el proceso, al cerrar la sesión. Ninguna frase termina el proceso; termina desde la bandeja del sistema (RF-86) o al cerrar la sesión de Windows, cerrando antes la sesión de forma ordenada (RN-47). | A | 1 | Idea |
| RF-78 | Seguir escuchando entre órdenes, sin repetir «Hey Jarvis», hasta «Gracias Jarvis», «Buenas noches Jarvis» o 30 s ⚙ sin voz (pasa a reposo). La cuenta solo corre mientras se atiende al micrófono y no hay una orden en curso: empieza al terminar cada locución, se reinicia al acabar cada frase del usuario (reconocida o no) y con «Hey Jarvis». | A | 1 | Idea |
| RF-79 | Decir una frase fija en cada cambio del ciclo de vida: apertura, «Sesión iniciada. Le escucho.»; paso a reposo, «A su disposición.»; cierre, «Buenas noches. Sesión cerrada.»; vuelta a escucha, «Le escucho.». | M | 1 | Idea |
| RF-80 | Mostrar la animación de despertar al pasar a escucha desde dormido o desde reposo. Empieza a la vez que su frase (RNF-22) y dura 2 s (RNF-21), sin esperar a la frase. Si hay otra transición en curso, se funde con ella desde su estado actual, sin saltos. | M | 2 | Idea |
| RF-81 | Mostrar la animación de dormirse al pasar a reposo (la interfaz sigue visible) y al cerrar la sesión (la interfaz se oculta al terminar, salvo RF-01). Mismas reglas de inicio, duración y fundido que RF-80. | M | 2 | Idea |
| RF-82 | Mostrar la pantalla de sesión, a pantalla completa en el monitor principal, mientras la sesión está abierta. Al abrir la sesión pasa al frente y pide el foco. No queda siempre encima: el usuario puede pasar a otra ventana. En modo dormido no hay ninguna ventana visible. El cursor se oculta sobre ella tras 2 s sin moverse. | M | 2 | Idea |
| RF-83 | Hacer que el núcleo del orbe reaccione al nivel de la voz: al del micrófono mientras escucha y al de la voz del asistente mientras habla, en todas sus frases. En reposo y sin locución, queda quieto. | M | 2 | Idea |
| RF-86 | Mostrar un icono en la bandeja del sistema con el estado del asistente y un menú: abrir sesión, mostrar la pantalla de sesión, abrir la carpeta de configuración, abrir el registro de diagnóstico y salir. | M | 1 | Refuerzo |
| RF-95 | Reintentar cada 5 s ⚙ la apertura del micrófono cuando no está disponible e indicarlo en el icono de la bandeja. | M | 1 | Refuerzo |
| RF-96 | Releer la configuración al abrir cada sesión; si un archivo es inválido, conservar la configuración anterior y avisar por voz. | B | 3 | Refuerzo |

## Requisitos retirados

Ninguno. Todos los requisitos RF-01 a RF-83 de la versión anterior se conservan con su número.
