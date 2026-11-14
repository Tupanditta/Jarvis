# Reglas de negocio

Políticas del dominio que el asistente debe respetar, independientes de la tecnología. Todas están confirmadas. Columna **Origen**: ver [README.md](README.md). Los valores marcados con ⚙ son configurables.

## 1. Tareas

| ID | Regla | Origen |
|---|---|---|
| RN-01 | **Estados de tarea.** Toda tarea mostrada en la interfaz o registrada en el historial tiene exactamente uno de tres estados: `pendiente`, `error` o `completado`. Una tarea nace `pendiente` y termina en `completado` o `error`. | Idea |
| RN-41 | **Ruta de carpeta inválida.** Cuando en `cd`, en la apertura de una carpeta o en el mapeo de entorno la ruta no existe o no es una carpeta, la tarea queda en `error` y el asistente dice un motivo breve que distingue «no existe» de «no es una carpeta». No hay ningún otro efecto. Si falla la apertura del propio gestor de archivos, se aplica la misma pauta. | Idea |
| RN-44 | **Un turno a la vez.** Las órdenes se atienden de una en una y en orden. Mientras se atiende una, la escucha sigue activa y como máximo una orden posterior queda en espera; las demás se descartan. Las frases de control (RN-52) se atienden de inmediato, sin esperar. | Refuerzo |
| RN-52 | **Frases de control.** «Gracias Jarvis», «Buenas noches Jarvis» y «cancelar» son frases de control: tienen efecto en escucha y en espera, aunque haya una orden en curso. «Cancelar» detiene la orden o el diálogo en curso; la tarea afectada queda en `error` con el motivo «cancelada». | Refuerzo |

## 2. Sesión

| ID | Regla | Origen |
|---|---|---|
| RN-02 | **Valores por defecto.** Una sesión nueva se llama como la fecha local de apertura (`AAAA-MM-DD`) y no es importante. Si ya existe una sesión no eliminada con ese nombre, se añade un sufijo: `AAAA-MM-DD (2)`, `(3)`… | Idea + Refuerzo |
| RN-43 | **Ciclo de vida.** El asistente está siempre en una de estas situaciones: | Idea |
| | • **Dormido:** sin sesión. Situación al arrancar el proceso y tras cerrar una sesión. Solo se atiende «Hey Jarvis», que abre una sesión nueva y pasa a escucha. | |
| | • **Reposo:** sesión abierta, sin escuchar órdenes. «Hey Jarvis» pasa a escucha; «Buenas noches Jarvis» cierra la sesión y pasa a dormido. Ninguna otra frase tiene efecto. | |
| | • **Escucha:** sesión abierta, escuchando órdenes. «Gracias Jarvis» pasa a reposo; 30 s ⚙ sin voz pasan a reposo; «Buenas noches Jarvis» cierra la sesión. | |
| | • **Espera:** sesión abierta, esperando la respuesta a una pregunta. Cuenta como escucha para las frases de control: «Gracias Jarvis» cancela la operación en pausa y pasa a reposo; «Buenas noches Jarvis» la cancela y cierra la sesión. | |
| | Solo «Hey Jarvis» activa la escucha; «Jarvis» suelto no tiene efecto. Cerrar la sesión nunca termina el proceso. | |
| RN-03 | **Nombre fijado por el usuario.** Si el usuario fijó el nombre mediante el módulo Sesión, ningún protocolo puede cambiarlo. | Idea |
| RN-04 | **Renombrado propuesto por un protocolo.** Si el nombre no lo fijó el usuario, un protocolo puede proponer cambiarlo por el nombre del protocolo; solo se aplica si el usuario lo confirma. | Idea |
| RN-05 | **Prevalencia de la importancia.** Si el usuario marcó la sesión como no importante y después un protocolo la marca como importante, queda importante. | Idea |
| RN-06 | **Un protocolo nunca degrada la importancia.** | Idea |
| RN-07 | **Límite de sesiones importantes.** Como máximo hay 10 sesiones importantes no eliminadas. | Idea |
| RN-08 | **Desbordamiento.** Si ya hay 10 sesiones importantes y la actual pasa a serlo: se notifica al usuario por voz y en la interfaz de que se incorpora una nueva sesión importante y cuál sale; la importante más antigua pasa a no importante y queda marcada (`pending_purge_on_close = 1`) para eliminarse al cerrar la sesión actual. El aviso es informativo: no pide confirmación. Si antes de cerrar el usuario marca la sesión actual como no importante, la sesión desplazada recupera su importancia y pierde la marca. | Idea + Refuerzo |
| RN-09 | **Eliminación de la sesión desbordada.** Al cerrar la sesión actual, las sesiones marcadas se eliminan según RN-12. Si el proceso termina sin cerrar la sesión, la eliminación se aplica al recuperar la sesión interrumpida (RN-47). | Idea + Refuerzo |
| RN-46 | **Cierre con operaciones en curso.** Al cerrar la sesión: el diálogo pendiente se cancela, el protocolo en curso se detiene, los binarios externos en ejecución se terminan y toda tarea `pendiente` pasa a `error` con el motivo «sesión cerrada». Los avisos no entregados se descartan y se recalculan al abrir la siguiente sesión (RN-22). | Refuerzo |
| RN-47 | **Sesión interrumpida.** Si el proceso termina con la sesión abierta (apagado, fallo), al arrancar de nuevo esa sesión se da por cerrada con el motivo «interrumpida», en el momento de su última actividad, y se aplican RN-09 y RN-46. Salir desde la bandeja del sistema cierra la sesión de forma ordenada antes de terminar. | Refuerzo |

## 3. Historial

| ID | Regla | Origen |
|---|---|---|
| RN-10 | **Sesiones visibles.** El historial muestra como máximo 10 sesiones no eliminadas, primero las importantes y, dentro de cada grupo, de la más reciente a la más antigua. Las que quedan fuera se conservan ocultas. | Idea |
| RN-11 | **Confirmación para eliminar una sesión.** Solo se elimina por su identificador si el usuario lo confirma tras verla en la interfaz. La sesión actual no se puede eliminar. | Idea + Refuerzo |
| RN-12 | **Borrado lógico de sesiones.** Eliminar una sesión es marcarla como eliminada; el registro se conserva y deja de mostrarse. Sus actividades dejan de ser consultables. | Idea |
| RN-53 | **Identificador de sesión.** Es un número entero correlativo, visible en el historial, que el usuario dice por voz. | Refuerzo |

## 4. Comandos

| ID | Regla | Origen |
|---|---|---|
| RN-14 | **Directorio de trabajo persistente.** El asistente conserva su directorio de trabajo entre órdenes; solo cambia con `cd`. Vuelve a la carpeta personal del usuario en cada sesión nueva y no se guarda en la base de datos. Pasar a reposo y volver no lo cambia. | Idea |
| RN-15 | **Destino válido de `cd`.** Solo cambia si la ruta existe y es un directorio; si no, RN-41. | Idea |
| RN-16 | **Resultado de un binario externo.** Código de retorno 0: `completado`; cualquier otro, tiempo agotado o imposibilidad de lanzarlo: `error`. | Idea |
| RN-40 | **Límite del árbol.** El árbol del mapeo de entorno tiene como máximo 3 niveles de profundidad y 200 entradas; la generación se detiene al alcanzar cualquiera de los dos. La carpeta raíz no cuenta como nivel ni como entrada; sus hijos directos son el nivel 1. Las entradas incluyen carpetas y archivos. | Idea |
| RN-42 | **Rutas relativas.** En `cd`, en el mapeo de entorno, en la apertura de carpetas y en la creación, una ruta relativa se resuelve respecto al directorio de trabajo; una absoluta se usa tal cual. | Idea |
| RN-45 | **Lista cerrada de binarios.** Solo se ejecutan los binarios declarados en la configuración. Pedir otro produce `error` y el aviso «Ese comando no está permitido». Nunca se usa un intérprete de órdenes. Cada ejecución tiene un tiempo máximo de 120 s ⚙. | Refuerzo |

## 5. Apertura de Aplicaciones y Páginas

| ID | Regla | Origen |
|---|---|---|
| RN-17 | **Páginas permitidas y navegador.** Solo se abren las URLs del catálogo, y siempre con Microsoft Edge. El catálogo es un archivo de configuración que el usuario edita a mano; no se amplía por voz. | Idea |
| RN-49 | **Resolución de «abre X».** El nombre dicho se busca, por este orden, en el catálogo de aplicaciones, en el catálogo de páginas y en las aplicaciones descubiertas del sistema. Gana la primera fuente con una coincidencia que supere el umbral. Si ninguna la supera, `error` y «No encuentro X». | Refuerzo |

## 6. Creación de Archivos/Carpetas

| ID | Regla | Origen |
|---|---|---|
| RN-18 | **Nunca sobrescribir.** Hay colisión cuando ya existe algo en la ruta destino (ubicación + nombre). | Idea |
| RN-19 | **Resolución de colisiones.** Ante una colisión, la creación se pausa y solo continúa con otro nombre indicado por el usuario, o termina si la cancela. Si el nombre nuevo también colisiona, se vuelve a preguntar; tras 3 ⚙ colisiones seguidas la creación se cancela. | Idea + Refuerzo |
| RN-54 | **Ubicación por defecto.** Si no se indica ubicación, se crea en el directorio de trabajo. | Refuerzo |

## 7. Recordatorios

| ID | Regla | Origen |
|---|---|---|
| RN-20 | **Texto del recordatorio.** Es la orden sin su prefijo disparador. Solo se sustituyen prefijos cerrados muy comunes: «tengo que» → «Tienes que», «debo» → «Debes», «tenemos que» → «Tenéis que». El resto se conserva intacto, con la primera letra en mayúscula. Sin reglas de conjugación. | Idea |
| RN-21 | **Fechas.** Un recordatorio tiene de 1 a 5 ⚙ fechas de aviso y, opcionalmente, una fecha límite. Todas deben ser futuras al crearlo y la fecha límite no puede ser anterior a ninguna fecha de aviso. | Idea + Refuerzo |
| RN-22 | **Notificaciones sin sesión abierta.** Sin sesión abierta (proceso apagado o dormido) no se dispara ninguna notificación. Las que llegan en ese tiempo se disparan al abrir la siguiente sesión. No se guardan aparte: se recalculan desde la base de datos. | Idea |
| RN-23 | **Contenido del aviso por voz.** El aviso de que hay recordatorios no lee fechas, salvo la fecha límite de un recordatorio vencido. | Idea |
| RN-24 | **Leer no confirma.** | Idea |
| RN-25 | **Confirmación explícita.** Un recordatorio solo se confirma con «Confirmar recordatorios [índice]» estando activo el panel de recordatorios; si no lo está, «Confirmar recordatorios» primero lo activa. «Activo» significa que es el panel destacado de la interfaz; no implica foco del sistema. | Idea |
| RN-26 | **Efecto de la confirmación.** Un recordatorio confirmado se elimina según RN-13. | Idea |
| RN-27 | **Posponer un aviso.** Lo retrasa 10 minutos ⚙, o el tiempo que indique el usuario, y no cambia la fecha límite. Sin índice, se aplica al último recordatorio notificado o leído. | Idea + Refuerzo |
| RN-28 | **Posponer la fecha límite.** Solo antes de que venza la original; después se rechaza. | Idea |
| RN-29 | **Autoconfirmación a los 300 segundos.** Cuando el usuario escucha un recordatorio en su última fecha de aviso o con la fecha límite vencida, empieza un plazo de 300 s; si no lo confirma ni lo pospone, se confirma y se elimina, aunque su fecha límite sea futura. «Escuchar» es que el asistente termine de leerlo o de avisar de su fecha límite. Si la sesión se cierra durante el plazo, el plazo se pierde y se aplica RN-31. | Idea |
| RN-30 | **Fin de un recordatorio sin fecha límite.** Se elimina cuando se completan todas sus fechas de aviso (tras el plazo de RN-29 del último aviso, o al confirmarlo). | Idea |
| RN-31 | **Estados.** `activo` (por defecto), `vencido` o `eliminado`. Pasa de `activo` a `vencido` en el momento en que se da el aviso por voz de su fecha límite, con sesión abierta o al abrir la siguiente. Un recordatorio `vencido` no vuelve a avisar por voz; si no se confirmó, sigue visible en el panel hasta que el usuario lo confirme. | Idea |
| RN-32 | **Avisos completados y fecha límite futura.** El recordatorio sigue `activo` y visible, y avisa de nuevo al llegar la fecha límite (RN-31), salvo que antes se haya autoconfirmado (RN-29). | Refuerzo |
| RN-13 | **Borrado lógico.** Eliminar un recordatorio es cambiar su estado a `eliminado`. Sus fechas de aviso no se modifican; se ignoran por el estado del recordatorio. | Idea |
| RN-39 | **Avisos y diálogo.** Un aviso (recordatorio o fin de un binario) nunca interrumpe un diálogo ni una locución: espera a que terminen. En reposo, un aviso de recordatorio pone al asistente en escucha para que el usuario pueda responder. | Refuerzo |
| RN-50 | **Índices.** El índice de un recordatorio o de un resultado es su posición en la lista numerada que muestra el panel en ese momento. Un índice fuera de rango produce `error` y «No hay ningún elemento N». | Refuerzo |

## 8. Protocolos

| ID | Regla | Origen |
|---|---|---|
| RN-33 | **Definición.** Un protocolo tiene un identificador único, un nombre hablado, una lista ordenada de tareas (módulo, acción y parámetros) y puede estar marcado como importante. | Idea |
| RN-34 | **Orden de ejecución.** Las tareas se ejecutan en el orden definido. Una tarea en `error` no detiene el protocolo, salvo que esa tarea lo declare (`stop_on_error`); en ese caso las restantes quedan en `error` con el motivo «protocolo detenido». | Idea + Refuerzo |
| RN-35 | **Tareas que necesitan diálogo.** Como las tareas son secuenciales, el diálogo de una tarea se formula cuando le llega el turno y el protocolo espera su respuesta. Si el diálogo se cancela o vence, la tarea queda en `error`. | Refuerzo |
| RN-36 | **Protocolo importante.** Ejecutarlo hace importante la sesión actual, sujeto a RN-07 y RN-08. | Idea |
| RN-55 | **Un protocolo a la vez.** No se inicia un protocolo mientras otro está en curso. | Refuerzo |

## 9. Diálogo y voz

| ID | Regla | Origen |
|---|---|---|
| RN-37 | **Respuesta a una operación en pausa.** Mientras hay una operación en pausa, la respuesta del usuario se dirige a ella y no se interpreta como orden nueva, salvo las frases de control (RN-52). Solo puede haber una operación en pausa. Si la respuesta no es del tipo esperado, el asistente repite la pregunta una vez; a la segunda respuesta no válida, cancela la operación. | Idea + Refuerzo |
| RN-38 | **Tiempo máximo de espera.** Toda operación en pausa espera como máximo 20 s ⚙ de silencio; al vencer se cancela y el asistente dice «Operación cancelada». Nunca se ejecuta una acción por defecto. La espera no requiere repetir «Hey Jarvis». | Idea + Refuerzo |
| RN-48 | **Interrupción de la locución.** Mientras el asistente habla no se capturan órdenes. Las frases del ciclo de vida no se pueden interrumpir. Cualquier otra locución se interrumpe diciendo «Hey Jarvis» o con el botón de silencio de la interfaz; el asistente calla y escucha. | Idea + Refuerzo |
| RN-51 | **Órdenes no reconocidas.** Una frase que no alcanza el umbral de ninguna intención se ignora en silencio: sin voz y sin animación. La interfaz la muestra en los subtítulos como no reconocida. Cuenta como voz para la cuenta de 30 s. | Idea + Refuerzo |
