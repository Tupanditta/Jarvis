# Lista de verificación manual del prototipo 1

Guion de pruebas manuales con micrófono, altavoz, foco, monitores y arranque. Origen: `software/design.md` §9.3 y T-43 de `software/tasks.md`. Se ejecuta en T-52 (usuario, Windows 11). Los casos de uso están en `software/CasosUso/Especificaciones/` (CU-03, CU-04, CU-05).

Convenciones:

- Todos los comandos se lanzan desde `implementation\` (PowerShell), salvo que se indique otra cosa.
- Casillas de resultado: `[ ]` sin probar, `[✔]` correcto, `[✘]` falla. Escribe el detalle en **Notas**.
- Lo que el diseño no especifica se marca **por confirmar**; no se da por esperado.
- Log del asistente: `%LOCALAPPDATA%\jarvis_assistant\logs\jarvis.log`. El log no contiene audio ni texto transcrito en nivel `INFO` (D-24).
- Frases fijas: «Sesión iniciada. Le escucho.» (apertura), «Le escucho.» (vuelta desde reposo), «A su disposición.» (reposo), «Buenas noches. Sesión cerrada.» (cierre).

## 0. Datos de la ejecución y hardware de referencia

| Campo | Valor |
|---|---|
| Fecha | |
| Probador | |
| CPU | |
| GPU | |
| RAM | |
| Windows (versión y compilación) | |
| Monitor principal: modelo, resolución, frecuencia (Hz) | |
| Segundo monitor (si hay): modelo, resolución, frecuencia (Hz) | |
| Micrófono (nombre en Windows y API de host que abre el log) | |
| Altavoz / salida | |
| Versión del asistente / commit | |
| ¿Existe `implementation\models\openwakeword\buenas_noches_jarvis.onnx`? (sí/no) | |

## 1. Preparación

1. Detener cualquier instancia previa: `powershell -ExecutionPolicy Bypass -File scripts\stop_jarvis.ps1` (imprime «Procesos terminados: N» o «No hay procesos del asistente en ejecucion.»).
2. Comprobar el entorno: existe `implementation\.venv\Scripts\pythonw.exe` y la carpeta `implementation\models\` con los modelos obligatorios (sin ellos no arranca, §6).
3. Borrar o renombrar `%LOCALAPPDATA%\jarvis_assistant\logs\jarvis.log` para leer solo la ejecución actual.
4. Lanzamiento manual sin consola: `powershell -ExecutionPolicy Bypass -File scripts\start_jarvis.ps1`. Para ver errores de arranque: `... start_jarvis.ps1 -Console` (solo diagnóstico; no es el modo de las pruebas de arranque).
5. Terminar el asistente al acabar una prueba: `scripts\stop_jarvis.ps1` (equivale a terminarlo desde el sistema, CU-05 A3).

Alcance de las pruebas de voz: CU-05 por voz («Buenas noches Jarvis») **no está disponible mientras falte el modelo opcional** (DEF-30, D-42; modelo futuro P-22). Sin él se ejecuta el bloque 5; con él, además el bloque 6.

## 2. Arranque, instancia única y terminación del proceso

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-01 | Instalar el arranque automático: `powershell -ExecutionPolicy Bypass -File scripts\install_startup.ps1`. Abrir `shell:startup` (Win+R). | Existe `Jarvis.lnk` que apunta a `.venv\Scripts\pythonw.exe` con argumentos `-I -m jarvis_assistant`, directorio de trabajo `implementation\` y ventana minimizada. El script imprime «Acceso directo creado: ...». | RF-75, D-40 | [ ] | |
| M-02 | Cerrar sesión de Windows y volver a entrar (o reiniciar) con el acceso directo instalado. | Al entrar, el proceso arranca solo, **sin ventana de consola y sin nada visible** en pantalla ni en la barra de tareas (**por confirmar**: si el acceso directo minimizado deja algún botón en la barra). No se abre ninguna sesión. | RF-75, CU-03 criterios 1 y 2 | [ ] | |
| M-03 | Abrir el Administrador de tareas (Ctrl+Mayús+Esc), pestaña Detalles. | Aparece `pythonw.exe` (el asistente) en ejecución. El log tiene el arranque en `DORMIDO`. | RF-75, RF-77 | [ ] | |
| M-04 | Con el asistente en marcha, ejecutar de nuevo el acceso directo (doble clic en `Jarvis.lnk` o repetir `start_jarvis.ps1`). | No aparece un segundo `pythonw.exe` del asistente; no se ve nada. El log registra que la segunda instancia sale sin hacer nada. | D-16 | [ ] | |
| M-05 | Abrir una sesión con «Hey Jarvis» (bloque 3) y terminar `pythonw.exe` desde el Administrador de tareas («Finalizar tarea»). | El proceso termina y la pantalla de sesión desaparece. No se dice ninguna frase (**por confirmar**: CU-05 A3 deja por definir si se muestra o dice algo al terminar). | CU-05 A3, RF-77, DEF-19 | [ ] | |
| M-06 | Tras M-05, lanzar el acceso directo (o cerrar sesión de Windows y volver a entrar). | El proceso arranca en modo dormido, **sin sesión** (la anterior se perdió). | CU-05 A3 (criterio de aceptación), DEF-17 | [ ] | |
| M-07 | Con la sesión abierta, apagar o reiniciar el equipo, o cerrar la sesión de Windows. | El proceso termina con el apagado o el cierre de sesión (no queda `pythonw.exe` al volver a entrar, salvo el relanzado por M-02). | RF-77, CU-05 A3 | [ ] | |
| M-08 | Retirar el arranque: `powershell -ExecutionPolicy Bypass -File scripts\uninstall_startup.ps1`. Revisar `shell:startup` y volver a iniciar sesión. | `Jarvis.lnk` ya no existe; al entrar en Windows no se lanza el asistente. | RF-75, D-40 | [ ] | |

## 3. CU-03 Abrir sesión (micrófono y altavoz reales)

Prerrequisito: asistente en `DORMIDO` (`start_jarvis.ps1`).

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-10 | Decir «Gracias Jarvis», «Buenas noches Jarvis» y «Jarvis» suelto en modo dormido. | No se abre sesión, no hay respuesta ni nada en pantalla. | CU-03 A3, RN-43 | [ ] | |
| M-11 | Decir «Hey Jarvis» en modo dormido. | Se abre sesión nueva; la pantalla de sesión aparece a pantalla completa, al frente y con foco; la animación de despertar (2 s) empieza a la vez que «Sesión iniciada. Le escucho.»; el asistente queda escuchando. El log registra la detección aceptada y el cambio de modo. | CU-03 pasos 2-8, RF-60, RF-82 | [ ] | |
| M-12 | Cerrar la sesión por terminación del proceso y repetir M-11 un segundo día o dos veces seguidas con sesión cerrada (**solo con modelo de cierre**: ver bloque 6 para cerrar por voz). | Dos aperturas crean dos sesiones distintas. Sin modelo de cierre esto se cubre con la prueba automática; aquí queda **por confirmar** cómo observarlo a mano (el log no está especificado para esto). | CU-03 criterio 4, RF-01 | [ ] | |
| M-13 | Dichas durante «Sesión iniciada. Le escucho.»: «Hey Jarvis» y una orden hablada (A4). | No tienen efecto mientras suena la frase: no se capturan ni se detectan. Dichas más de 0,2 s después de acabar, se atienden con normalidad. | CU-03 A4, RNF-07, DEF-22 | [ ] | |
| M-14 | Con la escucha activa, decir «Hey Jarvis». | Se ignora en silencio: sin animación, sin voz, sin sesión nueva; la cuenta de 30 s vuelve a empezar (no pasa a reposo antes de 30 s desde ese «Hey Jarvis»). | CU-03 A2, RF-78 | [ ] | |
| M-15 | Dar una orden y callar 1 s; después hablar sin parar más de 15 s. | La orden se da por terminada tras 1 s de pausa, y como mucho a los 15 s. Tras una orden sigue escuchando sin repetir «Hey Jarvis». | CU-03 paso 8, RF-61 | [ ] | |
| M-16 | Notificaciones pendientes (recordatorio vencido con el asistente dormido o apagado), si hay forma de crearlo. | Se dispara tras «Sesión iniciada. Le escucho.», nunca antes ni en modo dormido. **Por confirmar**: el prototipo no define cómo crear recordatorios a mano; si no es posible, marcar «no aplicable». | CU-03 pasos 5 y 7, RN-22 | [ ] | |
| M-17 | Con la pantalla de sesión abierta y escuchando, observar el núcleo de la animación mientras se habla y mientras suena la frase del asistente. | El núcleo cambia con el nivel del micrófono al escuchar y con el nivel de la voz del asistente al hablar. | CU-03 paso 8, RF-83 | [ ] | |
| M-18 | Directorio de trabajo tras abrir sesión. | **Por confirmar** cómo observarlo sin órdenes que lo cambien (en el prototipo no hay órdenes `cd`); cubierto por la prueba automática. | CU-03 criterio 5, RN-14 | [ ] | |

CU-03 A5 («Hey Jarvis» durante la animación de dormirse del cierre) **no se prueba a mano**: con voz real «Buenas noches. Sesión cerrada.» dura unos 2 s y no queda ventana durante la animación; se verifica solo con dobles de prueba con tiempos controlados (§9 inicio, CU-03 criterio de aceptación).

## 4. CU-04 Pasar a reposo

Prerrequisito: sesión abierta y escuchando (M-11).

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-20 | Decir «Gracias Jarvis». | El asistente dice «A su disposición.», empieza a la vez la animación de dormirse (2 s), deja de escuchar órdenes y la pantalla de sesión **sigue abierta** (reposo). | CU-04 flujo principal, RF-76, RF-79, RF-81, RF-82 | [ ] | |
| M-21 | En reposo, decir «Hey Jarvis». | Vuelve a escuchar **sin sesión nueva** y conservando la sesión; «Le escucho.» a la vez que la animación de despertar; la pantalla no se cierra ni se reabre. | CU-03 A1, RN-43 | [ ] | |
| M-22 | En reposo: decir «Gracias Jarvis» y una orden cualquiera. | Sin respuesta, sin animación y sin cambio de estado. | CU-04 A3, criterio «en reposo» | [ ] | |
| M-23 | Escuchando: decir una frase no reconocida (incluida «Hey Jarvis» transcrita o una orden cualquiera sin intención). | Sin voz ni animación; sigue escuchando y la frase reinicia la cuenta de 30 s. No pasa a reposo. | CU-04 A1, RF-65 | [ ] | |
| M-24 | Escuchando, callar 30 s desde el final de la última frase del asistente. Después repetir hablando antes de los 30 s. | A los 30 s: «A su disposición.», animación de dormirse y reposo con sesión abierta. Si se habló antes, no pasa a reposo. La cuenta no corre mientras el asistente habla. | CU-04 A5, RF-78 | [ ] | |
| M-25 | Decir «Gracias Jarvis» mientras suena «Sesión iniciada. Le escucho.» (A4 de CU-03). | No tiene efecto (no se atiende el micrófono mientras habla). | CU-03 A4, RNF-07 | [ ] | |
| M-26 | Decir «Gracias Jarvis» con la animación de despertar aún en curso (<2 s tras «Hey Jarvis»; difícil por A4, probar al terminar la frase). | La de despertar se funde con la de dormirse sin saltos visibles. **Por confirmar**: ventana útil para observarlo con voz real; puede quedar cubierto solo por dobles. | CU-04 criterio de fundido, RF-81 | [ ] | |
| M-27 | Observar el núcleo mientras suena «A su disposición.» (con «Gracias Jarvis» y por silencio), incluida la animación de dormirse. | El núcleo cambia con el nivel de esa frase hasta que acaba, aunque ya esté en reposo. | CU-04 criterios RF-83 | [ ] | |
| M-28 | Con «Buenas noches Jarvis» dicho **sin modelo** (A4 de CU-04 / A6 de CU-05). | Se sigue escuchando, no se cierra la sesión. | CU-04 A4, CU-05 A6 | [ ] | |

## 5. CU-05 sin el modelo de cierre (DEF-30, D-42, CU-05 A6)

Cómo probar el arranque sin el modelo opcional: renombrar o mover `implementation\models\openwakeword\buenas_noches_jarvis.onnx` (o comprobar que no está) y arrancar con `scripts\start_jarvis.ps1`.

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-30 | Arrancar sin `buenas_noches_jarvis.onnx`. | El asistente arranca (no se queda sin proceso). El log tiene el aviso de modelo ausente (`WARNING`). | DEF-30, D-42, CU-05 A6 | [ ] | |
| M-31 | Probar «Hey Jarvis» y «Gracias Jarvis» (M-11, M-20). | Funcionan con normalidad. | CU-05 A6 | [ ] | |
| M-32 | Con la sesión abierta, decir «Buenas noches Jarvis» (en escucha y en reposo). | No cierra la sesión, no responde, no muestra la animación de dormirse y el proceso sigue. | CU-05 A6, CU-04 A4 | [ ] | |
| M-33 | (Opcional, **por confirmar** cómo provocarlo) Colocar en `models\openwakeword\` un `buenas_noches_jarvis.onnx` corrupto (archivo con texto) y arrancar. | Arranca; el log contiene un registro de error sobre ese archivo; «Hey Jarvis» y «Gracias Jarvis» funcionan; «Buenas noches Jarvis» no cierra la sesión. | CU-05 A6 (criterio de archivo corrupto), D-42 | [ ] | |

## 6. CU-05 con el modelo de cierre (solo si existe `buenas_noches_jarvis.onnx`)

Hoy el modelo no existe (DEF-30, P-22): si falta, marcar el bloque «no aplicable». Si se coloca: copiar a `implementation\models\openwakeword\` y reiniciar (`stop_jarvis.ps1` y `start_jarvis.ps1`).

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-40 | Con modelo añadido tras haber probado sin él, reiniciar y decir «Buenas noches Jarvis». | La sesión se cierra sin más cambios. | CU-05 criterio «añadir el archivo» | [ ] | |
| M-41 | Escuchando, decir «Buenas noches Jarvis». | «Buenas noches. Sesión cerrada.» a la vez que la animación de dormirse (2 s); queda en `DORMIDO`; al acabar la animación la pantalla se cierra y no queda nada visible. | CU-05 pasos 3-6 | [ ] | |
| M-42 | En reposo, decir «Buenas noches Jarvis». | Mismo resultado que M-41. | CU-05 | [ ] | |
| M-43 | Tras cerrar: el proceso sigue en el Administrador de tareas; «Hey Jarvis» abre sesión nueva; «Gracias Jarvis» y órdenes no responden. | Cumple. | CU-05 postcondiciones, CU-03 | [ ] | |
| M-44 | Decir «Buenas noches Jarvis» durante «Le escucho.»/«A su disposición.» y luego más de 0,2 s después de que acabe. | Durante la frase no cierra; después, sí. | CU-05 A4, RNF-07 | [ ] | |
| M-45 | Estando en `DORMIDO`, decir «Buenas noches Jarvis». | Sin respuesta, animación ni cambio. | CU-05 A2 | [ ] | |
| M-46 | Observar el núcleo durante «Buenas noches. Sesión cerrada.» y la animación de dormirse. | Cambia con el nivel de la frase. | CU-05 RF-83 | [ ] | |
| M-47 | Ninguna frase de voz termina el proceso. | `pythonw.exe` sigue tras todas las frases probadas. | CU-05, RF-77 | [ ] | |

CU-05 A5 («Hey Jarvis» durante la animación de dormirse del cierre) **no se prueba a mano**: con voz real, la animación no deja ventana tras ~2 s; se verifica solo con dobles de prueba con tiempos controlados.

## 7. Foco, ventanas y monitores

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-50 | Con sesión abierta, Alt+Tab a otra aplicación. | Esa aplicación queda por delante de la pantalla de sesión (no queda siempre encima). | CU-03 reglas, RF-82, DEF-27 | [ ] | |
| M-51 | Tras M-50, pasar a reposo (si hace falta, por silencio o «Gracias Jarvis»; con la otra aplicación delante) y decir «Hey Jarvis». | La pantalla de sesión vuelve al frente y **toma el foco**; «Le escucho.». | CU-03 A1, RF-82 | [ ] | |
| M-52 | Con otra aplicación con foco (p. ej. un editor con cursor de texto) y el asistente en `DORMIDO`, decir «Hey Jarvis». | La pantalla de sesión pasa al frente y toma el foco aunque la otra lo tuviera (respaldo `AttachThreadInput`, RES-16). | CU-03 criterio de foco, RES-16 | [ ] | |
| M-53 | Dos monitores: poner el cursor y la ventana con foco en el monitor **no principal** y decir «Hey Jarvis». | La pantalla de sesión se abre a pantalla completa en el monitor **principal**. | CU-03 criterio multi-monitor, RF-82 | [ ] | |
| M-54 | Con la sesión abierta, no mover el ratón 2 s; después moverlo. | El cursor se oculta tras 2 s sin moverse y reaparece al mover. | CU-03 criterio de cursor, RF-82 | [ ] | |
| M-55 | Pantalla de sesión abierta: Alt+F4. Después clic derecho/«Cerrar ventana» en el icono de la barra de tareas (si existe), si hay forma. | No se cierra la pantalla ni termina el proceso. **Por confirmar**: qué icono o menú hay en la barra para «Cerrar ventana». | RF-77, RF-82 | [ ] | |
| M-56 | Con la sesión abierta, Win+D (minimiza todo). Con el asistente en reposo, decir «Hey Jarvis». | La pantalla vuelve al frente y toma el foco. | RF-82 | [ ] | |
| M-57 | Documental: abrir un Símbolo del sistema **como administrador** en primer plano y decir «Hey Jarvis». | Se anota si la pantalla queda al frente con foco y qué registra el log. Documenta el comportamiento; **no es criterio de aceptación**. | §8.2 (riesgo de procesos elevados) | [ ] | |

## 8. Animaciones, fundidos y observación visual

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-60 | Observar en el monitor real despertar, dormirse y escucha, sin y con transcripción en curso (decir una orden larga). | Dibujo sin tirones visibles; cifra de fps y desfase no se miden a mano (ver M-62 y T-47..T-50). | RNF-21, CU-03 | [ ] | |
| M-61 | Fundidos: provocar dormirse con despertar en curso y despertar con dormirse en curso (cuando se pueda). | Fundido suave sin saltos visibles. | RF-80, RF-81 | [ ] | |
| M-62 | Grabar a cámara rápida (p. ej. 240 fps) el desfase animación–voz (§5.9, T-49). | Desfase ≤ 45 ms. El detalle de la calibración se anota en T-49. | RNF-22, §5.9 | [ ] | |
| M-63 | Observar el núcleo en las cuatro frases: «Sesión iniciada. Le escucho.», «Le escucho.», «A su disposición.», «Buenas noches. Sesión cerrada.» (esta última solo con modelo). | El núcleo reacciona al nivel de cada frase mientras suena; al escuchar, al nivel del micrófono. | RF-83 | [ ] | |

## 9. Micrófono, robustez y registro de errores

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-70 | Con el asistente en marcha, desconectar el micrófono (USB o desactivar el dispositivo) y volver a conectarlo. | No se cierra el proceso ni se muestra nada. El log registra el aviso con la causa y los reintentos cada 5 s; al reconectar, vuelven los bloques y «Hey Jarvis» funciona. | D-23, §4.5 | [ ] | |
| M-71 | Provocar una excepción a propósito en un hilo (modo de diagnóstico). | Queda en el log (D-24). **Por confirmar**: el diseño no define el mecanismo (nombre del modo/variable) del modo de diagnóstico; hasta que se defina, anotar «no ejecutable». | D-24 | [ ] | |
| M-72 | Prueba sin red: desactivar los adaptadores de red (Wi-Fi/Ethernet) y recorrer arranque, M-11, M-20 y (si procede) M-41. | Todo funciona igual; nada intenta conectarse. | RNF-02 | [ ] | |
| M-73 | Con la red **activa**, ejecutar un ciclo de vida completo (arranque, abrir, escuchar, reposo, volver) con un monitor de tráfico (Monitor de recursos de Windows → Red, o registro del Firewall). | 0 conexiones salientes del proceso `pythonw.exe` del asistente. | RNF-01 | [ ] | |

## 10. Selección del micrófono y diagnóstico (BUG-01, D-43)

Variables (D-43): `JARVIS_INPUT_DEVICE` (subcadena del nombre), `JARVIS_INPUT_HOSTAPI` (p. ej. `MME`), `JARVIS_LOG_LEVEL` (`DEBUG` para diagnóstico). Se fijan con `setx` y se aplican al **volver a iniciar sesión** en Windows (el acceso directo hereda el entorno al arrancar la sesión).

Comandos exactos (desde `implementation\`):

```powershell
.\.venv\Scripts\python.exe scripts\diagnose_mic.py                  # todas las entradas (5 s cada una, di «Hey Jarvis»)
.\.venv\Scripts\python.exe scripts\diagnose_mic.py --default        # solo el predeterminado
.\.venv\Scripts\python.exe scripts\diagnose_mic.py --devices 1 5 12 # índices concretos
.\.venv\Scripts\python.exe scripts\diagnose_mic.py --configured     # lo que elegiría la app con tu entorno
setx JARVIS_INPUT_DEVICE "Varios micrófonos"
setx JARVIS_INPUT_HOSTAPI "MME"
setx JARVIS_LOG_LEVEL "DEBUG"
```

`diagnose_mic.py` imprime un veredicto por dispositivo (MUDO, SEÑAL o DETECTA), el método de apertura y la API de host, y recomienda las variables exactas. No guarda audio salvo con `--save-wav DIR`.

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-80 | Ejecutar `diagnose_mic.py` (todas) diciendo «Hey Jarvis» en cada cuenta atrás. | Recomienda una configuración (`JARVIS_INPUT_DEVICE` / `JARVIS_INPUT_HOSTAPI`) o indica «no se pudo verificar». Anotar para P-24 qué método de apertura (directo 16 kHz o nativo+remuestreo) usó cada dispositivo con señal. | D-43, P-24 | [ ] | |
| M-81 | Aplicar la recomendación con `setx`, cerrar y abrir sesión de Windows. Con el asistente en marcha, leer el log. | Línea de dispositivo abierto con nombre, API de host, índice (y canales/frecuencia). Texto aproximado: «Micrófono abierto». | D-43 §4.6 b | [ ] | |
| M-82 | Esperar ≥ 10 s hablando cerca del micrófono y mirar el log. | Líneas `audio: pico=… dBFS rms=… dBFS bloques/s=… descartados=…` cada 5 s, con pico y RMS coherentes con la voz (silencio muy bajo, voz claramente más alta; bloques/s ≈ 31,25). | D-43 | [ ] | |
| M-83 | `setx JARVIS_INPUT_DEVICE "NombreQueNoExiste"`, volver a iniciar sesión. | Arranca con el predeterminado de Windows y deja un `WARNING` con la configuración pedida y la lista de entradas. El aviso no se repite cada 5 s. | D-43 §4.6 a | [ ] | |
| M-84 | `setx JARVIS_LOG_LEVEL "DEBUG"`, volver a iniciar sesión y decir «Hey Jarvis». | En el log, `DEBUG`: «Puntuación máxima» por segundo (de `hey_jarvis`); `INFO`: «Detección aceptada» con frase y puntuación. | D-43 | [ ] | |
| M-85 | Silenciar el micrófono en Windows (o taparlo/desactivarlo) con el asistente abierto > 5 s. | `WARNING` de «micrófono mudo» una vez por episodio; al volver la señal, un `INFO` de recuperación. | D-43 §4.6 b | [ ] | |
| M-86 | Al terminar el diagnóstico: volver a `INFO` (`setx JARVIS_LOG_LEVEL "INFO"` o quitar la variable) y limpiar las variables si no se quieren conservar. | Nivel normal restaurado (DEBUG habilita también el texto transcrito, D-24). **Por confirmar**: mecanismo para borrar variables de usuario (p. ej. Configuración de Windows → Variables de entorno). | D-24, D-43 | [ ] | |

## 11. Diagnóstico si no despierta con «Hey Jarvis»

Arrancar con `JARVIS_LOG_LEVEL=DEBUG` (M-84) y repetir la frase. Mirar `%LOCALAPPDATA%\jarvis_assistant\logs\jarvis.log`.

1. ¿Hay línea «Micrófono abierto» (dispositivo, API de host, índice)?
   - No: el micrófono no abre. Buscar el `WARNING` con la causa (ocupado, desconectado, API que no admite el flujo; D-43). Cerrar apps que lo usen, elegir otro dispositivo (M-80, M-81).
   - Sí: continuar.
2. ¿Hay informes `audio: pico=…` cada 5 s y aviso de «micrófono mudo»?
   - Hay aviso «micrófono mudo» o pico ≈ −120 dBFS con voz: **micrófono mudo (silencio digital)** → ejecutar `diagnose_mic.py` y fijar otro dispositivo con `setx JARVIS_INPUT_DEVICE ...` (y/o `JARVIS_INPUT_HOSTAPI`); revisar Windows → Privacidad y seguridad → Micrófono (acceso de aplicaciones de escritorio activado) y que no esté silenciado ni desactivado en Sonido. Este es el síntoma de BUG-01 (el predeterminado dio silencio digital de forma intermitente).
   - No hay informes `audio:`: bloques sin llegar; revisar si hay `WARNING` de reintento.
   - Informes con pico/RMS acordes con la voz: **hay señal**, continuar.
3. Con señal: ¿aparece «Puntuación máxima» de `hey_jarvis` por encima de ~0,5 al decir la frase, y «Detección aceptada»?
   - No hay «Detección aceptada» y la puntuación máxima queda baja (umbral 0,5): **señal pero puntuación baja** → pronunciación (más claro, más cerca, ritmo normal), ruido ambiente, ganancia/volumen del micrófono; probar varias veces (la puntuación varía con cada pronunciación) y otro dispositivo si se sospecha del dispositivo (no está probado que dependa del dispositivo, D-43). Cambio de umbral: **por confirmar** (fijado por DEF-25; no se cambia a mano).
   - «Detección aceptada» pero no se abre la pantalla: problema de foco o ventana (bloque 7), no de micrófono; mirar el log tras la detección. Detección suprimida por antirrebote aparece en `DEBUG`.
4. Anotar en Notas el dispositivo, la API de host, los picos y las puntuaciones observadas.

## 11 bis. Arranque con la sesión abierta (DEF-31, temporal)

**Temporal:** estas dos pruebas (M-87, M-88) se retiran de esta lista con T-76 y T-77, cuando se retome la activación por «Hey Jarvis» y desaparezca el arranque con sesión abierta (condición de retirada de D-45 f). Mientras estén vigentes, M-02, M-03 y M-06 (arranque en `DORMIDO` sin nada visible) solo se cumplen con `start_with_open_session=False`. Ajuste: `start_with_open_session` en `config.py` (D-45); cambiarlo y reiniciar el asistente.

| ID | Qué se hace | Resultado esperado | Traza | ✔/✘ | Notas |
|---|---|---|---|---|---|
| M-87 | Con el acceso directo instalado (M-01), cerrar sesión de Windows y volver a entrar (o reiniciar), primero con `start_with_open_session=True` (valor por defecto) y después con `False`. Sin consola en ambos casos. | **`True`:** al entrar en Windows el proceso arranca solo y se abre la pantalla de sesión a pantalla completa y con foco; suena «Sesión iniciada. Le escucho.» y el asistente queda escuchando (se atiende una orden sin decir antes «Hey Jarvis»). **`False`:** el arranque queda en `DORMIDO` sin nada visible; decir «Hey Jarvis» abre la sesión (M-11). Este caso `False` solo es verificable cuando se retome la activación por «Hey Jarvis»; hasta entonces anotar «no aplicable». | DEF-31, D-45, RF-75, CU-03 A6 | [ ] | |
| M-88 | Lanzar el asistente a mano (`scripts\start_jarvis.ps1`, sin pasar por el inicio de Windows) con `start_with_open_session=True`, y después con `False`. | **`True`:** al arrancar el proceso (sin entrar en Windows) se abre la pantalla de sesión, suena «Sesión iniciada. Le escucho.» y el asistente queda escuchando; el log registra la apertura de sesión sin detección de «Hey Jarvis». La apertura espera a que termine la precarga (D-45). **`False`:** `DORMIDO` sin nada visible ni sonido; «Hey Jarvis» abre la sesión (solo verificable al retomar la activación; hasta entonces «no aplicable»). | DEF-31, D-45, CU-03 A6 | [ ] | |

## 12. Resumen de la ejecución

| Bloque | Pruebas | ✔ | ✘ | No aplicable | Notas |
|---|---|---|---|---|---|
| 2 Arranque y terminación | M-01..M-08 | | | | |
| 3 CU-03 | M-10..M-18 | | | | |
| 4 CU-04 | M-20..M-28 | | | | |
| 5 CU-05 sin modelo | M-30..M-33 | | | | |
| 6 CU-05 con modelo | M-40..M-47 | | | | |
| 7 Foco, ventanas, monitores | M-50..M-57 | | | | |
| 8 Animaciones | M-60..M-63 | | | | |
| 9 Robustez, red | M-70..M-73 | | | | |
| 10 Micrófono (D-43) | M-80..M-86 | | | | |
| 11 bis Arranque con sesión abierta (DEF-31, temporal; se retira con T-76 y T-77) | M-87..M-88 | | | | |

Defectos encontrados (ID, descripción, prueba que lo detecta):

-
