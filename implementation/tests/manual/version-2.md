# Lista manual de la versión 2.0

Lo que las pruebas automáticas no ven: usan plataforma, voz y reloj falsos. Se recorre en el
equipo de referencia antes de cerrar la versión. Marque cada punto y anote la fecha; si algo
falla, anote qué pasó y no lo marque hasta corregirlo.

Rutas que se usan abajo:

- Registro: `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.
- Base de datos: `%LOCALAPPDATA%\Jarvis\data\jarvis.db`.
- Configuración (`profiles.toml`, `layouts.toml`, `catalog.toml`, `commands.toml`):
  `%APPDATA%\Jarvis\config\`.

Los comandos se ejecutan desde `implementation\`. Use datos inventados: un perfil «Prueba» y la
contraseña `clave-prueba`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` y
      `.\.venv\Scripts\python.exe -m ruff check src scripts tests` en verde.
- [ ] En la pantalla dormida, Configuración → Perfiles: crear el perfil «Prueba», ponerle la
      contraseña `clave-prueba` y Guardar. Ni `profiles.toml` ni `jarvis.log` contienen
      `clave-prueba` (RNF-32).

## Perfiles protegidos

Especificación: [perfiles-protegidos.md](../../../software/Modulos/Accion/perfiles-protegidos.md).

Para ver los avisos guardados:

```powershell
.\.venv\Scripts\python.exe -c "import os, sqlite3; db = sqlite3.connect(os.path.expandvars(r'%LOCALAPPDATA%\Jarvis\data\jarvis.db')); print(*db.execute('SELECT profile_id, attempted_at, attempts, origin, acknowledged_at FROM intrusion_alerts'), sep='\n')"
```

- [ ] Elegir «Prueba» en el selector y escribir «Hey Jarvis»: aparece la caja de la contraseña
      en el centro y el orbe sigue dormido. Lo que se escribe no se ve, ni como puntos. Esc la
      cierra sin abrir sesión.
- [ ] Contraseña correcta y Enter: la caja se cierra y se abre la sesión.
- [ ] Una contraseña incorrecta: la caja se sacude, se pone roja y sigue abierta.
- [ ] Tres fallos seguidos: el tercero responde igual que los anteriores y la caja se cierra.
      No se abre sesión y nada en pantalla ni en la voz habla de un aviso ni de intentos
      restantes. La consulta muestra un aviso nuevo de «Prueba» con `attempts = 3` y
      `origin = inicio`.
- [ ] Tras los tres fallos, «Hey Jarvis» vuelve a mostrar la caja sin decir nada del aviso.
- [ ] Dos fallos, Esc y otro fallo: se guarda un aviso (cancelar no reinicia la cuenta).
- [ ] Entrar después con la contraseña correcta: tras la frase de apertura, lo primero es el
      aviso, antes que cualquier recordatorio. Se oye la alerta de seguridad y la tarjeta crítica
      queda por encima de todo, con la fecha y la hora del intento en hora local (en la base,
      `attempted_at` está en UTC).
- [ ] Cerrar la sesión sin pulsar «Entendido» y volver a entrar: el aviso sale otra vez. Pulsar
      «Entendido», cerrar y entrar: ya no sale, y `acknowledged_at` tiene valor.
- [ ] Configuración → Perfiles: «Prueba» está bloqueado. No se edita ni se duplica hasta dar su
      contraseña. Sigue desbloqueado hasta cerrar la ventana, y al reabrirla la pide otra vez.
- [ ] Los fallos en la configuración suman con los del inicio: dos fallos en la configuración y
      uno al abrir sesión guardan un aviso.
- [ ] Tras todo lo anterior, `jarvis.log` no contiene `clave-prueba`.

## Voz

Con el altavoz encendido y la voz real (Piper).

- [ ] Al aparecer la caja por primera vez se oye «Esta área está protegida por un nivel de
      seguridad superior. Introduzca la clave correcta para obtener acceso.», entera y sin que
      se despierte el orbe.
- [ ] Cada fallo dice «Clave incorrecta. Acceso denegado.».
- [ ] Al entrar con la contraseña se oye «Identidad confirmada. Ha accedido a un entorno de
      trabajo protegido con privilegios avanzados. Tiene acceso a protocolos y funciones
      confidenciales. ¿En qué vamos a trabajar, señor?» en lugar de «Sesión iniciada. Le
      escucho.». Un perfil sin contraseña sigue diciendo la frase normal.

## Recursos y Ruido

Especificación: [hud.md](../../../software/Modulos/Infraestructura/hud.md), sección 3.1.

- [ ] Recursos se ve al abrir sesión con la plantilla de fábrica. CPU y RAM cambian cada segundo
      y se parecen a lo que da el Administrador de tareas (pestaña Detalles) para el proceso del
      asistente. La RAM sale en MB, o en GB con un decimal, sobre la total del equipo.
- [ ] Ruido está oculto al abrir sesión. Al mostrarlo con su botón del selector aparece el icono
      del micrófono en la barra de tareas de Windows. Al ocultarlo, el icono desaparece
      (RNF-33).
- [ ] Estados del ruido: en silencio, «SILENCIO» o «CONCENTRACIÓN ALTA»; con conversación o
      música sostenida, «CONCENTRACIÓN MEDIA» o «CONCENTRACIÓN BAJA». Cada rótulo tiene su
      color.
- [ ] La media: una palmada o una frase de un par de segundos no cambia el valor. Un ruido
      sostenido lo cambia en unos 30 s.
- [ ] Con el micrófono desactivado en Sonido de Windows, el medidor muestra «SIN MICRÓFONO» y el
      asistente sigue funcionando.
- [ ] Un triple clic en un medidor lo pasa a la otra esquina inferior y el otro ocupa la que
      queda libre. Nunca comparten esquina.
- [ ] Fluidez: con `ui.quality = "high"`, `--ui-debug` y los dos medidores a la vista, el
      contador no baja de 30 fps y ronda 60 fps durante las animaciones y al atender órdenes
      (RNF-21). Anotar la cifra.
- [ ] Con los dos medidores a la vista, `python scripts\measure.py proceso --estado uso`
      cumple (RNF-05).

## Catálogo

Especificación: [catalogo.md](../../../software/Modulos/Accion/catalogo.md). Copie
`catalog.toml` y `commands.toml` antes de empezar, para comparar.

- [ ] «Añade al catálogo» solo abre la ventana y dice «Complete los datos en la ventana del
      catálogo, señor.». No cambia ningún archivo.
- [ ] Añadir una aplicación (p. ej. nombre «Bloc de prueba», ruta `notepad.exe`). Sin cerrar la
      sesión, «Abre bloc de prueba» la abre.
- [ ] Añadir una página (p. ej. «Página de prueba», `https://example.com`). En la misma sesión,
      «Abre página de prueba» la abre en Microsoft Edge.
- [ ] Añadir un comando que no esté en `commands.toml` (p. ej. `hostname`). En la misma sesión,
      «Ejecuta hostname» lo ejecuta.
- [ ] `catalog.toml` y `commands.toml` conservan todos sus comentarios y su formato, con las
      entradas nuevas añadidas.
- [ ] «Quita página de prueba del catálogo» pregunta «¿Elimino Página de prueba del catálogo,
      señor?». Con un no, la página sigue y se abre. Con un sí, desaparece del archivo y
      «Abre página de prueba» ya no la encuentra.
- [ ] Eliminar desde la ventana del catálogo pregunta lo mismo y no borra nada sin un sí.
- [ ] Al acabar, quitar las entradas de prueba.

## Plantillas

Especificación: [configurador.md](../../../software/Modulos/Infraestructura/configurador.md),
editor de plantillas. Copie `layouts.toml` y `profiles.toml` antes de empezar.

- [ ] Configuración → Plantillas → «+»: mover, redimensionar y cerrar ventanas, arrastrar el
      selector de ventanas y la caja de texto, y cambiar el ancho de la caja desde sus extremos.
      No baja de 300 px.
- [ ] Las dos barras: si al soltar una tapa la otra, vuelve a donde estaba.
- [ ] Aceptar, asignar la plantilla a «Prueba» y Guardar. Elegir «Prueba» en la pantalla
      dormida: la caja de texto ya está donde se dejó.
- [ ] Abrir sesión en «Prueba»: cada ventana, las dos barras y los medidores están en la
      posición y con el tamaño del editor. Mover ventanas y pulsar «Restablecer disposición»
      vuelve a la plantilla. La sesión siguiente empieza otra vez en la plantilla.
- [ ] Tras guardar, `layouts.toml` y `profiles.toml` conservan todos los comentarios de antes,
      incluido el bloque de ejemplo del principio de `layouts.toml`.

## Eliminar sesiones

Último cambio de la rama: una sesión sin actividades no se guarda (RN-69).

- [ ] «Hey Jarvis» y enseguida «Buenas noches Jarvis», sin ninguna orden: en la sesión
      siguiente, «Muestra el historial» no la lista. El registro dice «Sesión N vacía:
      eliminada al cerrar (voz)».
- [ ] Una sesión con al menos una orden sí queda en el historial al cerrarla.
- [ ] Abrir sesión sin órdenes y terminar el proceso desde el Administrador de tareas. Al
      arrancar, no está en el historial y el registro dice «vacía: eliminada al recuperarla».
      Si tenía órdenes, queda como interrumpida.
- [ ] «Elimina sesiones» con un intervalo (p. ej. «1-2») y un sí: las sesiones desaparecen, las
      demás quedan numeradas 1..N y conservan sus actividades. El número de la sesión actual
      que muestra la pantalla pasa al nuevo, y la sesión siguiente es la N+1.

## Cierre

Hecho cuando todas las casillas están marcadas, o los fallos encontrados están corregidos y su
casilla se ha vuelto a comprobar. Quite el perfil «Prueba» y su plantilla al terminar.
