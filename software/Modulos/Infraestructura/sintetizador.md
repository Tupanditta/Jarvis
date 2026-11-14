# Sintetizador de voz (TTS)

- **Código:** `speaker/`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Decir las respuestas del asistente con una voz neuronal local de español de España, a partir de frases estáticas parametrizadas (RES-15, RES-27).

## Comportamiento

### Frases

- Todas las frases están en un catálogo único, `speaker/phrases.py`: un identificador y una plantilla con parámetros (`"comandos.cd.ok": "Directorio cambiado a {carpeta}."`). No hay generación libre de texto.
- Los módulos nunca escriben texto de voz: devuelven `Phrase(id, params)`.
- El asistente trata al usuario de usted.
- `phrases.py` incluye formateadores para decir valores de forma natural: fechas («mañana a las nueve y media», «el cinco de diciembre a las doce»), duraciones («dentro de diez minutos»), recuentos con singular y plural («1 carpeta», «3 carpetas»).
- Una prueba comprueba que cada identificador usado en el código existe en el catálogo y recibe todos sus parámetros.

### Síntesis

- `piper-tts` con la voz `es_ES-davefx-medium`, cargada al arrancar el proceso.
- La síntesis corre en el ejecutor TTS (1 hilo).
- Las cuatro frases del ciclo de vida y las frases sin parámetros más usadas se sintetizan al arrancar y se guardan en memoria. El resto se sintetiza al decirse y se guarda en una caché en memoria de 64 ⚙ entradas.

### Reproducción

- Un flujo de salida de `sounddevice` en el dispositivo de salida predeterminado, a la frecuencia de la voz. Se abre al abrir la sesión, antes de la frase de apertura, y se cierra cuando termina la frase de cierre; en modo dormido no hay ningún flujo de salida abierto.
- **Cola de locuciones:** las frases se dicen de una en una, en orden. `await say(phrase)` termina cuando la frase acaba de sonar o se interrumpe.
- **Nivel:** el callback de salida calcula el nivel del bloque que reproduce; el núcleo lo publica como `AudioLevel(source="assistant")` (RF-83).
- **Fallo del dispositivo de salida:** se registra, la frase se da por dicha tras su duración nominal y el asistente sigue funcionando; el texto se ve en los subtítulos.

### Sincronía con la animación (RNF-22)

Para una frase del ciclo de vida, el `speaker` publica el evento de la transición en el mismo instante en que entrega el primer bloque de audio al flujo de salida. Como esas frases ya están sintetizadas, no hay espera entre la decisión y el sonido.

### Interrupción (RN-48, RF-70)

| Tipo de locución | Modo de captura mientras suena | Se interrumpe con |
|---|---|---|
| Frase del ciclo de vida | `MUTED` | Nada. |
| Cualquier otra | `WAKE_ONLY` | «Hey Jarvis», el botón de silencio de la interfaz, o un cierre de sesión. |

Al interrumpir: el audio se corta con un fundido de 30 ms, se vacía la cola de locuciones y se publica `SpeechFinished(interrupted=True)`. Al terminar cualquier locución, la captura se reabre tras 0,3 s ([captura-audio.md](captura-audio.md)).

### Repetir (RF-94)

El `speaker` guarda la última frase dicha que no sea del ciclo de vida. «Repite» la vuelve a decir.

## Interfaz

```python
class Speaker:
    async def preload(self) -> None: ...
    async def say(self, phrase: Phrase, *, lifecycle: bool = False,
                  on_start: Callable[[], None] | None = None) -> SpeechOutcome: ...
    def stop(self) -> None: ...                  # interrumpe y vacía la cola
    def current_level(self) -> float: ...
    @property
    def last_phrase(self) -> Phrase | None: ...
```

## Criterios de aceptación

- Con un sintetizador y un reproductor falsos: orden de la cola, interrupción, cambio de modo de captura al inicio y al fin, `on_start` llamado al empezar el audio.
- Todas las frases del catálogo se renderizan con parámetros de ejemplo sin error.
- Formateadores de fechas, duraciones y plurales con pruebas unitarias.
- Con el modelo real (marcador `models`): la síntesis de una frase corta tarda menos de 0,5 s en el equipo de referencia.

## Prohibiciones

- No se genera texto libre.
- No se usa ningún servicio en red.
- Ningún módulo de acción llama a Piper ni al reproductor directamente.
