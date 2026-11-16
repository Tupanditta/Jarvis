# Manual de uso de Jarvis

Cómo usar Jarvis en el día a día. Para instalarlo, vea [INSTALAR.md](INSTALAR.md); para añadir sus aplicaciones, páginas o protocolos, [PERSONALIZAR.md](PERSONALIZAR.md).

## Lo esencial

1. Escriba **«Hey Jarvis»** en la caja de texto y pulse Enter. Jarvis responde «Sesión iniciada. Le escucho.»
2. Escriba una orden, por ejemplo **«ayuda»**, que muestra todas las órdenes con un ejemplo.
3. Si Jarvis le pregunta algo, responda en la caja. **«Cancelar»** detiene lo que esté haciendo.
4. **«Gracias Jarvis»** lo deja en reposo. **«Buenas noches Jarvis»** cierra la sesión.

Jarvis responde siempre con voz y con un subtítulo. No escucha el micrófono: todo se escribe.

## Índice

1. [Estados y frases de control](#1-estados-y-frases-de-control)
2. [Cómo escribir órdenes](#2-cómo-escribir-órdenes)
3. [Órdenes](#3-órdenes)
4. [Cuando Jarvis pregunta](#4-cuando-jarvis-pregunta)
5. [La interfaz](#5-la-interfaz)
6. [Problemas frecuentes](#6-problemas-frecuentes)

## 1. Estados y frases de control

| Estado | Qué significa | Qué atiende |
|---|---|---|
| Dormido | Sin sesión. Es el estado al arrancar. | Solo «Hey Jarvis». Lo que se escribe se oculta con asteriscos. |
| Escuchando | Sesión abierta. | Todas las órdenes. |
| Esperando | Jarvis ha preguntado algo. | La respuesta y las frases de control. |
| Reposo | Sesión abierta, en pausa. | Solo «Hey Jarvis» y «Buenas noches Jarvis». |

| Frase | Efecto |
|---|---|
| «Hey Jarvis» o «Jarvis» | Dormido: abre una sesión. Reposo: vuelve a escuchar. Mientras habla: lo hace callar. |
| «Gracias Jarvis» | Pasa a reposo. Cancela la pregunta pendiente, si la hay. |
| «Buenas noches Jarvis» | Cierra la sesión. El programa sigue abierto en la bandeja. |
| «Cancelar» · «Olvídalo» · «Déjalo» | Detiene la orden o la pregunta en curso. |

- Tras **120 segundos** sin escribir, Jarvis pasa a reposo.
- Cerrar la sesión cancela las preguntas pendientes, detiene los protocolos y termina los programas en ejecución.
- Para salir del todo, use **«Salir»** en el icono de la bandeja.

## 2. Cómo escribir órdenes

- **Siga el patrón.** Cada orden tiene una forma fija con huecos: «abre {objetivo}», «crea la carpeta {nombre}». «Ayuda» las muestra todas.
- **Se admiten erratas** leves, mayúsculas, signos y tildes ausentes: «avre la carpeta descargas» funciona.
- **Números** en letra o en cifra: «sesión doce» o «sesión 12».
- **Rutas como se dicen:** «barra» separa carpetas y «punto», la extensión: «proyectos barra web», «notas punto txt».
- **Una frase que no encaja se ignora**, sin voz. El subtítulo la marca como «no reconocido».
- **Una orden cada vez.** Puede seguir escribiendo mientras Jarvis trabaja: se guarda una orden en espera y las demás se descartan.

## 3. Órdenes

Los ejemplos usan nombres inventados. La lista completa de frases está en el [catálogo de intenciones](software/catalogo-intenciones.md).

### Generales

| Orden | Efecto |
|---|---|
| «Ayuda» · «Qué puedes hacer» | Muestra todas las órdenes. |
| «Repite» | Repite la última respuesta. |
| «Preséntate» · «Quién eres» | Jarvis se presenta. |
| «Muestra la pantalla» · «Oculta la pantalla» | Trae al frente o minimiza la pantalla de sesión. |
| «Aparta {ventana}» · «Aparta módulos» | Lleva al borde una ventana, o todas. «Desaparta…» las devuelve. |

### Apertura

| Orden | Ejemplo |
|---|---|
| Abrir una aplicación o página | «Abre Visual Studio Code» · «Abre GitHub» |
| Abrir una carpeta | «Abre la carpeta descargas» · «Abre esta carpeta» |
| Traer al frente algo abierto | «Trae al frente GitHub» |

Jarvis busca el nombre en sus aplicaciones, después en sus páginas y por último en el menú Inicio. Las páginas se abren en Microsoft Edge y solo si están en su catálogo ([PERSONALIZAR.md](PERSONALIZAR.md)).

### Búsqueda

| Orden | Ejemplo |
|---|---|
| Buscar archivos y carpetas | «Busca presupuesto» |
| Solo archivos o solo carpetas | «Busca el archivo factura enero» · «Busca la carpeta prácticas» |
| Abrir un resultado o su carpeta | «Abre el resultado dos» · «Abre la carpeta del resultado dos» |

Con [*Everything*](https://www.voidtools.com/) instalado, busca en todo el disco. Sin él, solo en sus carpetas personales y durante 5 segundos como máximo.

### Creación

| Orden | Ejemplo |
|---|---|
| Crear un archivo | «Crea el archivo notas punto txt en documentos» |
| Crear una carpeta | «Crea la carpeta apuntes» |
| Crear carpetas anidadas | «Crea las carpetas backend barra src barra modelos» |
| Crear una estructura | «Crea la estructura proyecto python llamada analizador» |

Sin ubicación, se crea en la carpeta actual. Jarvis **nunca sobrescribe**: si el nombre existe, pide otro.

### Comandos

Jarvis tiene una carpeta actual propia, que empieza en su carpeta personal en cada sesión.

| Orden | Ejemplo |
|---|---|
| Cambiar de carpeta | «Ve a proyectos barra web» · «Ve atrás» |
| Ver dónde está y qué hay | «Dónde estoy» · «Qué hay aquí» · «Árbol» |
| Ejecutar un programa | «Ejecuta git status» · «Ejecuta gcc main punto c» |
| Limpiar o abrir una terminal | «Limpia la consola» · «Abre una terminal» |

Solo se ejecutan los programas permitidos en su configuración, con un máximo de 120 segundos y de uno en uno.

### Recordatorios

| Orden | Ejemplo |
|---|---|
| Crear | «Recuérdame que tengo que llamar al dentista mañana a las nueve» |
| Ver o leer | «Muestra los recordatorios» · «Lee el recordatorio uno» |
| Confirmar | «Confirmar recordatorios dos» |
| Posponer el aviso | «Posponer» · «Posponer media hora» |
| Posponer la fecha límite | «Pospón la fecha límite del recordatorio uno hasta el viernes a las diez» |
| Eliminar | «Elimina el recordatorio tres» |

- Si no indica la fecha, Jarvis la pregunta. Después ofrece añadir otro aviso (hasta 5) o una fecha límite.
- **Los avisos solo suenan con una sesión abierta.** Los atrasados suenan al abrir la siguiente.
- Leer no confirma. Para confirmar, escriba «Confirmar recordatorios» y luego el número.
- «Posponer» sin duración retrasa el aviso 10 minutos.
- Si no responde al último aviso en 5 minutos, se confirma solo.

### Protocolos

| Orden | Ejemplo |
|---|---|
| Ejecutar | «Protocolo modo trabajo» |
| Ver los disponibles | «Qué protocolos hay» |

Un protocolo ejecuta varias tareas seguidas. Se definen en su configuración ([PERSONALIZAR.md](PERSONALIZAR.md#7-protocolos-protocolstoml)).

### Sesión e Historial

| Orden | Ejemplo |
|---|---|
| Nombrar la sesión | «Llama a la sesión práctica de redes» |
| Marcar o desmarcar como importante | «Marca la sesión como importante» · «La sesión no es importante» |
| Ver sesiones anteriores | «Muestra el historial» |
| Ver lo que hizo en una sesión | «Actividades de la sesión doce» · «Qué he hecho» |
| Eliminar una sesión | «Elimina la sesión doce» |

- Cada sesión se llama por defecto como su fecha (`AAAA-MM-DD`).
- El historial muestra hasta 10 sesiones, primero las importantes.
- Puede haber 10 sesiones importantes como máximo. Si marca una más, la más antigua deja de serlo y se elimina al cerrar la sesión actual. Jarvis avisa.
- Para eliminar una sesión, Jarvis pide confirmación. La sesión actual no se puede eliminar.

## 4. Cuando Jarvis pregunta

Algunas órdenes necesitan un dato o una confirmación. Jarvis pregunta y muestra una barra con el tiempo que queda.

| Pregunta | Respuestas válidas |
|---|---|
| Sí o no | «sí», «vale», «adelante», «hazlo» · «no», «mejor no» |
| Un nombre | «informe dos punto txt» |
| Una fecha | «mañana a las nueve», «el viernes a las diez» (sin hora: 9:00) |
| ¿Algo más? | «otro aviso {fecha}», «fecha límite {fecha}», «nada más» |

- No hace falta repetir «Hey Jarvis».
- Una respuesta no válida repite la pregunta una vez; la segunda cancela.
- Sin respuesta en **20 segundos**, se cancela. Jarvis nunca hace nada por defecto.

## 5. La interfaz

- **Pantalla de sesión:** a la izquierda, la actividad (cada tarea con su estado); en el centro, el orbe; a la derecha, el panel del módulo en uso; abajo, los subtítulos y la caja de texto.
- **HUD:** ventana pequeña siempre visible en una esquina, con el estado, la última respuesta y su propia caja de texto. Haga clic en la caja para escribir. Mientras Jarvis habla, muestra un botón para silenciarlo.
- **Ventanas flotantes:** los paneles se mueven y redimensionan. Un triple clic en la cabecera, o «aparta {ventana}», la lleva al borde como una pestaña; un clic en la pestaña la devuelve. «Restablecer disposición» lo coloca todo como al principio.
- **Icono de la bandeja:** gris (dormido), cian tenue (reposo), cian (activo), ámbar (esperando). Su menú abre la sesión, la configuración y el registro, y permite salir.

## 6. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| Jarvis no responde. | Mire el estado arriba a la derecha. Si está dormido o en reposo, escriba «Hey Jarvis». Si la frase no es del catálogo, escriba «ayuda». |
| «No encuentro {nombre}». | Añada la aplicación, la página o un alias en su configuración ([PERSONALIZAR.md](PERSONALIZAR.md)). |
| «Ese comando no está permitido». | Añada el programa a los permitidos ([PERSONALIZAR.md](PERSONALIZAR.md#5-programas-permitidos-commandstoml)). |
| «La carpeta {nombre} no existe». | La ruta parte de la carpeta actual. Escriba «dónde estoy» o use un lugar con nombre. |
| Un recordatorio no sonó. | No había sesión abierta. Abra una: los avisos pendientes suenan al empezar. |
| «Búsqueda limitada a sus carpetas». | Instale *Everything* para buscar en todo el disco. |
| Un cambio de configuración no se aplica. | Se aplica al abrir sesión: «Buenas noches Jarvis» y luego «Hey Jarvis». |
| Jarvis no habla o no arranca. | Vea [Problemas frecuentes de INSTALAR.md](INSTALAR.md#problemas-frecuentes). |
