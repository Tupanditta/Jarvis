# CU-05. Cerrar sesión

- **Actor principal:** ACT-01.
- **Objetivo:** cerrar la sesión y devolver el asistente al modo dormido, sin terminar el proceso.
- **Requisitos:** RF-02, RF-07, RF-77, RF-79, RF-81, RF-82, RF-86, RF-93, RN-09, RN-43, RN-46, RN-47.
- **Módulos:** [Máquina de estados](../../Modulos/Infraestructura/maquina-estados.md), [Sesión](../../Modulos/Accion/sesion.md), [Captura de audio](../../Modulos/Infraestructura/captura-audio.md).

## Precondiciones

Sesión abierta; asistente en `LISTENING_COMMAND` o `AWAITING_*`.

## Disparador

El usuario dice «Buenas noches Jarvis».

## Flujo principal

1. El sistema captura y transcribe la frase, y el enrutador la reconoce como frase de control (similitud ≥ 80).
2. El sistema cancela el diálogo y la orden en curso, detiene el protocolo y los binarios en ejecución, y deja en `error` las tareas `pendiente` (RN-46).
3. El sistema elimina de forma lógica las sesiones desplazadas por desbordamiento durante esta sesión (RN-09) y marca la sesión como cerrada.
4. El sistema pasa a `DORMIDO`. A la vez empiezan la animación de dormirse (2 s) y la frase «Buenas noches. Sesión cerrada.».
5. Al terminar la animación, la pantalla de sesión y el HUD se ocultan. El transcriptor se libera.
6. El sistema atiende solo «Hey Jarvis». El proceso sigue en marcha.

## Flujos alternativos

- **A1. Cierre desde reposo.** En `IDLE`, la frase se capta con la escucha restringida: solo frases cortas se transcriben y solo se acepta esta, con similitud ≥ 85. Sigue en el paso 2.
- **A2. Escucha restringida desactivada.** Con `audio.closing_phrase_in_idle = false`, en reposo hay que decir antes «Hey Jarvis».
- **A3. «Hey Jarvis» durante la animación de cierre.** CU-03, A5.
- **A4. Frase parecida.** «Buenas noches» sin «Jarvis» no alcanza el umbral y se ignora.
- **A5. Salir desde la bandeja o fin de la sesión de Windows.** Se ejecutan los pasos 2 y 3 sin frase ni animación, y el proceso termina.
- **A6. El proceso termina de forma inesperada.** La sesión queda abierta en la base de datos; en el siguiente arranque se cierra como «interrumpida» y se aplican los pasos 2 y 3 (RN-47).

## Postcondiciones

Sesión con `closed_at` y motivo; asistente en `DORMIDO`; ninguna ventana visible; sin trabajos programados.
