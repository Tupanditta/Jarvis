# Lista manual de la fase 1. Ciclo de vida por voz

Se recorre en el equipo de referencia, con micrófono y altavoz reales, al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m models tests\models` en verde.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m hardware tests\hardware` en verde.
- [ ] `.\.venv\Scripts\python.exe scripts\diagnose_mic.py`: hay al menos una entrada que
      «detecta». Si recomienda otro dispositivo o API, copiar las líneas a `settings.toml`.
- [ ] `.\.venv\Scripts\python.exe scripts\calibrate_wakeword.py`: 9 o más detecciones de 10
      (RNF-30). Si no, aplicar la ganancia o el umbral recomendados, o entrenar el
      verificador con `--train-verifier`, y repetir. Anotar el resultado: ____ de 10.

## Arranque (proceso.md)

- [ ] `.\.venv\Scripts\pythonw.exe -m jarvis_assistant` arranca sin ventana de consola.
- [ ] En modo dormido no hay nada visible salvo el icono de la bandeja.
- [ ] El registro dice «Listo en N s» con N ≤ 10 (RNF-25).
- [ ] Lanzarlo por segunda vez no hace nada; el registro dice «Ya hay otra instancia».
- [ ] El texto emergente del icono es «Jarvis: dormido».

## CU-03. Abrir sesión

- [ ] «Hey Jarvis»: se oye «Sesión iniciada. Le escucho.» y aparece la ventana de estado con
      el número y el nombre de la sesión (la fecha de hoy).
- [ ] El estado pasa de «Hablando» a «Escuchando» al terminar la frase.
- [ ] Decir algo durante la frase de apertura no tiene efecto (A4).
- [ ] «Hey Jarvis» con la escucha activa: sin frase ni cambio visible (A2).
- [ ] En modo dormido, «Gracias Jarvis», «Buenas noches Jarvis» y «Jarvis» no hacen nada (A3).
- [ ] «Abrir sesión» en el menú de la bandeja abre la sesión igual que la voz (A6).
- [ ] Con el micrófono desactivado en Windows, el icono lo indica en unos segundos y la
      sesión se puede abrir desde la bandeja; al reactivarlo, el icono se recupera (A7).

## CU-04. Pasar a reposo

- [ ] «Gracias Jarvis»: se oye «A su disposición.» y el estado queda «En reposo»; la ventana
      sigue visible.
- [ ] 30 s de silencio en escucha pasan a reposo con la misma frase (A1).
- [ ] «Muchas gracias Jarvis por todo» se muestra como no reconocida y no pasa a reposo (A2).
- [ ] En reposo, «Hey Jarvis»: se oye «Le escucho.» y vuelve a «Escuchando», sin sesión nueva.
- [ ] En reposo, una conversación o un vídeo de fondo no tienen efecto.

## CU-05. Cerrar sesión

- [ ] «Buenas noches Jarvis» en escucha: se oye «Buenas noches. Sesión cerrada.», la ventana
      se oculta al terminar y el proceso sigue en marcha.
- [ ] «Buenas noches Jarvis» en reposo cierra la sesión (A1).
- [ ] «Buenas noches», sin «Jarvis», se ignora en escucha y en reposo (A4).
- [ ] «Hey Jarvis» justo después de la frase de cierre abre una sesión nueva (A3).
- [ ] «Salir» en la bandeja con una sesión abierta: el proceso termina en menos de 3 s, sin
      frase. Al arrancar de nuevo, el registro no dice «recuperada como interrumpida» (A5).
- [ ] Terminar el proceso desde el Administrador de tareas con una sesión abierta: al
      arrancar de nuevo, el registro dice «Sesión N recuperada como interrumpida» (A6).

## Bandeja

- [ ] El icono cambia de color en dormido, reposo, escuchando, procesando y hablando.
- [ ] «Abrir sesión» solo aparece en dormido; «Mostrar pantalla», solo con sesión.
- [ ] «Abrir configuración» y «Abrir registro» abren sus carpetas.

## Privacidad y consumo

- [ ] Con la red desactivada, todo lo anterior funciona igual (RNF-01).
- [ ] En el registro, en nivel `INFO`, no aparece ningún texto transcrito (RES-48).
- [ ] En las carpetas de datos y de registro no hay ningún archivo de audio.
- [ ] En modo dormido, el consumo de CPU del proceso es bajo y estable (RNF-04): ____ %.
- [ ] Latencia percibida entre el fin de «Gracias Jarvis» y la respuesta (RNF-03): ____ s.

## Inicio automático

- [ ] `.\scripts\install_startup.ps1` crea `Jarvis.lnk` en la carpeta Inicio; tras reiniciar
      la sesión de Windows el asistente está en la bandeja.
- [ ] `.\scripts\uninstall_startup.ps1` lo elimina.
