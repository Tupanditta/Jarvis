# CU-10. Gestionar la sesión y el historial

- **Actor principal:** ACT-01.
- **Objetivo:** nombrar la sesión, marcar su importancia, consultar el historial y eliminar sesiones.
- **Requisitos:** RF-03 a RF-14, RF-72, RF-118, RNF-12, RN-02 a RN-12, RN-53, RN-69.
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
4. El sistema la borra con sus actividades, renumera las sesiones posteriores (la 13 pasa a ser la 12, y así sucesivamente) y dice «Sesión 12 eliminada.». El historial se actualiza con los ids nuevos.

## Flujos alternativos

- **A1. Desbordamiento** (paso 2 del flujo principal): ya hay 10 sesiones importantes. El sistema dice «Se incorpora una nueva sesión importante. La sesión {nombre} deja de serlo y se eliminará al cerrar.». La más antigua pasa a no importante y queda marcada (RN-08). Se elimina al cerrar la sesión actual (CU-05).
- **A2. Restauración:** si, antes de cerrar, el usuario escribe «La sesión no es importante», la sesión desplazada recupera su importancia.
- **A3. Actividades de la sesión actual:** «Qué he hecho» muestra las de la sesión en curso.
- **A4. Identificador inexistente** (flujo secundario, paso 1): `error`; «No existe la sesión {id}.».
- **A5. Es la sesión actual:** `error`; «No se puede eliminar la sesión actual.».
- **A6. El usuario escribe «No», «cancelar», o no responde en 20 s** (paso 3): no se elimina; «Operación cancelada.».
- **A7. Respuesta no válida** (paso 3): «No le he entendido.» y se repite la pregunta una vez; a la segunda, se cancela.
- **A8. Varias sesiones** (flujo secundario, paso 1): el usuario escribe «Elimina sesiones». El sistema muestra el historial y pregunta «¿Qué sesiones elimino? Puede decirme, por ejemplo, 1, 3, 5 o 1-5.» (`SESSION_IDS`). Con «1-3», muestra esas sesiones; si alguna es importante, lo dice («Atención: hay importancia marcada en …»); pregunta «¿Elimino las sesiones 1, 2 y 3?» y, con un sí, las borra, renumera y dice «Sesiones 1, 2 y 3 eliminadas.». A4 y A5 se aplican a cada id elegido.
- **A9. Solo está la sesión actual** (A8): `error`; «No hay sesiones que eliminar. Solo está la actual.».

## Postcondiciones

Los cambios quedan guardados en la base de datos. Una sesión eliminada ya no está en ella, ni sus actividades, y los ids siguen siendo 1..N (RNF-12).
