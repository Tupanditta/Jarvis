# Transcriptor (STT)

- **Código:** `transcriber/`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Convertir en texto cada orden y cada respuesta habladas, en español, sin conexión (RF-62, RES-11), con la precisión que exige RNF-31.

## Comportamiento

| Aspecto | Decisión |
|---|---|
| Motor | `faster-whisper`, modelo `small` ⚙, `compute_type="int8"`, `device="cpu"`. |
| Idioma | `language="es"`, sin detección automática. |
| Decodificación | `beam_size=3` ⚙ para órdenes; `beam_size=1` para los segmentos restringidos del reposo. `condition_on_previous_text=False`, `vad_filter=False` (la segmentación ya está hecha), `temperature=0`. |
| Hilos | `cpu_threads = min(4, núcleos físicos − 1)` ⚙, mínimo 1. El hilo del ejecutor baja su prioridad. |
| Carga | Al abrir la sesión, en el ejecutor STT, en paralelo con la animación de despertar. Se libera al cerrar la sesión. En reposo sigue cargado. |
| Orden antes de terminar la carga | Espera a la carga; no se pierde. |
| Ejecución | `await transcribe(pcm)` desde el núcleo; el trabajo corre en el ejecutor STT (1 hilo), así que las transcripciones son secuenciales. |

### Indicación inicial de vocabulario

`vocabulary.py` genera el texto de `initial_prompt` para que el modelo reconozca nombres propios y términos técnicos. Es una función pura: los mismos términos de entrada dan siempre el mismo texto.

El vocabulario sigue al contexto. El orquestador lo recalcula y llama a `set_vocabulary`:

- al abrir cada sesión,
- cuando cambia el directorio de trabajo (`WorkdirChanged`), y
- al empezar y al terminar un diálogo.

Contenido, en orden de prioridad:

1. Frases fijas: «Jarvis, Gracias Jarvis, Buenas noches Jarvis».
2. Durante un diálogo: las respuestas admitidas de su pregunta.
3. Nombres de las subcarpetas y de los archivos del directorio de trabajo: carpetas primero, orden alfabético, sin los ocultos, hasta 30 ⚙ (`stt.vocabulary_workdir_entries`). Es lo que el usuario dicta con más probabilidad en una ruta o en un nombre.
4. Nombres de los protocolos.
5. Nombres de los lugares con nombre.
6. Nombres del catálogo de aplicaciones y de páginas.
7. Binarios permitidos (`git`, `gcc`, `python`…).
8. Aplicaciones descubiertas del sistema.

Los términos se unen con comas. Si el texto supera 600 caracteres ⚙, se recorta por el final, de modo que se pierden primero los de menor prioridad.

La indicación orienta al modelo, no lo obliga. La fiabilidad de rutas, nombres y comandos descansa en tres capas: esta indicación, los alias de la configuración y la resolución difusa contra las carpetas, los catálogos y los binarios reales ([enrutador-intenciones.md](enrutador-intenciones.md), secciones 4 y 6).

### Filtro de resultados

Whisper puede inventar texto con ruido o silencio. Se devuelve texto vacío cuando:

- la probabilidad de «sin voz» del segmento supera 0,6 ⚙, o
- el texto normalizado coincide con la lista de frases espurias conocidas de `transcriber/` (p. ej. «subtítulos realizados por la comunidad de amara.org», «gracias por ver el vídeo»), o
- el texto normalizado reproduce la propia indicación de vocabulario: tres o más de sus términos seguidos y en el mismo orden. Con ruido, el modelo tiende a repetir la indicación.

Un texto vacío se trata como frase no reconocida (RN-51).

## Interfaz

```python
class Transcriber(Protocol):
    async def load(self) -> None: ...
    def unload(self) -> None: ...
    async def transcribe(self, pcm: np.ndarray, *, restricted: bool = False) -> str: ...
    def set_vocabulary(self, terms: Sequence[str]) -> None: ...
```

## Privacidad

El texto transcrito solo se escribe en el registro de diagnóstico en nivel `DEBUG` (RES-48).

## Ampliación prevista (posterior a la versión 1)

**Segunda pasada precisa para órdenes con entidades dictadas.** Si, tras el uso real de la fase 7, las órdenes con rutas, nombres o comandos no alcanzan RNF-31, la respuesta prevista es transcribir de nuevo, con un modelo mayor de `faster-whisper` (`large-v3-turbo`, `int8`), solo las órdenes cuyo patrón tiene un hueco `DIR_PATH`, `NEW_NAME`, `NEW_PATH` o `COMMAND_LINE`. Es gratuito y local.

- **Por qué no está en la versión 1:** añade entre 2 y 4 s a esas órdenes y cerca de 1 GB de RAM, fuera de RNF-03 y RNF-05, y no se sabe todavía si hace falta.
- **Por qué cabe sin rediseñar:** el transcriptor está detrás del protocolo `Transcriber`; el modelo es configuración (`stt.model`); el orquestador ya conoce el patrón elegido antes de ejecutar. Basta un segundo `Transcriber` y una regla en el orquestador. El enrutador, los módulos y la interfaz no cambian.
- **Qué habría que actualizar:** RES-11, RES-46, RNF-03, RNF-05 y `fetch_models.py`.

## Criterios de aceptación

- `vocabulary`: orden de prioridad, límite de entradas del directorio de trabajo y recorte, con pruebas unitarias.
- El vocabulario se recalcula al abrir sesión, con `WorkdirChanged` y al empezar y terminar un diálogo (prueba de integración con un transcriptor falso).
- Filtro de frases espurias y de eco de la indicación, con pruebas unitarias.
- Con el modelo real (marcador `models`): `gracias_jarvis.wav` y `buenas_noches_jarvis.wav` producen un texto que el enrutador acepta; `control_silencio.wav` y `control_ruido.wav` producen texto vacío o no reconocido.
- Latencia dentro de RNF-03 en el equipo de referencia.
- RNF-31 medido con la lista manual de órdenes habladas.

## Prohibiciones

- No se usa ningún servicio en red ni GPU.
- No se usa `vosk`.
- No se guarda el audio.
