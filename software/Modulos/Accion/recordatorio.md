# Módulo de acción: Recordatorio

- **Código:** `action_modules/reminder_manager.py`. Nombre de módulo: `recordatorio`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Crear recordatorios con una o varias fechas de aviso y una fecha límite opcional, notificarlos, posponerlos y confirmarlos.

## Acciones

| Acción | Parámetros | Efecto |
|---|---|---|
| `crear` | `texto: TEXT` (por voz); `texto`, `avisos`, `limite` (en protocolos) | Crea un recordatorio (RF-35 a RF-38). |
| `mostrar` | — | Activa el panel de recordatorios y dice cuántos hay (RF-51). |
| `leer` | `n: INTEGER` | Lee el texto del recordatorio *n* (RF-42). No confirma (RN-24). |
| `confirmar` | `n: INTEGER` (opcional) | Confirma el recordatorio *n* (RF-43, RF-44). |
| `posponer` | `n: INTEGER` (opcional), `duracion: DURATION` (opcional) | Pospone el aviso (RF-45 a RF-47). |
| `posponer_limite` | `n: INTEGER`, `fecha: DATETIME` | Pospone la fecha límite (RF-48). |
| `eliminar` | `n: INTEGER` | Elimina el recordatorio *n* tras confirmación (RF-51). |

Todas activan el panel de recordatorios. En protocolos solo se admiten `crear` y `mostrar`.

## Reglas

### Texto (RN-20)

1. El patrón del enrutador ya ha separado el prefijo disparador («recuérdame», «recuérdame que», «crea un recordatorio para»…).
2. Sustituciones cerradas al inicio del texto: «tengo que» → «Tienes que»; «debo» → «Debes»; «tenemos que» → «Tenéis que».
3. El resto se conserva intacto; la primera letra, en mayúscula. Sin reglas de conjugación (RES-26).

### Creación por voz

1. Se busca una expresión de fecha al final del texto (`datetimes.find_suffix`). Si la hay, es la primera fecha de aviso y se quita del texto. Ejemplo: «recuérdame llamar a Ana mañana a las 9» → texto «Llamar a Ana», aviso mañana a las 9:00.
2. Si el texto queda vacío: `error`, «No he entendido qué quiere que le recuerde.».
3. Si no hay fecha: se pregunta (`DATETIME`) «¿Cuándo quiere que se lo recuerde?». Si se cancela o vence, no se crea nada.
4. Se pregunta (`REMINDER_ACTION`) «¿Quiere añadir otro aviso o una fecha límite?». Respuestas:
   - «otro aviso {fecha}»: se añade y se vuelve a preguntar, hasta 5 ⚙ avisos.
   - «fecha límite {fecha}»: se fija y termina el diálogo.
   - una negación, «cancelar» o el vencimiento del tiempo: termina el diálogo **y el recordatorio se guarda** con lo que ya tiene. Es la única excepción a «cancelar no hace nada», porque la fecha obligatoria ya se dio.
5. Validación (RN-21): todas las fechas futuras; la fecha límite no anterior a ningún aviso. Una fecha no válida se rechaza con su motivo y se repite la pregunta.
6. Se guarda en una transacción (recordatorio y avisos), se programan los avisos y se dice la confirmación con la primera fecha.

### Programación (RES-14)

- `APScheduler` (`AsyncIOScheduler`) en el bucle del núcleo, con su almacén en memoria. La base de datos es la única fuente de verdad.
- Trabajos, con identificador estable: `trigger:{id}` por cada fecha de aviso no disparada; `deadline:{id}` por cada fecha límite de un recordatorio `activo`; `autoconfirm:{id}` para la autoconfirmación.
- **Al abrir la sesión** (`on_session_opened`):
  1. avisos con `is_fired = 0` y fecha ya pasada de recordatorios `activo` → se disparan juntos, en un solo aviso;
  2. recordatorios `activo` con fecha límite ya pasada → aviso de vencimiento y paso a `vencido`;
  3. se programan los avisos y las fechas límite futuros.
- **Al cerrar la sesión** (`on_session_closed`): se eliminan todos los trabajos. Sin sesión no se dispara nada (RN-22).

### Notificación

Cuando vence un aviso:

1. `is_fired = 1`.
2. Se encola un aviso en la cola de avisos (RN-39). Varios avisos simultáneos se agrupan en uno.
3. Al entregarse: se activa el panel numerado, con los recordatorios notificados destacados, y el asistente dice «Tiene un recordatorio.» o «Tiene N recordatorios.». No lee fechas ni textos (RN-23).

Cuando vence una fecha límite: el asistente dice «El recordatorio {n} ha vencido. Su fecha límite era {fecha}.», y el recordatorio pasa a `vencido` (RN-31). Un recordatorio `vencido` no vuelve a avisar por voz.

### Panel e índices

El panel muestra los recordatorios `activo` y `vencido`, ordenados por identificador, numerados del 1 al *n*. El índice que dice el usuario es esa posición (RN-50).

### Leer, confirmar, posponer

- **Leer:** dice el texto; si está vencido, añade su fecha límite. No cambia nada (RN-24). Interrumpible con «Hey Jarvis» (RN-48).
- **Confirmar (RN-25):** si el panel de recordatorios no es el panel activo, «Confirmar recordatorios» lo activa y dice «Diga confirmar recordatorios y el número.», sin confirmar nada, aunque se haya dicho un índice. Con el panel activo y un índice: el recordatorio pasa a `eliminado` (RN-26).
- **Posponer aviso (RN-27):** sin índice, se aplica al último recordatorio notificado o leído. El último aviso disparado de ese recordatorio se reprograma a ahora + 10 minutos ⚙ (o la duración dicha) con `is_fired = 0`. Se cancela su autoconfirmación. Voz: «Pospuesto. Le avisaré dentro de {duración}.». No cambia la fecha límite. Si el recordatorio aún no ha avisado: `error`, «Ese recordatorio aún no ha avisado.».
- **Posponer fecha límite (RN-28):** solo si el recordatorio tiene fecha límite, está `activo` y esa fecha no ha pasado. La nueva debe ser futura y no anterior a los avisos pendientes. Si ya venció: `error`, «La fecha límite ya ha vencido y no se puede posponer.».
- **Eliminar:** pregunta (`BOOLEAN`); con un sí, pasa a `eliminado`.

### Autoconfirmación (RN-29, RN-30, RN-32)

- Empieza un plazo de 300 s ⚙ cuando el asistente termina de **leer** un recordatorio que no tiene avisos pendientes (era su última fecha de aviso) o que está `vencido`, y cuando termina de **avisar del vencimiento** de una fecha límite.
- Si en ese plazo el usuario lo confirma o lo pospone, el plazo se cancela.
- Al cumplirse: el recordatorio pasa a `eliminado`, en silencio, y el panel se actualiza. Se aplica aunque tenga una fecha límite futura.
- Si la sesión se cierra durante el plazo, el plazo se pierde: el recordatorio sigue visible y se elimina al confirmarlo o al cumplirse un plazo nuevo tras otra lectura.
- Un recordatorio con todos sus avisos disparados y fecha límite futura sigue `activo` y avisará al llegar la fecha límite (RN-32).

### Borrado lógico (RN-13)

Eliminar es `status = 'eliminado'`. Las filas de `reminder_triggers` no se tocan.

## Datos

Tablas `reminders` y `reminder_triggers`, mediante `ReminderRepository`.

## Eventos

`RemindersChanged` (lista completa, tras cada cambio), `PanelActivated`.

## Criterios de aceptación

Con reloj falso, planificador controlado y base de datos en memoria:

- Extracción del texto y de la fecha final; sustituciones de RN-20.
- Diálogo de creación: sin fecha, con otro aviso, con fecha límite, con negación, con tiempo agotado (se guarda), fechas no válidas.
- Aviso con sesión abierta; aviso sin sesión entregado al abrir la siguiente; avisos simultáneos agrupados.
- Vencimiento de la fecha límite con y sin sesión; un `vencido` no vuelve a avisar.
- Leer no confirma. Confirmar con el panel inactivo solo lo activa.
- Posponer aviso con y sin índice y con duración; posponer fecha límite antes y después de vencer.
- Autoconfirmación a los 300 s; cancelada al confirmar o posponer; perdida al cerrar la sesión.
- Ningún `DELETE`.

## Prohibiciones

- No se usan reglas de conjugación verbal.
- Leer un recordatorio no lo confirma ni lo elimina.
- Posponer un aviso no cambia la fecha límite.
- No se puede posponer una fecha límite ya vencida.
- Un recordatorio `vencido` no vuelve a avisar por voz.
- No se usa `DELETE` físico ni se guardan recordatorios fuera de la base de datos.
