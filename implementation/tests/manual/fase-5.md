# Lista manual de la fase 5. Recordatorios

Se recorre en el equipo de referencia al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`; no debe contener el texto
de ningún recordatorio (RES-48).

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `--preview` muestra el panel de recordatorios: tres filas numeradas, el segundo destacado
      (fondo `bg.raised`, borde `primary`) y el tercero con el distintivo «vencido».
- [ ] La ventana «Recordatorios» se abre desde el dock y su botón de actualizar dice cuántos hay.

## Crear (CU-11)

- [ ] «Recuérdame que tengo que llamar a Ana mañana a las nueve»: pregunta «¿Quiere añadir otro
      aviso o una fecha límite?»; «No»: «Recordatorio creado para mañana a las 9.». El panel
      muestra «Tienes que llamar a Ana» con su próximo aviso.
- [ ] «Recuérdame comprar pan»: pregunta cuándo. «patata»: «No he entendido la fecha.» y la
      pregunta otra vez. «En dos horas»: sigue con la pregunta de más avisos.
- [ ] «Otro aviso el viernes a las diez» añade un aviso y repite la pregunta; «fecha límite el
      sábado a las doce» la fija y termina.
- [ ] Ante la pregunta de más avisos, «cancelar» y 20 s sin respuesta: el recordatorio se guarda
      y **no** se dice «Operación cancelada.».
- [ ] Una fecha pasada («hoy a las 8» por la tarde): «Esa fecha ya ha pasado.» y la pregunta
      otra vez. Una fecha límite anterior a un aviso: «La fecha límite no puede ser anterior a un
      aviso.».
- [ ] «Recuérdame mañana a las nueve»: «No he entendido qué quiere que le recuerde.».

## De principio a fin

- [ ] **Un recordatorio «en un minuto»:** «Recuérdame regar las plantas en un minuto», «no».
      Al minuto: el panel se activa con el recordatorio destacado y la voz dice «Tiene un
      recordatorio.», sin texto ni fecha. «Lee el recordatorio uno» lo lee y no lo confirma.
      Sin hacer nada, a los 5 minutos desaparece del panel (autoconfirmación).
- [ ] Con el panel de comandos activo, «Confirmar recordatorios uno» solo activa el panel y dice
      «Escriba confirmar recordatorios y el número.». Repetido, lo confirma.
- [ ] Dos recordatorios para el mismo minuto: un solo aviso «Tiene 2 recordatorios.».
- [ ] **Posponer interrumpiendo la lectura:** mientras lee un recordatorio, escribir «Hey
      Jarvis»: calla. «Posponer»: «Pospuesto. Le avisaré dentro de 10 minutos.» y vuelve a avisar
      a los 10 minutos. «Posponer media hora» usa esa duración.
- [ ] En reposo («Gracias Jarvis»), un aviso que vence pone al asistente en escucha y se dice.
- [ ] Un aviso que vence durante una pregunta se dice después de responderla.
- [ ] Fecha límite: «Recuérdame pagar en un minuto», «fecha límite en dos minutos». A los dos
      minutos: «El recordatorio 1 ha vencido. Su fecha límite era hoy a las …»; el distintivo
      «vencido» aparece. Antes de vencer, «Pospón la fecha límite del recordatorio uno hasta
      mañana» la cambia; después, «La fecha límite ya ha vencido y no se puede posponer.».
- [ ] «Elimina el recordatorio uno» pregunta; «sí» lo elimina; «no» lo deja.
- [ ] «Lee el recordatorio 9» con menos recordatorios: «No existe ningún elemento con el número 9».

## Sin sesión (RN-22)

- [ ] **Vence con el asistente dormido:** crear uno «en dos minutos» y cerrar la sesión. Pasados
      los dos minutos no se dice nada. Al abrir la sesión, tras la frase de apertura: «Tiene un
      recordatorio.».
- [ ] Una fecha límite que vence sin sesión se avisa al abrir la siguiente, y el recordatorio
      vencido no vuelve a avisar en sesiones posteriores.
- [ ] Cerrar la sesión durante el plazo de 5 minutos tras leer un recordatorio: en la siguiente
      sesión sigue en el panel.
- [ ] En la base de datos, los confirmados y eliminados tienen `status = 'eliminado'`; ninguna
      fila se ha borrado.
