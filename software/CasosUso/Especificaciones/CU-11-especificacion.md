# CU-11. Crear un recordatorio

- **Actor principal:** ACT-01.
- **Objetivo:** guardar un recordatorio con una o varias fechas de aviso y, si se quiere, una fecha límite.
- **Requisitos:** RF-35 a RF-38, RF-66, RF-67, RF-72, RN-20, RN-21, RN-37, RN-38, RES-14, RES-25, RES-26, RES-35.
- **Módulo:** [Recordatorio](../../Modulos/Accion/recordatorio.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario escribe «Recuérdame que tengo que llamar a Ana mañana a las nueve».

## Flujo principal

1. El sistema identifica `recordatorio.crear`; el patrón separa el prefijo «recuérdame que».
2. El sistema encuentra al final del texto la fecha «mañana a las nueve»: es la primera fecha de aviso. El texto restante, «tengo que llamar a Ana», se convierte en «Tienes que llamar a Ana» (RN-20).
3. El sistema pasa a `AWAITING_PARAMETER` y pregunta «¿Quiere añadir otro aviso o una fecha límite?».
4. El usuario escribe «No».
5. El sistema guarda el recordatorio y su aviso, lo programa y dice «Recordatorio creado para mañana a las nueve.». El panel de recordatorios lo muestra.

## Flujos alternativos

- **A1. Sin fecha en la orden** (paso 2): «Recuérdame comprar pan». El sistema pregunta «¿Cuándo quiere que se lo recuerde?» y el usuario escribe una fecha («en dos horas»). Sigue en el paso 3. Si cancela o no responde, no se crea nada.
- **A2. Otro aviso** (paso 4): «Otro aviso el viernes a las diez». El sistema lo añade y repite la pregunta, hasta 5 avisos.
- **A3. Fecha límite** (paso 4): «Fecha límite el sábado a las doce». El sistema la fija y pasa al paso 5.
- **A4. Sin respuesta o «cancelar»** (paso 4): el recordatorio se guarda con lo que ya tiene; es la única excepción a la cancelación, porque la fecha obligatoria ya se dio.
- **A5. Fecha no entendida** (pasos 3 y 4, A1): «No he entendido la fecha.» y se repite la pregunta una vez.
- **A6. Fecha pasada:** «Esa fecha ya ha pasado.» y se repite la pregunta.
- **A7. Fecha límite anterior a un aviso:** «La fecha límite no puede ser anterior a un aviso.» y se repite la pregunta.
- **A8. Texto vacío** (paso 2): «Recuérdame mañana a las nueve» → `error`; «No he entendido qué quiere que le recuerde.».
- **A9. Desde un protocolo:** el texto, los avisos y la fecha límite vienen en los parámetros; no hay diálogo.

## Postcondiciones

Recordatorio en estado `activo` con sus avisos en la base de datos, con fechas en UTC, y programado mientras dure la sesión.
