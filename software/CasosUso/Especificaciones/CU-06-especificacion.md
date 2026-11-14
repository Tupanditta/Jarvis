# CU-06. Ejecutar un binario externo

- **Actor principal:** ACT-01. **Secundario:** ACT-04.
- **Objetivo:** ejecutar un programa permitido en el directorio de trabajo y conocer su resultado.
- **Requisitos:** RF-15, RF-19, RF-20, RF-69, RF-71, RNF-07, RNF-27, RN-14, RN-16, RN-39, RN-45, RES-29.
- **Módulo:** [Comandos](../../Modulos/Accion/comandos.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`. El directorio de trabajo es el deseado (p. ej. tras «Ve a proyectos barra jarvis»).

## Disparador

El usuario dice «Ejecuta {comando}», p. ej. «Ejecuta gcc main punto c».

## Flujo principal

1. El sistema identifica `comandos.ejecutar`. La primera palabra, tras aplicar los alias, es un binario de la lista permitida; el resto son sus argumentos.
2. El sistema crea la tarea en `pendiente`, dice «Ejecutando {comando}.» y lanza el programa, sin intérprete de órdenes, en el directorio de trabajo.
3. El sistema sigue escuchando órdenes mientras el programa se ejecuta (RNF-07). La salida aparece en el panel de comandos según se produce.
4. El programa termina con código 0. La tarea pasa a `completado`.
5. Cuando no hay un diálogo ni una locución en curso, el sistema avisa: «{comando} ha terminado correctamente.» (RN-39).

## Flujos alternativos

- **A1. Código de retorno distinto de 0** (paso 4): la tarea pasa a `error`; el aviso es «{comando} ha fallado.». La salida de errores queda visible en el panel.
- **A2. Binario no permitido** (paso 1): `error`; «Ese comando no está permitido.». No se ejecuta nada.
- **A3. Programa no encontrado** (paso 2): `error`; «No encuentro el programa {nombre}.».
- **A4. Tiempo agotado:** a los 120 s el sistema termina el programa; `error`; «El comando ha tardado demasiado.».
- **A5. Ya hay un binario en ejecución** (paso 2): `error`; «Ya hay un comando en ejecución.».
- **A6. «Cancelar» inmediatamente después de lanzarlo, o cierre de sesión:** el programa se termina; `error`.
- **A7. Dentro de un protocolo:** el programa se espera en línea y su resultado es el de la tarea del protocolo (CU-13).

## Postcondiciones

Actividad registrada con su estado final; salida visible en el panel de comandos. El directorio de trabajo no cambia.
