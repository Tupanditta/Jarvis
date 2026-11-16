# Lista manual de la fase 1. Ciclo de vida por texto

Se recorre en el equipo de referencia, con altavoz real, al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

Las órdenes se escriben en la caja de texto de la ventana y se envían con Enter.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m models tests\models` en verde.
- [ ] `.\.venv\Scripts\python.exe -m pytest -m hardware tests\hardware` en verde.

## Arranque (proceso.md)

- [ ] `.\.venv\Scripts\pythonw.exe -m jarvis_assistant` arranca sin ventana de consola.
- [ ] Aparece la ventana de fondo oscuro con el estado «Dormido» y la caja de texto con el foco
      y la ayuda «Escriba el código de activación para iniciar la sesión».
- [ ] La ventana no tiene ningún botón.
- [ ] Dormido, lo escrito en la caja se ve como asteriscos; «hy jarvs» + Enter abre la sesión.
- [ ] Con la sesión abierta, lo escrito se ve tal cual.
- [ ] El registro dice «Listo en N s» con N ≤ 10 (RNF-25).
- [ ] Lanzarlo por segunda vez no hace nada; el registro dice «Ya hay otra instancia».
- [ ] El texto emergente del icono de la bandeja es «Jarvis: dormido».
- [ ] Cerrar la ventana con ✕ la oculta y el proceso sigue en la bandeja; «Mostrar pantalla»
      la devuelve al frente con el foco en la caja.

## CU-03. Abrir sesión

- [ ] Escribir «Hey Jarvis»: se oye «Sesión iniciada. Le escucho.» y la ventana muestra el
      número y el nombre de la sesión (la fecha de hoy).
- [ ] También vale con erratas o sin mayúsculas: «hey jarbis», «jarvis».
- [ ] El estado pasa de «Hablando» a «Escuchando» al terminar la frase y la ayuda de la caja
      pasa a «Escriba una orden».
- [ ] Lo escrito durante la frase de apertura se atiende al terminar la frase (A4).
- [ ] «Hey Jarvis» con la escucha activa: sin frase ni cambio de estado (A2).
- [ ] En modo dormido, «Gracias Jarvis», «Buenas noches Jarvis» y cualquier otro texto no
      hacen nada (A3).
- [ ] «Abrir sesión» en el menú de la bandeja abre la sesión igual que escribir «Hey Jarvis» y
      muestra la ventana (A6).

## CU-04. Pasar a reposo

- [ ] «Gracias Jarvis»: se oye «A su disposición.» y el estado queda «En reposo»; la ayuda de
      la caja pasa a «En reposo. Escriba una orden».
- [ ] 30 s sin escribir en escucha pasan a reposo con la misma frase (A1).
- [ ] Teclear sin enviar reinicia esos 30 s.
- [ ] «Muchas gracias Jarvis por todo» se muestra como no reconocida y no pasa a reposo (A2).
- [ ] En reposo, «Hey Jarvis»: se oye «Le escucho.» y vuelve a «Escuchando», sin sesión nueva.
- [ ] En reposo, cualquier otro texto se descarta sin efecto.

## CU-05. Cerrar sesión

- [ ] «Buenas noches Jarvis» en escucha: se oye «Buenas noches. Sesión cerrada.», el estado
      vuelve a «Dormido», la ventana sigue visible y el proceso sigue en marcha.
- [ ] «Buenas noches Jarvis» en reposo cierra la sesión (A1).
- [ ] «Buenas noches», sin «Jarvis», se ignora en escucha y en reposo (A4).
- [ ] «Hey Jarvis» justo después de la frase de cierre abre una sesión nueva (A3).
- [ ] «Salir» en la bandeja con una sesión abierta: el proceso termina en menos de 3 s, sin
      frase. Al arrancar de nuevo, el registro no dice «recuperada como interrumpida» (A5).
- [ ] Terminar el proceso desde el Administrador de tareas con una sesión abierta: al
      arrancar de nuevo, el registro dice «Sesión N recuperada como interrumpida» (A6).

## Bandeja

- [ ] El icono cambia de color en dormido, reposo, escuchando y hablando.
- [ ] «Abrir sesión» solo aparece en dormido; «Mostrar pantalla», siempre.
- [ ] «Abrir configuración» y «Abrir registro» abren sus carpetas.

## Privacidad y consumo

- [ ] Con la red desactivada, todo lo anterior funciona igual (RNF-01).
- [ ] En el registro, en nivel `INFO`, no aparece el texto de ninguna orden (RES-48).
- [ ] El proceso no abre el micrófono: Windows no muestra el indicador de micrófono en uso.
- [ ] En modo dormido, el consumo de CPU del proceso es bajo y estable (RNF-04): ____ %.
- [ ] Latencia percibida entre pulsar Enter en «Gracias Jarvis» y la respuesta (RNF-03): ____ s.

## Inicio automático

- [ ] `.\scripts\install_startup.ps1` crea `Jarvis.lnk` en la carpeta Inicio; tras reiniciar
      la sesión de Windows el asistente está en la bandeja y su ventana, visible.
- [ ] `.\scripts\uninstall_startup.ps1` lo elimina.
