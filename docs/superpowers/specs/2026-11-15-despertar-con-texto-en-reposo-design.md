# Despertar con cualquier texto en reposo — diseño corto

## Intención

En reposo (`IDLE`), el usuario ya no tiene que escribir «Hey Jarvis» antes de dar una orden.
Cualquier texto despierta al asistente y se procesa en el mismo envío como orden o tarea.

## Objetivos

- En `IDLE`, cualquier texto no vacío pasa a `LISTENING_COMMAND` y se atiende como en escucha.
- La orden se ejecuta sin que el asistente diga antes «Le escucho».

## No objetivos

- `DORMIDO` no cambia: abrir sesión sigue exigiendo «Hey Jarvis» o «Abrir sesión» en la bandeja.
- No cambian los umbrales ni las frases de control.

## Comportamiento en `IDLE`

| Texto | Resultado |
|-------|-----------|
| «Hey Jarvis» | Igual que antes: pasa a escucha y dice «Le escucho.» |
| «Buenas noches Jarvis» | Igual que antes: cierra la sesión. |
| «Gracias Jarvis», «cancelar» y sus variantes | Sin efecto: ya está en reposo y no hay turno que cancelar. |
| Intención reconocida (p. ej. «muestra la pantalla») | Despierta en silencio (`ListeningResumed(silent=True)`) y ejecuta la orden. |
| Texto no reconocido | Despierta en silencio y se muestra como no reconocido (`CommandReceived(recognized=False)`). |
| Texto vacío o solo espacios | Se descarta, como hoy. |

Tras despertar, la cuenta de inactividad se reinicia como en cualquier turno de escucha.

Decisiones tomadas al planificar (se pueden corregir):

- Una frase parecida a «Buenas noches Jarvis» que alcanza `control_threshold` (80) pero no
  `idle_closing_threshold` (85) no cierra en reposo: cuenta como texto no reconocido y despierta.
- «Buenas noches» sin «Jarvis» en reposo despierta como texto no reconocido (antes se ignoraba).
- El texto de ayuda de la caja en reposo pasa de «En reposo. Escriba «Hey Jarvis»» a
  «En reposo. Escriba una orden».

## Enfoques

- **Elegido: el router enruta en `IDLE` como en escucha y la FSM despierta antes de aplicar la
  entrada.** En `_resting`, `IntentMatched` y `NoMatch` pasan a `LISTENING_COMMAND`, emiten
  `PublishListeningResumed(silent=True)` y después los efectos de `_listening`. Reutiliza el
  despertar silencioso que ya existe para los avisos.
- **Descartado: el orquestador inyecta un `WakeWord` antes del texto.** Haría decir «Le escucho»
  encima de la respuesta y repartiría la regla entre el orquestador y la FSM.
- **Descartado: una entrada nueva en la FSM (`TextInIdle`).** Duplica `IntentMatched` y `NoMatch`
  sin aportar nada.

## Restricciones

- El router sigue siendo código puro; la FSM sigue siendo la única dueña del estado.
- Actualizar la spec `2026-11-14-entrada-por-texto-design.md` (la regla «en reposo cualquier otro
  texto se descarta» y la nota equivalente más abajo).

## Lo que decide quien lo construya

- Cómo se factoriza en el router la rama común de `IDLE` y escucha.
- Los nombres y la organización de las pruebas nuevas.
