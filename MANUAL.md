# Manual de uso de Jarvis

Este manual explica cómo usar Jarvis en el día a día: cómo despertarlo, qué órdenes entiende, cómo responder a sus preguntas y cómo adaptarlo con los archivos de configuración.

Para instalarlo, consulte [implementation/README.md](implementation/README.md). Para adaptarlo a su equipo (aplicaciones, páginas, carpetas, protocolos), consulte [PERSONALIZAR.md](PERSONALIZAR.md). La lista completa de frases está en el [catálogo de intenciones](software/catalogo-intenciones.md).

## Índice

1. [Primeros pasos](#1-primeros-pasos)
2. [Estados del asistente](#2-estados-del-asistente)
3. [Cómo escribir órdenes](#3-cómo-escribir-órdenes)
4. [Órdenes generales](#4-órdenes-generales)
5. [Órdenes por módulo](#5-órdenes-por-módulo)
6. [Preguntas y respuestas](#6-preguntas-y-respuestas)
7. [La interfaz](#7-la-interfaz)
8. [Configuración](#8-configuración)
9. [Problemas frecuentes](#9-problemas-frecuentes)

## 1. Primeros pasos

1. Arranque el asistente con `.\scripts\start_jarvis.ps1` desde la carpeta `implementation\`, o déjelo en el inicio automático de Windows con `.\scripts\install_startup.ps1`.
2. Aparece un icono en la bandeja del sistema y la pantalla de sesión con una caja de texto. El asistente está **dormido**.
3. Escriba «Hey Jarvis» en la caja y pulse Enter. Jarvis responde «Sesión iniciada. Le escucho.»
4. Escriba una orden, por ejemplo «ayuda», y pulse Enter.
5. Cuando termine, escriba «Buenas noches Jarvis» para cerrar la sesión.

Jarvis responde siempre con voz y con un subtítulo en pantalla. No escucha el micrófono: todas las órdenes se escriben.

## 2. Estados del asistente

| Estado | Qué significa | Qué atiende |
|---|---|---|
| Dormido | No hay sesión abierta. Es el estado al arrancar y tras cerrar una sesión. | Solo «Hey Jarvis». Lo que se escribe se oculta con asteriscos. |
| Escuchando | Sesión abierta, atendiendo órdenes. | Todas las órdenes. |
| Esperando | Jarvis ha hecho una pregunta y espera la respuesta. | La respuesta y las frases de control. |
| Reposo | Sesión abierta, pero sin atender órdenes. | Solo «Hey Jarvis» y «Buenas noches Jarvis». |

### Frases de control

| Frase | Efecto |
|---|---|
| «Hey Jarvis» o «Jarvis» | Dormido: abre una sesión. Reposo: vuelve a escuchar. Mientras Jarvis habla: lo hace callar. |
| «Gracias Jarvis» | Pasa a reposo sin cerrar la sesión. Si había una pregunta pendiente, la cancela. |
| «Buenas noches Jarvis» | Cierra la sesión y vuelve a dormido. El proceso sigue en marcha. |
| «Cancelar», «Cancela», «Olvídalo» o «Déjalo» | Detiene la orden o la pregunta en curso. |

Tras 120 segundos sin escribir, Jarvis pasa a reposo solo. Al cerrar la sesión, se cancelan las preguntas pendientes, se detienen los protocolos y se terminan los programas en ejecución.

Para salir del todo, use «Salir» en el menú del icono de la bandeja. Así la sesión se cierra de forma ordenada.

## 3. Cómo escribir órdenes

- **Frases fijas con huecos.** Jarvis no entiende frases libres. Cada orden sigue un patrón, como «abre {objetivo}» o «crea la carpeta {nombre}».
- **Tolerancia a erratas.** Admite mayúsculas, signos de puntuación, tildes ausentes y erratas leves: «avre la carpeta descargas» funciona.
- **Números en letra o en cifra.** «Elimina la sesión doce» y «elimina la sesión 12» son lo mismo.
- **Rutas escritas como se dicen.** «barra» separa carpetas y «punto» separa la extensión: «proyectos barra web» y «notas punto txt».
- **Órdenes no reconocidas.** Si una frase no encaja con ninguna orden, Jarvis no responde. El subtítulo la marca como «no reconocido».
- **Una orden cada vez.** Puede seguir escribiendo mientras Jarvis trabaja. Se guarda como máximo una orden en espera; las demás se descartan.

## 4. Órdenes generales

| Orden | Efecto |
|---|---|
| «Ayuda» · «Qué puedes hacer» | Muestra el panel de ayuda con todas las órdenes y un ejemplo de cada una. |
| «Repite» · «Puedes repetir» | Repite la última respuesta. |
| «Preséntate» · «Quién eres» | Jarvis se presenta y enumera sus módulos. |
| «Muestra la pantalla» · «Pantalla completa» | Trae al frente la pantalla de sesión. |
| «Oculta la pantalla» · «Minimiza la pantalla» | Minimiza la pantalla de sesión. |
| «Aparta {ventana}» · «Aparta módulos» | Aparta a un borde la ventana de ese módulo, o todas las abiertas. |
| «Desaparta {ventana}» · «Desaparta módulos» | Devuelve a su sitio la ventana apartada, o todas. |

## 5. Órdenes por módulo

Los ejemplos usan nombres inventados. Sustitúyalos por los suyos.

### Sesión

Cada sesión se llama por defecto como su fecha de apertura (`AAAA-MM-DD`).

| Orden | Ejemplo |
|---|---|
| Nombrar la sesión | «Llama a la sesión práctica de redes» |
| Marcarla como importante | «Marca la sesión como importante» |
| Quitar la importancia | «La sesión no es importante» |

Puede haber como máximo 10 sesiones importantes. Si marca una undécima, Jarvis le avisa de cuál deja de ser importante. Esa sesión se elimina al cerrar la sesión actual.

### Historial

| Orden | Ejemplo |
|---|---|
| Ver las sesiones recientes | «Muestra el historial» |
| Ver lo que se hizo en una sesión | «Actividades de la sesión doce» · «Qué he hecho» |
| Eliminar una sesión | «Elimina la sesión doce» |

El historial muestra hasta 10 sesiones: primero las importantes. El número de cada sesión aparece en el panel. Jarvis pide confirmación antes de eliminar, y no permite eliminar la sesión actual.

### Comandos

Jarvis tiene un directorio de trabajo propio. Empieza en su carpeta personal en cada sesión y solo cambia con «ve a».

| Orden | Ejemplo |
|---|---|
| Cambiar de carpeta | «Ve a proyectos barra web» · «Ve atrás» · «cd documentos» |
| Listar la carpeta | «Qué hay aquí» · «ls» |
| Saber dónde está | «Dónde estoy» |
| Ver el árbol | «Árbol» · «Árbol de documentos» |
| Limpiar la consola | «Limpia la consola» |
| Ejecutar un programa | «Ejecuta git status» · «Ejecuta gcc main punto c» |
| Abrir una terminal | «Abre una terminal» |

- Solo se ejecutan los programas de la lista permitida (`commands.toml`). Cualquier otro produce «Ese comando no está permitido».
- Cada programa tiene 120 segundos como máximo. Solo puede haber uno en ejecución.
- El árbol muestra 3 niveles y 200 entradas como máximo.

### Apertura

| Orden | Ejemplo |
|---|---|
| Abrir una aplicación o una página | «Abre Visual Studio Code» · «Abre GitHub» |
| Abrir una carpeta en el Explorador | «Abre la carpeta descargas» · «Abre esta carpeta» |
| Traer al frente algo ya abierto | «Trae al frente GitHub» |

Jarvis busca el nombre primero en sus aplicaciones configuradas, después en sus páginas y por último en las aplicaciones del menú Inicio. Las páginas se abren siempre en Microsoft Edge y solo si están en `catalog.toml`.

### Búsqueda

| Orden | Ejemplo |
|---|---|
| Buscar archivos y carpetas | «Busca presupuesto» |
| Buscar solo archivos | «Busca el archivo factura enero» |
| Buscar solo carpetas | «Busca la carpeta prácticas» |
| Abrir un resultado | «Abre el resultado dos» |
| Abrir la carpeta de un resultado | «Abre la carpeta del resultado dos» |

Con [*Everything*](https://www.voidtools.com/) instalado, la búsqueda recorre todo el disco. Sin él, se limita a sus carpetas personales y se corta a los 5 segundos.

### Creación

| Orden | Ejemplo |
|---|---|
| Crear un archivo | «Crea el archivo notas punto txt en documentos» |
| Crear una carpeta | «Crea la carpeta apuntes» |
| Crear varias carpetas anidadas | «Crea las carpetas backend barra src barra modelos» |
| Crear una estructura predefinida | «Crea la estructura proyecto python llamada analizador» |

- Sin ubicación, se crea en el directorio de trabajo.
- Jarvis **nunca sobrescribe**. Si el nombre ya existe, pide otro. Tras 3 nombres repetidos seguidos, cancela.

### Recordatorios

| Orden | Ejemplo |
|---|---|
| Crear un recordatorio | «Recuérdame que tengo que llamar al dentista mañana a las nueve» |
| Ver los recordatorios | «Muestra los recordatorios» |
| Leer uno | «Lee el recordatorio uno» |
| Confirmarlo | «Confirmar recordatorios dos» |
| Posponer el aviso | «Posponer» · «Posponer media hora» |
| Posponer la fecha límite | «Pospón la fecha límite del recordatorio uno hasta el viernes a las diez» |
| Eliminarlo | «Elimina el recordatorio tres» |

Cómo funcionan:

1. Al crear un recordatorio sin fecha, Jarvis pregunta «¿Cuándo quiere que se lo recuerde?».
2. Después pregunta si quiere añadir otro aviso o una fecha límite. Responda «otro aviso el lunes a las diez», «fecha límite el viernes» o «nada más».
3. Un recordatorio admite hasta 5 avisos. Todas las fechas deben ser futuras.
4. Cuando llega un aviso, Jarvis dice «Tiene un recordatorio». Si estaba en reposo, se pone a escuchar.
5. Leer un recordatorio no lo confirma. Para confirmarlo, el panel de recordatorios debe estar activo: escriba «Confirmar recordatorios» y luego el número.
6. «Posponer» sin duración lo retrasa 10 minutos.
7. Si no responde a un último aviso en 5 minutos, el recordatorio se confirma solo.

Los avisos **solo suenan con una sesión abierta**. Los que llegan mientras Jarvis está dormido o apagado suenan al abrir la siguiente sesión.

### Protocolos

Un protocolo ejecuta con una sola orden una lista de tareas de varios módulos. Se definen en `protocols.toml`.

| Orden | Ejemplo |
|---|---|
| Ejecutar un protocolo | «Protocolo modo trabajo» |
| Ver los protocolos disponibles | «Qué protocolos hay» |

Las tareas se ejecutan en orden. Un error no detiene el protocolo, salvo que la tarea lo indique. Un protocolo puede proponer su nombre para la sesión; solo se aplica si usted lo confirma.

## 6. Preguntas y respuestas

Algunas órdenes necesitan un dato o una confirmación. Jarvis pregunta, pasa al estado **esperando** y muestra la pregunta con una barra de tiempo.

| Tipo de pregunta | Respuestas válidas |
|---|---|
| Sí o no | Sí: «sí», «vale», «de acuerdo», «adelante», «hazlo». No: «no», «mejor no», «no lo hagas». |
| Nombre nuevo | Cualquier nombre válido: «informe dos punto txt». |
| Fecha | «mañana a las nueve», «el viernes a las diez». Sin hora, se usan las 9:00. |
| Más avisos | «otro aviso {fecha}», «fecha límite {fecha}», «nada más», «listo». |

- No hace falta repetir «Hey Jarvis» para responder.
- Si la respuesta no es válida, Jarvis repite la pregunta una vez. A la segunda, cancela.
- Sin respuesta en 20 segundos, la operación se cancela. Jarvis nunca ejecuta nada por defecto.

## 7. La interfaz

### Pantalla de sesión

Ventana a pantalla completa con estas zonas:

- **Barra superior:** nombre de la sesión (con estrella si es importante), estado del asistente y hora.
- **Panel de actividad**, a la izquierda: cada tarea con su estado. El punto late mientras está pendiente; si hay error, se muestra el motivo.
- **Orbe**, en el centro: reacciona a la voz y al estado del asistente.
- **Panel activo**, a la derecha: comandos, búsqueda, recordatorios, historial, etc.
- **Subtítulos**, abajo: su última orden y la respuesta de Jarvis. Se desvanecen a los 6 segundos.
- **Caja de texto:** la única entrada de órdenes.

### HUD flotante

Ventana compacta, siempre encima, en una esquina de la pantalla. Muestra el estado, la última respuesta y su propia caja de texto. No roba el foco: haga clic en su caja para escribir. El botón de la cabecera la expande para ver el panel activo. Mientras Jarvis habla, aparece el botón de silencio.

### Ventanas flotantes

Los paneles son ventanas que se pueden mover y redimensionar. Para apartar una ventana a un borde:

- haga triple clic en su cabecera,
- use el botón del selector «Apartar ventanas», o
- escriba «Aparta {ventana}».

La ventana queda como una pestaña pequeña. Un clic en la pestaña la devuelve a su sitio. «Restablecer disposición», en el selector, devuelve todas las ventanas a su posición inicial.

### Bandeja del sistema

El color del icono indica el estado: gris (dormido), cian tenue (reposo), cian (activo) y ámbar (esperando). Su menú permite abrir la sesión, abrir las carpetas de configuración y de registro, y salir.

## 8. Configuración

Su configuración personal está en `%APPDATA%\Jarvis\config\`, fuera del repositorio. Se abre con «Abrir configuración» en el menú de la bandeja. Los cambios se aplican **al abrir la siguiente sesión**.

Allí se definen sus aplicaciones y páginas web, sus carpetas con nombre, los programas permitidos, las estructuras de carpetas, los protocolos y los ajustes generales.

Cómo hacerlo, con ejemplos e instrucciones para agentes: [PERSONALIZAR.md](PERSONALIZAR.md).

## 9. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| Jarvis no responde a una orden. | La frase no encaja con ningún patrón, o el asistente está en reposo o dormido. | Mire el estado en la barra superior. Escriba «Hey Jarvis» y luego «ayuda» para ver las frases válidas. |
| «No encuentro {nombre}». | El nombre no está en el catálogo o se parece poco. | Añada el elemento o un alias en `catalog.toml`. |
| «Ese comando no está permitido». | El programa no está en la lista permitida. | Añádalo a `commands.toml`. |
| «La carpeta {nombre} no existe». | La ruta es relativa al directorio de trabajo actual. | Escriba «dónde estoy» o use un lugar con nombre de `places.toml`. |
| Un recordatorio no ha sonado. | No había ninguna sesión abierta. | Abra una sesión: los avisos pendientes suenan al empezar. |
| La búsqueda dice «Búsqueda limitada a sus carpetas». | *Everything* no está instalado. | Instale *Everything* y su línea de órdenes `es.exe`. |
| Jarvis no habla. | Falta la voz o no hay altavoz. | Ejecute `scripts\fetch_models.py` y compruebe el altavoz. Los subtítulos siguen funcionando. |
| Un cambio de configuración no se aplica. | Los archivos se leen al abrir sesión. | Escriba «Buenas noches Jarvis» y luego «Hey Jarvis». |

El registro de diagnóstico está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`. Para ver más detalle, arranque con `.\scripts\start_jarvis.ps1 -Console` o con `--log-level DEBUG`.
