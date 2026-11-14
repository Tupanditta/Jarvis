# CU-13. Ejecutar un protocolo

- **Actor principal:** ACT-01.
- **Objetivo:** lanzar con una sola orden una secuencia predefinida de tareas de varios módulos.
- **Requisitos:** RF-52 a RF-57, RF-99, RNF-14, RNF-19, RN-03 a RN-08, RN-33 a RN-36, RN-55, RES-36.
- **Módulos:** [Protocolos](../../Modulos/Accion/protocolos.md), [Sesión](../../Modulos/Accion/sesion.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`. El protocolo está definido en `protocols.toml`.

## Disparador

El usuario dice «Protocolo modo trabajo».

## Flujo principal

1. El sistema identifica `protocolos.ejecutar` y encuentra el protocolo por su nombre.
2. El sistema abre el panel del protocolo con todas sus tareas en `pendiente` y dice «Iniciando el protocolo modo trabajo.».
3. El nombre de la sesión no lo ha fijado el usuario: el sistema pasa a `AWAITING_CONFIRMATION` y pregunta «¿Quiere llamar a esta sesión modo trabajo?». El usuario dice «Sí» y la sesión toma ese nombre.
4. El protocolo es importante: la sesión pasa a importante (RN-36).
5. El sistema ejecuta las tareas en orden, cada una con la interfaz común de su módulo. El estado de cada una cambia en el panel en cuanto se produce, sin frases intermedias.
6. Al terminar, el sistema dice «Protocolo modo trabajo completado.». Cada tarea queda registrada como actividad de la sesión.

## Flujos alternativos

- **A1. Nombre fijado por el usuario** (paso 3): no se pregunta y el nombre no cambia (RN-03).
- **A2. El usuario dice «No» o no responde** (paso 3): el nombre no cambia; el protocolo continúa.
- **A3. Desbordamiento de sesiones importantes** (paso 4): CU-10, A1.
- **A4. Una tarea falla** (paso 5): queda en `error`, el sistema dice su motivo y continúa con la siguiente. Al final: «Protocolo modo trabajo terminado con {n} errores.».
- **A5. Una tarea con `stop_on_error` falla:** las restantes quedan en `error`, «protocolo detenido».
- **A6. Una tarea necesita un diálogo** (p. ej. una colisión de nombre): se formula cuando le llega el turno y el protocolo espera la respuesta (RN-35).
- **A7. «Cancelar» durante la ejecución:** se cancela la tarea en curso y las restantes quedan en `error`, «cancelada».
- **A8. Protocolo no encontrado** (paso 1): `error`; «No encuentro {nombre}.».
- **A9. Listar:** «Qué protocolos hay» los muestra y dice cuántos son.

## Postcondiciones

Tareas ejecutadas en orden; sesión renombrada o marcada según las reglas; actividades registradas con el protocolo como tarea padre.
