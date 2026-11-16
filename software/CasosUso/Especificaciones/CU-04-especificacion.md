# CU-04. Pasar a reposo

- **Actor principal:** ACT-01.
- **Objetivo:** que el asistente deje de atender órdenes, manteniendo la sesión abierta.
- **Requisitos:** RF-76, RF-78, RF-79, RF-81, RF-83, RF-61, RF-62, RF-63, RF-65, RNF-04, RNF-11, RN-14, RN-43, RN-51, RN-52.
- **Módulos:** [Máquina de estados](../../Modulos/Infraestructura/maquina-estados.md), [Enrutador](../../Modulos/Infraestructura/enrutador-intenciones.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario escribe «Gracias Jarvis» y pulsa Enter.

## Flujo principal

1. La interfaz publica el texto y el orquestador lo entrega al enrutador.
2. El enrutador la reconoce como frase de control, comparando la frase completa (similitud ≥ 80).
3. El sistema pasa a `IDLE`. A la vez empiezan la animación de dormirse (2 s) y la frase «A su disposición.». El núcleo reacciona a la voz del asistente mientras suena.
4. Al terminar, la interfaz queda en su aspecto de reposo: orbe tenue y lento, sin reacción al audio; la caja de texto indica «En reposo. Escriba «Hey Jarvis»». La sesión, el directorio de trabajo y los recordatorios programados no cambian.
5. El sistema atiende solo «Hey Jarvis» (CU-03, A1) y «Buenas noches Jarvis» (CU-05, A1); cualquier otro texto se descarta.

## Flujos alternativos

- **A1. 120 s sin escribir.** Si pasan 120 s sin enviar texto ni teclear mientras escucha y no hay ninguna orden en curso, el sistema pasa a reposo igual que en los pasos 3 a 5.
- **A2. Frase parecida pero no igual.** «Muchas gracias Jarvis por todo» no alcanza el umbral: se muestra como no reconocida, sin frase del asistente, y reinicia la cuenta de 120 s (RN-51).
- **A3. «Gracias Jarvis» con una orden en curso.** La orden se cancela (su tarea queda en `error`, «cancelada») y se aplica el flujo principal. Un binario lanzado en segundo plano sigue ejecutándose.
- **A4. «Gracias Jarvis» durante un diálogo.** La operación en pausa se cancela y se aplica el flujo principal.
- **A5. Aviso de recordatorio en reposo.** El sistema vuelve a escucha, sin frase, para entregarlo (CU-12).

## Postcondiciones

Asistente en `IDLE`; sesión abierta. Consumo dentro de RNF-04.
