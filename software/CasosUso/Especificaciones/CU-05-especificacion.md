# CU-05. Cerrar sesión

- **Actor principal:** ACT-01.
- **Objetivo:** cerrar la sesión y devolver el asistente al modo dormido, sin terminar el proceso.
- **Requisitos:** RF-02, RF-07, RF-77, RF-79, RF-81, RF-82, RF-86, RF-93, RN-09, RN-43, RN-46, RN-47.
- **Módulos:** [Máquina de estados](../../Modulos/Infraestructura/maquina-estados.md), [Sesión](../../Modulos/Accion/sesion.md), [Entrada por texto](../../Modulos/Infraestructura/entrada-texto.md).

## Precondiciones

Sesión abierta; asistente en `LISTENING_COMMAND` o `AWAITING_*`.

## Disparador

El usuario escribe «Buenas noches Jarvis» y pulsa Enter.

## Flujo principal

1. El enrutador reconoce el texto como frase de control (similitud ≥ 80).
2. El sistema cancela el diálogo y la orden en curso, detiene el protocolo y los binarios en ejecución, y deja en `error` las tareas `pendiente` (RN-46).
3. El sistema marca la sesión como cerrada y elimina las sesiones desplazadas por desbordamiento durante esta sesión (RN-09, RN-12). Si la sesión no tiene actividades, no es importante y no desplazó a ninguna, la elimina en lugar de cerrarla (RN-69).
4. El sistema pasa a `DORMIDO`. A la vez empiezan la animación de dormirse (2 s) y la frase «Buenas noches. Sesión cerrada.».
5. Al terminar la animación, la pantalla de sesión queda en su aspecto de dormido, visible, y el HUD se oculta.
6. El sistema atiende solo «Hey Jarvis». El proceso sigue en marcha.

## Flujos alternativos

- **A1. Cierre desde reposo.** En `IDLE`, la frase se acepta con similitud ≥ 85. Sigue en el paso 2.
- **A2.** Retirado: entrada por texto (el cierre en reposo se reconoce siempre).
- **A3. «Hey Jarvis» durante la animación de cierre.** CU-03, A5.
- **A4. Frase parecida.** «Buenas noches» sin «Jarvis» no alcanza el umbral y se ignora.
- **A5. Salir desde la bandeja o fin de la sesión de Windows.** Se ejecutan los pasos 2 y 3 sin frase ni animación, y el proceso termina.
- **A6. El proceso termina de forma inesperada.** La sesión queda abierta en la base de datos; en el siguiente arranque se cierra como «interrumpida» y se aplican los pasos 2 y 3 (RN-47).

## Postcondiciones

Sesión con `closed_at` y motivo; asistente en `DORMIDO`; la ventana sigue visible con la caja de texto; sin trabajos programados.
