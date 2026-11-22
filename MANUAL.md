# Manual de uso de Jarvis

Cómo usar Jarvis en el día a día. Para instalarlo, vea [INSTALAR.md](INSTALAR.md); para añadir sus aplicaciones, páginas o protocolos, [PERSONALIZAR.md](PERSONALIZAR.md).

## Lo esencial

1. Si tiene varios perfiles, elija el suyo bajo el orbe.
2. Escriba **«Hey Jarvis»** en la caja de texto y pulse Enter. Si el perfil tiene contraseña, escríbala. Jarvis responde «Sesión iniciada. Le escucho.»
3. Escriba una orden, por ejemplo **«ayuda»**, que muestra todas las órdenes con un ejemplo.
4. Si Jarvis le pregunta algo, responda en la caja. **«Cancelar»** detiene lo que esté haciendo.
5. **«Gracias Jarvis»** lo deja en reposo. **«Buenas noches Jarvis»** cierra la sesión.

Jarvis responde con voz y con un subtítulo. Si desactiva el sonido en la configuración, solo con el subtítulo. Todo se escribe: no hay entrada por voz.

## Índice

1. [Estados y frases de control](#1-estados-y-frases-de-control)
2. [Cómo escribir órdenes](#2-cómo-escribir-órdenes)
3. [Órdenes](#3-órdenes)
4. [Cuando Jarvis pregunta](#4-cuando-jarvis-pregunta)
5. [La interfaz](#5-la-interfaz)
6. [Perfiles y contraseñas](#6-perfiles-y-contraseñas)
7. [La ventana de configuración](#7-la-ventana-de-configuración)
8. [El Acedor](#8-el-acedor)
9. [Problemas frecuentes](#9-problemas-frecuentes)

## 1. Estados y frases de control

| Estado | Qué significa | Qué atiende |
|---|---|---|
| Dormido | Sin sesión. Es el estado al arrancar. Aquí se elige el perfil y se abre la configuración. | Solo «Hey Jarvis». Lo que se escribe se oculta con asteriscos. |
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

Con [*Everything*](https://www.voidtools.com/) instalado, busca en todo el disco. Sin él, solo en sus carpetas personales y durante 5 segundos como máximo. Si solo hay un resultado, Jarvis ofrece abrirlo.

### Creación

| Orden | Ejemplo |
|---|---|
| Crear un archivo | «Crea el archivo notas punto txt en documentos» |
| Crear una carpeta | «Crea la carpeta apuntes» |
| Crear carpetas anidadas | «Crea las carpetas backend barra src barra modelos» |
| Crear una estructura | «Crea la estructura proyecto python llamada analizador» |

Sin ubicación, se crea en la carpeta actual. Jarvis **nunca sobrescribe**: si el nombre existe, pide otro.

### Comandos

Cada ventana de Comandos es una consola con su propia carpeta actual, que empieza en su carpeta personal en cada sesión. Una orden va a la ventana de Comandos que está delante. Un protocolo con tareas de Comandos abre su propia ventana de Comandos, y otra nueva cada vez que cambia de carpeta.

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
| Oír todos seguidos | «Léeme los recordatorios» |
| Confirmar | «Confirmar recordatorios dos» |
| Posponer el aviso | «Posponer» · «Posponer media hora» |
| Posponer la fecha límite | «Pospón la fecha límite del recordatorio uno hasta el viernes a las diez» |
| Eliminar | «Elimina el recordatorio tres» |

- Si no indica la fecha, Jarvis la pregunta. Después ofrece añadir otro aviso (hasta 5) o una fecha límite.
- **Cada perfil tiene sus recordatorios.** Una sesión solo ve y crea los de su perfil.
- **Los avisos solo suenan con una sesión abierta.** Los atrasados suenan al abrir la siguiente. Tras un aviso, Jarvis ofrece dictar los recordatorios avisados.
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
| Eliminar varias | «Elimina sesiones» y, cuando pregunte, «1, 3, 5» o «1-5» |

- Cada sesión se llama por defecto como su fecha (`AAAA-MM-DD`).
- El historial muestra hasta 10 sesiones, primero las importantes.
- Una sesión sin actividades y no importante no se guarda en el historial.
- Puede haber 10 sesiones importantes como máximo. Si marca una más, la más antigua deja de serlo y se elimina al cerrar la sesión actual. Jarvis avisa.
- Para eliminar sesiones, Jarvis pide confirmación y avisa si alguna es importante. La sesión actual no se puede eliminar.
- **Eliminar no tiene vuelta atrás:** la sesión se borra con sus actividades. Las demás se renumeran de 1 en adelante, sin huecos.

### Catálogo

| Orden | Ejemplo |
|---|---|
| Ver aplicaciones, páginas y comandos | «Muestra el catálogo» |
| Añadir uno | «Añade al catálogo» (los datos se rellenan en la ventana) |
| Eliminar uno | «Quita GitHub del catálogo» |

- La ventana del catálogo también añade y elimina con el ratón, y filtra por tipo.
- Eliminar pide confirmación. Los cambios valen al momento, en la sesión en curso.
- Las aplicaciones que Jarvis encuentra en el menú Inicio no salen aquí.

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

- **Pantalla dormida:** el orbe; debajo, el selector de perfiles (solo con dos perfiles o más), el botón «Configuración» y la caja de texto.
- **Pantalla de sesión:** en el centro, el orbe; alrededor, las ventanas flotantes de los módulos; por defecto, el selector de ventanas arriba y la caja de texto abajo, con los subtítulos junto a ella. Qué ventanas se abren al empezar y dónde va cada cosa lo decide la plantilla de su perfil.
- **Selector de ventanas:** muestra u oculta cada ventana y cada medidor. «Restablecer disposición» lo vuelve a colocar todo como dice la plantilla.
- **Ventanas flotantes:** se mueven y redimensionan. Un triple clic en la cabecera, o «aparta {ventana}», la lleva al borde como una pestaña; un clic en la pestaña la devuelve.
- **Medidores:** en las esquinas inferiores. **Recursos** muestra la CPU y la RAM que usa Jarvis. **Ruido** muestra el ruido de fondo en decibelios aproximados (mediana de los últimos 30 s) y el nivel de concentración que permite: silencio, alta, media o baja. Un triple clic cambia un medidor de esquina. Solo miden mientras se ven; el de ruido no graba ni guarda audio y cierra el micrófono al ocultarlo.
- **HUD:** ventana pequeña siempre visible en una esquina, con el estado, la última respuesta y su propia caja de texto. Haga clic en la caja para escribir. Mientras Jarvis habla, muestra un botón para silenciarlo.
- **Icono de la bandeja:** gris (dormido), cian tenue (reposo), cian (activo), ámbar (esperando). Su menú abre la sesión, la pantalla, el HUD, la carpeta de configuración y el registro, y permite salir.

## 6. Perfiles y contraseñas

- Un **perfil** da a Jarvis su nombre de usuario («preséntate»), la plantilla de la pantalla de sesión y sus propios recordatorios. Se crean en la [ventana de configuración](#7-la-ventana-de-configuración).
- **Elegir perfil:** en la pantalla dormida, con el ratón o con ←/→ mientras la caja de texto está vacía. La última sesión recuerda el perfil con el que se abrió.
- **Perfil protegido:** lleva un candado en el selector. Tras «Hey Jarvis» aparece una caja que pide la contraseña sin mostrar lo que escribe. La contraseña se pone, cambia o quita en la configuración, y tiene al menos 4 caracteres.
- **Tres fallos seguidos** registran un aviso de intrusión. Todos los fallos reciben la misma respuesta. El dueño del perfil ve el aviso al abrir su siguiente sesión, con voz y con una tarjeta que sigue en pantalla hasta que la confirma.
- **No hay recuperación:** si olvida la contraseña de un perfil, solo el Acedor puede eliminarlo ([sección 8](#8-el-acedor)). También puede quitarlo a mano de `profiles.toml` ([PERSONALIZAR.md](PERSONALIZAR.md#9-perfiles-profilestoml)).

## 7. La ventana de configuración

Se abre con el botón **«Configuración»** de la pantalla dormida. Mientras está abierta no se puede iniciar sesión.

| Apartado | Qué permite |
|---|---|
| Plantillas | Crear, editar, duplicar y eliminar plantillas de la pantalla de sesión. El editor muestra la pantalla a tamaño real: coloque las ventanas, el selector y la caja de texto con el ratón. |
| Perfiles | Nombre del perfil, su nombre de usuario, su plantilla y su contraseña. Activar al Acedor. |
| Sonido | Activar o desactivar la voz y los sonidos. Sin sonido, los subtítulos siguen. |

- **Guardar** comprueba todo antes de escribir y se aplica al abrir la siguiente sesión. **Cancelar** pregunta si hay cambios sin guardar.
- Un perfil protegido pide su contraseña antes de editarlo.
- Desde aquí se añaden perfiles, pero no se eliminan: eso lo hace el Acedor.

## 8. El Acedor

El Acedor es un perfil administrador **opcional**, con autoridad sobre todos los demás. Se activa en la configuración, en la tarjeta del Acedor del apartado Perfiles, poniéndole una contraseña. Después, su contraseña solo se cambia dando la actual. Desde entonces aparece el último en el selector.

En su sesión, el Acedor solo usa estas órdenes, las de Sesión y las generales:

| Orden | Ejemplo |
|---|---|
| Ver y cambiar permisos | «Muestra los permisos» · «Da permiso de comandos a Trabajo» · «Quita permiso de comandos a Casa» |
| Ver contraseñas | «Muestra las contraseñas» |
| Ver o eliminar perfiles | «Muestra los perfiles» · «Elimina el perfil Casa» |

- **Permisos:** una tabla con una fila por perfil y una casilla por módulo o medidor. Un módulo restringido no sale en la ayuda, sus ventanas no se muestran y sus órdenes responden «No tiene autorización…». Se aplica al abrir cada sesión.
- **Credenciales:** las contraseñas de los perfiles protegidos, ocultas hasta pulsar el ojo. Nunca se dicen en voz alta. Una contraseña puesta antes de activar al Acedor solo se ve después de que su dueño vuelva a entrar con ella.
- **Perfiles:** eliminar un perfil pide confirmación y se lleva sus recordatorios. No se puede eliminar el último perfil ni al Acedor.
- **Avisos de intrusión:** el Acedor recibe los de todos los perfiles.
- **Si olvida su contraseña**, cierre Jarvis y ejecute desde `implementation\`: `.\.venv\Scripts\python.exe -m jarvis_assistant --reiniciar-acedor`. El Acedor queda desactivado y las contraseñas que guardaba dejan de poder verse. Los permisos y las contraseñas de los perfiles siguen valiendo.

## 9. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| Jarvis no responde. | Mire el estado arriba a la derecha. Si está dormido o en reposo, escriba «Hey Jarvis». Si la frase no es del catálogo, escriba «ayuda». |
| «No encuentro {nombre}». | Añada la aplicación, la página o un alias en su configuración ([PERSONALIZAR.md](PERSONALIZAR.md)). |
| «Ese comando no está permitido». | Añada el programa a los permitidos con «Añade al catálogo» o en su configuración ([PERSONALIZAR.md](PERSONALIZAR.md#5-programas-permitidos-commandstoml)). |
| «No tiene autorización para usar {módulo}». | El Acedor ha restringido ese módulo a su perfil. Pídale permiso. |
| No puedo escribir «Hey Jarvis». | La ventana de configuración está abierta. Ciérrela. |
| He olvidado una contraseña. | Vea la [sección 6](#6-perfiles-y-contraseñas) (perfil) o la [sección 8](#8-el-acedor) (Acedor). |
| El medidor de ruido dice que no hay micrófono. | Conecte un micrófono o actívelo en la configuración de privacidad de Windows. |
| «La carpeta {nombre} no existe». | La ruta parte de la carpeta actual. Escriba «dónde estoy» o use un lugar con nombre. |
| Un recordatorio no sonó. | No había sesión abierta. Abra una: los avisos pendientes suenan al empezar. |
| «Búsqueda limitada a sus carpetas». | Instale *Everything* para buscar en todo el disco. |
| Un cambio de configuración no se aplica. | Se aplica al abrir sesión: «Buenas noches Jarvis» y luego «Hey Jarvis». |
| Jarvis no habla. | Compruebe que el sonido está activado en la configuración (apartado Sonido). |
| Jarvis no arranca, o no habla con el sonido activado. | Vea [Problemas frecuentes de INSTALAR.md](INSTALAR.md#problemas-frecuentes). |
