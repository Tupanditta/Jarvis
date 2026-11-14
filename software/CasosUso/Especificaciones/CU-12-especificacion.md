# CU-12. Atender un recordatorio

- **Actor principal:** ACT-01. **Secundario:** ACT-03.
- **Objetivo:** recibir el aviso de un recordatorio, leerlo y posponerlo o confirmarlo.
- **Requisitos:** RF-39 a RF-51, RF-70, RF-85, RN-13, RN-22 a RN-32, RN-39, RN-48, RN-50.
- **Módulo:** [Recordatorio](../../Modulos/Accion/recordatorio.md).

## Precondiciones

Existe al menos un recordatorio `activo` con una fecha de aviso. Sesión abierta.

## Disparador

Llega la fecha de aviso de un recordatorio (ACT-03).

## Flujo principal

1. El planificador dispara el aviso. El sistema lo marca como disparado y lo encola.
2. Cuando no hay diálogo, orden en curso ni locución, el sistema activa el panel numerado de recordatorios, con el recordatorio destacado, y dice «Tiene un recordatorio.», sin leer fechas (RN-23). Si estaba en reposo, pasa antes a escucha.
3. El usuario dice «Lee el recordatorio uno». El sistema lee su texto. No lo confirma (RN-24).
4. Si era su última fecha de aviso, al terminar la lectura empieza el plazo de 300 s (RN-29).
5. El usuario dice «Confirmar recordatorios uno». El sistema lo elimina (borrado lógico), actualiza el panel y dice «Recordatorio 1 confirmado.».

## Flujos alternativos

- **A1. Posponer** (tras el paso 2 o el 3): «Posponer» retrasa el aviso 10 minutos; «Posponer media hora», el tiempo dicho. El sistema dice «Pospuesto. Le avisaré dentro de {duración}.». La fecha límite no cambia. El plazo de autoconfirmación se cancela.
- **A2. Callar la lectura** (paso 3): mientras el asistente lee, el usuario dice «Hey Jarvis»; la lectura se corta y el usuario puede decir «posponer» (RF-47).
- **A3. Autoconfirmación** (paso 4): si pasan 300 s sin confirmar ni posponer, el recordatorio se elimina en silencio, aunque tenga una fecha límite futura.
- **A4. Confirmar con el panel inactivo** (paso 5): si el panel de recordatorios no es el activo, «Confirmar recordatorios» lo activa y el sistema dice «Diga confirmar recordatorios y el número.»; no confirma nada.
- **A5. Aviso sin sesión abierta:** no se dispara nada. Al abrir la siguiente sesión, tras «Sesión iniciada. Le escucho.», se ejecuta el paso 2 con todos los avisos pendientes agrupados: «Tiene {n} recordatorios.» (RN-22).
- **A6. Vence la fecha límite:** el sistema dice «El recordatorio {n} ha vencido. Su fecha límite era {fecha}.»; el recordatorio pasa a `vencido` y empieza el plazo de 300 s. Un recordatorio `vencido` no vuelve a avisar por voz; sigue en el panel hasta que se confirme.
- **A7. Posponer la fecha límite:** «Pospón la fecha límite del recordatorio uno hasta el viernes a las diez». Solo antes de que venza; después, «La fecha límite ya ha vencido y no se puede posponer.».
- **A8. Aviso durante un diálogo o una locución:** espera a que terminen (RN-39).
- **A9. Índice inexistente:** «No hay ningún elemento {n}.».
- **A10. Consulta a demanda:** «Muestra los recordatorios» activa el panel y dice cuántos hay. «Elimina el recordatorio {n}» lo elimina tras confirmación.
- **A11. Cierre de sesión durante el plazo de 300 s:** el plazo se pierde; el recordatorio sigue visible en la siguiente sesión.

## Postcondiciones

El recordatorio queda `activo` (pospuesto o pendiente de otros avisos), `vencido` o `eliminado`. Ninguna fila se borra físicamente.
