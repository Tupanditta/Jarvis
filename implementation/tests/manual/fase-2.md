# Lista manual de la fase 2. Interfaz completa

Se recorre en el equipo de referencia al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `.\.venv\Scripts\python.exe -m jarvis_assistant --preview` abre la interfaz sin voz ni
      modelos y recorre todos los estados en bucle; cerrar la pantalla termina la vista previa.
- [ ] `--preview --ui-debug` muestra el contador de frames arriba a la izquierda.

## Lista de comprobación visual (Interfaz, sección 11)

Con `--preview` y en uso real.

- [ ] El orbe se parece a las tres imágenes de referencia: esfera luminosa, anillos concéntricos
      con datos, cian sobre negro.
- [ ] Donde se cruzan dos capas del orbe, la zona es más clara.
- [ ] Despertar: punto de luz, destello, expansión de anillos en sentidos opuestos,
      estabilización. Dura 2 s.
- [ ] Dormirse: frenado, colapso, viraje a marino; en el cierre, chispa y partículas; en reposo,
      orbe tenue y lento.
- [ ] Interrumpir una animación con la contraria no produce ningún salto (escribir «Hey Jarvis»
      durante la animación de cierre).
- [ ] Al hablar el asistente, el núcleo y el espectro siguen su voz; en escucha y en reposo,
      quietos.
- [ ] Los cinco aspectos (escuchando, hablando, procesando, esperando, reposo) se distinguen sin
      leer el texto.
- [ ] Ningún color fuera de la tabla de tokens. Los colores de estado solo indican estado.
- [ ] Todo el texto se lee a un metro de la pantalla; ningún texto se corta sin elipsis.
- [ ] Los paneles se ven igual en la pantalla de sesión y en el HUD.
- [ ] El HUD no tapa más del 60 % del alto, no parpadea al actualizarse y no toma el foco salvo
      con un clic en su caja de texto.
- [ ] La caja de texto se ve en dormido, en reposo y en escucha, con la ayuda de cada estado, y
      recibe el teclado al abrir la pantalla.
- [ ] A 1366 × 768 nada se solapa.
- [ ] Con `ui.reduce_motion = true`, no hay giros ni colapsos, solo fundidos.
- [ ] `ui.quality = "medium"` y `"low"`: menos partículas; en `low`, sin partículas ni
      resplandor y anillos sin texto.

## Ventanas (hud.md, sección 2)

- [ ] Al arrancar: pantalla completa en el monitor principal, orbe apagado (un punto marino),
      sin paneles ni subtítulos, caja con el foco. El HUD no se ve.
- [ ] «Hey Jarvis»: la pantalla pasa al frente con el despertar; los paneles aparecen con un
      fundido.
- [ ] Pasar a otra ventana (Alt+Tab) con la sesión abierta: aparece el HUD en la esquina de
      `ui.hud_corner`; la pantalla queda detrás sin cambios. Volver a la pantalla oculta el HUD.
- [ ] Minimizar la pantalla: aparece el HUD.
- [ ] «Oculta la pantalla» la minimiza y muestra el HUD, sin voz. «Muestra la pantalla» la trae
      al frente con el foco en la caja y oculta el HUD, sin voz.
- [ ] «Mostrar pantalla» en la bandeja hace lo mismo.
- [ ] Cerrar la pantalla con ✕: se oculta, el proceso sigue en la bandeja y, con sesión, se ve el
      HUD.
- [ ] «Gracias Jarvis» con el HUD a la vista: el mini orbe se atenúa y el HUD se contrae; la
      pantalla sigue visible detrás.
- [ ] «Buenas noches Jarvis» con el HUD a la vista: el HUD se desvanece y se oculta a los 2 s; la
      pantalla queda en su aspecto de dormido.
- [ ] El cursor se oculta sobre la pantalla tras 2 s sin moverlo y reaparece al moverlo.
- [ ] «Salir» en la bandeja termina el proceso aunque la pantalla esté visible.

## Foco (RNF-13), 10 repeticiones de cada

- [ ] Al aparecer el HUD, la ventana activa sigue siendo la que el usuario estaba usando.
- [ ] Al actualizarse el HUD (subtítulos, estado, expandir), la ventana activa no cambia.
- [ ] Clic en los botones de expandir y de silencio del HUD: la ventana activa no cambia.
- [ ] Clic en la caja de texto del HUD: recibe el teclado; Enter envía y el foco se queda en la
      caja. Al volver a otra ventana, el HUD deja de aceptar el foco.

## Fluidez y sincronía

- [ ] Con `--ui-debug`, durante las animaciones de despertar y dormirse: ____ fps de media,
      mínimo ____ fps (objetivo 60, nunca menos de 30, RNF-21).
- [ ] Con `--log-level DEBUG`, abrir y cerrar la sesión: la diferencia entre «Inicio del audio de
      ciclo.apertura» y «Inicio de la animación wake (pantalla)» es ≤ 150 ms (RNF-22): ____ ms.
      Lo mismo para reposo y cierre: ____ ms, ____ ms.
- [ ] Cada animación de transición dura 2 s ± 0,1 s.

## Bandeja

- [ ] El icono es un círculo con un anillo, en cuatro variantes: dormido (gris), reposo (cian
      tenue), activo (cian; escuchando, procesando y hablando) y esperando (ámbar).
