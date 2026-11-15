# Lista manual de la fase 3. Órdenes sin diálogo

Se recorre en el equipo de referencia al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m hardware tests\hardware` en verde (abre y cierra
      el Bloc de notas; la búsqueda con *Everything* se salta si no está instalado).
- [ ] `--preview` recorre también los paneles de comandos (listado, árbol y salida), aperturas,
      búsqueda, historial y ayuda.
- [ ] Opcional: *Everything* instalado y en marcha, con `es.exe` en el `PATH`.

## Comandos (CU-02, CU-06)

- [ ] «Dónde estoy» dice y muestra la carpeta personal al empezar la sesión.
- [ ] «Ve a documentos» (lugar con nombre), «ve a {subcarpeta}», «ve a {a} barra {b}» y «ve
      atrás» cambian el directorio; la voz dice el nombre real de la carpeta.
- [ ] «Ve a {carpeta inexistente}» y «ve a {un archivo}»: tarea en error, con el motivo que
      distingue «no existe» de «no es una carpeta»; el directorio no cambia.
- [ ] Una ruta literal (`cd C:\Users`) y una unidad («ve a disco ce») funcionan.
- [ ] «Lista» / «qué hay aquí»: carpetas primero, orden alfabético; la voz dice el recuento.
- [ ] «Árbol» y «árbol de {ruta}»: sangría por nivel, máximo 3 niveles; en una carpeta grande,
      la línea «… (árbol recortado)» y «Se muestra solo una parte».
- [ ] «Limpia la consola» vacía el panel, sin voz.
- [ ] «Ejecuta git status» en un repositorio: «Ejecutando…», la salida aparece en el panel y,
      al terminar, el aviso «ha terminado correctamente».
- [ ] «Ejecuta python guion guion version» y «ejecuta gcc main punto c» pasan los argumentos
      bien escritos.
- [ ] Un comando que falla (`git estado`): tarea en error, salida de errores en rojo y aviso
      «ha fallado».
- [ ] «Ejecuta rm algo»: «Ese comando no está permitido»; no se ejecuta nada.
- [ ] Con un binario largo en ejecución: se atienden otras órdenes; un segundo «ejecuta…»
      responde «Ya hay un comando en ejecución»; «cancelar» lo termina.
- [ ] «Hey Jarvis» se atiende con un binario en ejecución, 10 de 10 intentos (RNF-07).
- [ ] «Abre una terminal» abre la terminal del sistema en el directorio de trabajo.

## Apertura (CU-01, CU-07)

- [ ] «Abre {aplicación del catálogo}», «abre GitHub» (en Microsoft Edge) y «abre {aplicación
      del menú Inicio}» abren lo pedido y añaden su tarjeta al panel.
- [ ] La aplicación abierta toma el foco; la pantalla de sesión queda detrás y aparece el HUD,
      que no toma el foco (RNF-13). 10 de 10 pruebas.
- [ ] A los pocos segundos se activa el botón «traer al frente» de la tarjeta; el clic y «trae
      al frente {nombre}» traen la ventana.
- [ ] Con la ventana cerrada, la orden responde «Esa ventana ya no está abierta» y el botón se
      desactiva.
- [ ] «Abre la carpeta descargas», «abre esta carpeta» y una subcarpeta relativa abren el
      explorador; una ruta inválida da su motivo.
- [ ] «Abre {algo que no existe}»: «No he podido encontrar…».

## Búsqueda (CU-08)

- [ ] «Busca {consulta}», «busca el archivo {consulta}» y «busca la carpeta {consulta}»
      muestran hasta 10 resultados numerados con su carpeta; la voz dice el total y el primero.
- [ ] Con *Everything*: el resultado llega en menos de 2 s (RNF-09).
- [ ] Sin *Everything*: el panel marca «limitada», la voz lo dice y, la primera vez, aconseja
      instalarlo; la búsqueda se corta a los 5 s.
- [ ] «Abre el resultado dos» abre el archivo con su aplicación; «abre la carpeta del resultado
      dos» abre su carpeta; un número fuera de rango da «No existe ningún elemento…».

## Historial y núcleo

- [ ] «Muestra el historial»: la sesión actual aparece marcada como «actual», con su número.
- [ ] «Qué he hecho» y «actividades de la sesión {n}» muestran las tareas con su estado.
- [ ] Todas las órdenes anteriores aparecen en el panel de actividad con su estado (RF-71).
- [ ] «Ayuda» muestra las órdenes por módulo, con un ejemplo de cada una.
- [ ] «Repite» repite la última respuesta; sin ninguna, lo dice.
- [ ] Escribir «Hey Jarvis» mientras el asistente habla lo calla; el botón de silencio, también.
- [ ] Editar `catalog.toml` y abrir una sesión nueva: el cambio ya vale. Con un error de sintaxis
      en el archivo, el asistente lo dice tras la frase de apertura y usa el anterior.

## Medidas

- [ ] Latencia (RNF-03): de Enter al inicio de la respuesta, mediana ≤ 0,5 s en 20 órdenes.
- [ ] Rutas escritas (RNF-31): 30 órdenes con lugares con nombre, subcarpetas, nombres con
      extensión y comandos con opciones; ≥ 95 % resueltas a la primera.
- [ ] Red desactivada: todo lo anterior funciona igual (RNF-02).
