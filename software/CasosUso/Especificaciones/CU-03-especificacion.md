# CU-03. Abrir sesión

- **Actor principal:** ACT-01.
- **Objetivo:** abrir una sesión nueva y dejar el asistente escuchando órdenes.
- **Requisitos:** RF-01, RF-41, RF-60, RF-61, RF-75, RF-78, RF-79, RF-80, RF-82, RF-83, RF-86, RF-87, RF-96, RNF-03, RNF-07, RNF-22, RNF-25, RN-02, RN-14, RN-22, RN-43, RES-10, RES-32, RES-42.
- **Módulos:** [Máquina de estados](../../Modulos/Infraestructura/maquina-estados.md), [Entrada por texto](../../Modulos/Infraestructura/entrada-texto.md), [Sesión](../../Modulos/Accion/sesion.md), [Interfaz](../../Modulos/Infraestructura/hud.md).

## Precondiciones

El proceso está en marcha en `DORMIDO`: sin sesión, con la ventana visible en su aspecto de dormido y la caja de texto atendiendo solo «Hey Jarvis». Es la situación al arrancar y tras cerrar una sesión.

## Disparador

El usuario escribe «Hey Jarvis» en la caja de texto y pulsa Enter.

## Flujo principal

1. El enrutador reconoce la frase de activación comparando la frase completa (similitud ≥ 80); valen las erratas leves y «Jarvis» a secas.
2. El sistema recarga la configuración, crea una sesión nueva con el nombre y la importancia por defecto (RN-02) y pone el directorio de trabajo en la carpeta del usuario (RN-14).
3. La pantalla de sesión pasa al frente con el foco en la caja de texto. A la vez empiezan la animación de despertar (2 s) y la frase «Sesión iniciada. Le escucho.».
4. Al terminar la frase, el sistema entrega los avisos de recordatorio que quedaron pendientes sin sesión (RF-41; continúa en CU-12).
5. El sistema pasa a `LISTENING_COMMAND`: atiende cada orden que el usuario escribe, sin repetir «Hey Jarvis». El núcleo del orbe reacciona a la voz del asistente cuando habla. Empieza la cuenta de 30 s sin escribir.

## Flujos alternativos

- **A1. Volver a escuchar desde reposo.** En `IDLE`, «Hey Jarvis» no abre sesión nueva: el sistema dice «Le escucho.» y muestra la animación de despertar, en la pantalla de sesión si es la ventana activa o, si no lo es, en el HUD flotante, sin tocar el foco. Sigue en el paso 5.
- **A2. «Hey Jarvis» con la escucha activa.** Se ignora en silencio: sin animación ni frase. La cuenta de 30 s vuelve a empezar. Si el asistente estaba diciendo una respuesta, calla (RN-48).
- **A3. Otra frase en modo dormido.** «Gracias Jarvis», «Buenas noches Jarvis» o cualquier otro texto no tienen ningún efecto.
- **A4. Texto enviado durante la frase de apertura.** Las frases del ciclo de vida no se interrumpen: lo enviado mientras suena una se atiende, en orden, al terminar.
- **A5. «Hey Jarvis» durante la animación de cierre de la sesión anterior.** La sesión nueva se abre al instante; la pantalla no se oculta y la animación de dormirse se funde con la de despertar.
- **A6. Apertura desde la bandeja.** «Abrir sesión» en el menú del icono de la bandeja equivale al paso 1.
- **A7.** Retirado: entrada por texto (no hay micrófono).
- **A8. Configuración inválida** (paso 2): se conserva la anterior y, tras la frase de apertura, el sistema dice «Hay un error en la configuración de {archivo}. Uso la anterior.».

## Postcondiciones

Sesión abierta y registrada con `closed_at` vacío; asistente en `LISTENING_COMMAND`; pantalla de sesión visible.
