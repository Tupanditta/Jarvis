# CU-10. Gestionar la sesión y el historial

- **Actor principal:** ACT-01.
- **Objetivo:** nombrar la sesión, marcar su importancia, consultar el historial y eliminar una sesión.
- **Requisitos:** RF-03 a RF-14, RF-72, RNF-12, RN-02 a RN-12, RN-53.
- **Módulos:** [Sesión](../../Modulos/Accion/sesion.md), [Historial](../../Modulos/Accion/historial.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Flujo principal: nombre, importancia y consulta

1. El usuario escribe «Llama a la sesión práctica de redes». El sistema fija el nombre, lo marca como fijado por el usuario y dice «Sesión renombrada a práctica de redes.».
2. El usuario escribe «Marca la sesión como importante». El sistema la marca y dice «Sesión marcada como importante.». La barra superior muestra la estrella.
3. El usuario escribe «Muestra el historial». El sistema muestra hasta 10 sesiones, primero las importantes y de la más reciente a la más antigua, con su identificador, y dice «Hay {n} sesiones en el historial.».
4. El usuario escribe «Actividades de la sesión doce». El sistema muestra sus actividades y dice «La sesión {nombre} tiene {n} actividades.».

## Flujo secundario: eliminar una sesión

1. El usuario escribe «Elimina la sesión doce».
2. El sistema muestra esa sesión, pasa a `AWAITING_CONFIRMATION` y pregunta «¿Elimino la sesión 12, {nombre}?».
3. El usuario escribe «Sí».
4. El sistema la marca como eliminada (borrado lógico) y dice «Sesión 12 eliminada.». Ya no aparece en el historial.

## Flujos alternativos

- **A1. Desbordamiento** (paso 2 del flujo principal): ya hay 10 sesiones importantes. El sistema dice «Se incorpora una nueva sesión importante. La sesión {nombre} deja de serlo y se eliminará al cerrar.». La más antigua pasa a no importante y queda marcada (RN-08). Se elimina al cerrar la sesión actual (CU-05).
- **A2. Restauración:** si, antes de cerrar, el usuario escribe «La sesión no es importante», la sesión desplazada recupera su importancia.
- **A3. Actividades de la sesión actual:** «Qué he hecho» muestra las de la sesión en curso.
- **A4. Identificador inexistente** (flujo secundario, paso 1): `error`; «No existe la sesión {id}.».
- **A5. Es la sesión actual:** `error`; «No se puede eliminar la sesión actual.».
- **A6. El usuario escribe «No», «cancelar», o no responde en 20 s** (paso 3): no se elimina; «Operación cancelada.».
- **A7. Respuesta no válida** (paso 3): «No le he entendido.» y se repite la pregunta una vez; a la segunda, se cancela.

## Postcondiciones

Los cambios quedan guardados en la base de datos. Una sesión eliminada conserva su fila (RNF-12).
