# Captura de audio y palabra de activación

- **Código:** `audio_capture/`, `scripts/calibrate_wakeword.py`, `scripts/diagnose_mic.py`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Escuchar el micrófono de forma continua y con bajo consumo, detectar «Hey Jarvis» de forma fiable con la voz del usuario (RNF-30), delimitar cada orden hablada y entregar su audio al núcleo, sin que ningún audio salga del dispositivo ni se guarde en disco (RNF-01, RES-48).

## Responsabilidades

1. Abrir y mantener el flujo del micrófono.
2. Detectar «Hey Jarvis» con `openwakeword` (RF-60).
3. Detectar voz con Silero VAD y segmentar las órdenes (RF-61).
4. Aplicar el modo de captura que fija el núcleo.
5. Medir el nivel del micrófono para la interfaz (RF-83).
6. Vigilar la salud de la señal (micrófono mudo, nivel) y dejar en el registro las trazas necesarias para calibrar.
7. Avisar de los 30 s sin voz no es suyo: lo cuenta el orquestador a partir de las órdenes que este módulo entrega.

## Formato de audio

16 kHz, mono, 16 bits, en bloques de 1280 muestras (80 ms), el tamaño que consume `openwakeword`.

- **Apertura:** primero se intenta abrir el dispositivo a 16 kHz. Si no lo admite, se abre a su frecuencia nativa y se remuestrea a 16 kHz con un filtro polifásico (`scipy.signal.resample_poly`), nunca descartando muestras sin filtrar.
- **Ganancia:** a cada bloque se le aplica la ganancia ⚙ `audio.input_gain` (1,0 por defecto; de 0,5 a 8), con saturación a 16 bits, antes de los detectores y de la transcripción. Su valor lo recomienda la calibración; el asistente no la ajusta solo.

## Modos de captura

El núcleo fija el modo; el hilo de audio lo lee en cada bloque.

| Modo | Cuándo | Palabra de activación | Detección de voz y segmentación |
|---|---|---|---|
| `WAKE_ONLY` | `DORMIDO`; y durante una locución interrumpible (RN-48). | Sí | No |
| `WAKE_AND_CLOSING` | `IDLE`. | Sí | Sí, restringida (ver abajo) |
| `COMMANDS` | `LISTENING_COMMAND` y `AWAITING_*`. | Sí | Sí |
| `MUTED` | Durante una frase del ciclo de vida. | No | No |

Al salir de `MUTED` o de la `WAKE_ONLY` de una locución, la captura se reabre 0,3 s ⚙ después del fin del audio reproducido, se descarta lo acumulado y se reinician los detectores (`openwakeword` y VAD), para no oír el eco de la propia voz.

## Detección de «Hey Jarvis»

- Modelo preentrenado `hey_jarvis` de `openwakeword`, con `onnxruntime` en CPU y 1 hilo.
- Se acepta con puntuación ≥ 0,5 ⚙ (`audio.wakeword_threshold`).
- Antirrebote: tras una detección, se ignoran las siguientes durante 1 s.
- Entrega `WakeWordDetected(at)` al núcleo.

El modelo está entrenado con voces en inglés. La frase se dice a la inglesa («jei YAR-vis»); una pronunciación muy castellanizada puntúa más bajo. Para que eso no impida usar el asistente existen el verificador personal y la calibración.

### Verificador personal (opcional)

Adapta la detección a la voz del usuario sin entrenar un modelo de palabra de activación nuevo. Es un clasificador pequeño (regresión logística de `scikit-learn`, la función de verificadores de `openwakeword`) que decide sobre las mismas características de audio que ya calcula el modelo preentrenado.

- **Archivo:** `wakeword_verifier.pkl`, en la carpeta de datos del usuario. Lo genera `scripts/calibrate_wakeword.py` en el propio equipo. No forma parte de `models/` ni se descarga.
- **Uso:** si el archivo existe y ⚙ `audio.wakeword_verifier = true`, se carga con `custom_verifier_models`. El modelo preentrenado actúa entonces como puerta con el umbral ⚙ `audio.wakeword_verifier_gate` (0,2): por debajo, no hay detección; por encima, la puntuación pasa a ser la del verificador, que se compara con `audio.wakeword_threshold`.
- **Efecto:** permite aceptar pronunciaciones a las que el modelo preentrenado da entre 0,2 y 0,5 sin aumentar las falsas activaciones, porque el verificador rechaza lo que no suena como el usuario diciendo la frase.
- **Sin archivo:** solo el modelo preentrenado. Es el comportamiento de partida.
- **Archivo ilegible o incompatible:** aviso (`WARNING`) y se sigue sin verificador. Nunca impide arrancar.
- **Consecuencia aceptada:** con verificador, «Hey Jarvis» responde mejor al usuario que a otras voces (nota de RES-42). No es un control de acceso.

### Trazas para calibrar

- `INFO`: cada detección aceptada, con su puntuación y si intervino el verificador.
- `INFO`: cada **casi detección**: la puntuación máxima de una ventana de 2 s quedó entre 0,15 y el umbral. Como máximo una línea cada 5 s. Sin esta traza, una frase que nunca alcanza el umbral no dejaría ningún dato.
- `DEBUG`: puntuación máxima de cada segundo.

## Segmentación de órdenes (modo `COMMANDS`)

Lógica pura en `segmenter.py`, probada sin audio real.

| Parámetro | Valor |
|---|---|
| Umbral de voz del VAD | 0,5 ⚙ por bloque |
| Inicio de orden | Primer bloque con voz; se incluyen los 400 ms anteriores |
| Fin de orden | 1 s ⚙ sin voz, o 15 s ⚙ de duración |
| Orden mínima | 300 ms de voz; por debajo se descarta y no cuenta como voz |

Al terminar una orden entrega `Utterance(pcm, started_at, ended_at, epoch)`. Mientras hay una orden en curso de captura, publica el nivel del micrófono.

## Escucha restringida (modo `WAKE_AND_CLOSING`)

Permite «Buenas noches Jarvis» en reposo (RF-02) sin un segundo modelo y con consumo acotado:

- Se segmenta igual que en `COMMANDS`, pero un segmento que supera 3,5 s se abandona sin entregarlo, y no se vuelve a capturar hasta el siguiente silencio. Una conversación o un vídeo de fondo se descartan así sin transcribir.
- Solo se entregan segmentos de entre 0,5 y 3,5 s, marcados `restricted=True`. El orquestador los transcribe con búsqueda voraz y el enrutador solo acepta la frase de cierre, con similitud ≥ 85 ⚙.
- Como máximo se entrega un segmento restringido cada 2 s.
- Se desactiva con ⚙ `audio.closing_phrase_in_idle = false`; entonces el modo en `IDLE` es `WAKE_ONLY` y la sesión se cierra diciendo «Hey Jarvis» y después «Buenas noches Jarvis».

## Micrófono

### Selección del dispositivo

Lógica pura en `device_selection.py`, probada con listas de dispositivos sin hardware. En Windows un mismo micrófono aparece una vez por cada API de audio, y no todas se comportan igual: en el prototipo, la entrada predeterminada entregó silencio digital de forma intermitente.

1. Se descartan las entradas sin canales y las de la API `Windows WDM-KS`.
2. **Nombre:** las entradas cuyo nombre contiene ⚙ `audio.input_device`; con el ajuste vacío, las que corresponden al dispositivo predeterminado del sistema.
3. **API:** si ⚙ `audio.input_hostapi` no está vacío, solo las de esa API. Si lo está, se elige por este orden de preferencia: `MME`, `Windows WASAPI`, `Windows DirectSound`. En Linux no hay preferencia de API.
4. Si el nombre o la API pedidos no existen, se usa el predeterminado del sistema y se registra un aviso (`WARNING`), una sola vez, con lo pedido y la lista de entradas disponibles.
5. Al abrir se registra en `INFO`: nombre, API, índice, frecuencia y si se abrió a 16 kHz o con remuestreo.

### Fallos

- **No disponible o error del flujo:** se publica `MicStatusChanged(False)`, se reintenta cada 5 s ⚙ y, mientras no haya una locución en curso, se reinicia PortAudio en cada reintento para refrescar la lista de dispositivos. Al recuperarse, `MicStatusChanged(True)`.
- **Micrófono mudo:** si el pico de la señal no pasa de 3 (sobre 32 767) durante 5 s seguidos con el flujo abierto, es silencio digital: el dispositivo no entrega audio, aunque el flujo no dé error. Se registra un aviso (`WARNING`) una vez por episodio, se publica `MicStatusChanged(False)` y se reabre el flujo en cada reintento, igual que si no estuviera disponible. Con el primer bloque con señal, `MicStatusChanged(True)` y un `INFO` de recuperación. Una habitación en silencio no produce silencio digital: el ruido de fondo de cualquier micrófono supera ese pico.
- El callback de PortAudio solo copia el bloque a una cola acotada (2 s); si la cola se llena, se descarta lo más antiguo y se registra.

### Telemetría de la señal

`telemetry.py` acumula, sin guardar audio, y escribe cada 5 s en `DEBUG`: pico y RMS en dBFS, bloques por segundo y bloques descartados. Sirve para distinguir en el registro «no llega audio», «llega muy bajo» y «llega bien pero no se detecta».

## Calibración

`scripts/calibrate_wakeword.py` es el paso de instalación que ajusta la activación a la voz y al micrófono del usuario. Abre el micrófono igual que el asistente (misma selección, misma ganancia) y trabaja siempre con el audio en memoria: no escribe audio en disco ni modifica la configuración; muestra las líneas de `settings.toml` que recomienda.

**Modo de medida** (por defecto):

1. Mide 3 s de ruido de fondo y pide decir «Hey Jarvis» 10 veces, una por indicación. Muestra el pico en dBFS y la puntuación máxima de cada repetición.
2. **Ganancia:** si el pico de la voz queda por debajo de −30 dBFS, recomienda el valor de `audio.input_gain` que lo lleva a −15 dBFS, con un máximo de 8.
3. **Veredicto**, con la configuración vigente:
   - 9 o más detecciones de 10: no hay que cambiar nada.
   - Menos de 9, y un umbral ≥ 0,3 daría 9 o más: recomienda ese valor de `audio.wakeword_threshold`.
   - En otro caso: recomienda entrenar el verificador personal.
   - Ninguna repetición llega a 0,2: el verificador no puede ayudar. Lo indica y recuerda la pronunciación a la inglesa y revisar el micrófono con `diagnose_mic.py`.

**Modo de entrenamiento** (`--train-verifier`):

1. Graba en memoria 20 repeticiones de «Hey Jarvis» (variando distancia y entonación), 60 s del usuario leyendo en voz alta un texto que el guion muestra y 20 s de ruido de fondo.
2. Extrae las características con `openwakeword`, tomando como positivas las ventanas con puntuación ≥ `audio.wakeword_verifier_gate`, y entrena el verificador.
3. **Validación:** pide 10 repeticiones nuevas y 30 s más de lectura. El verificador se guarda solo si detecta 9 o más de las 10 y no se activa ninguna vez durante la lectura. Si no, se descarta, no se guarda nada y el guion lo explica.
4. Al guardar, informa de la tasa de detección con y sin verificador.

Las reglas de recomendación y de validación son funciones puras con pruebas unitarias.

`scripts/diagnose_mic.py` sigue siendo la herramienta para elegir dispositivo: graba 5 s de cada entrada, mide el nivel, pasa el audio por `hey_jarvis`, clasifica cada una (muda, con señal, detecta) y recomienda los valores de `audio.input_device` y `audio.input_hostapi`.

## Interfaz

```python
class AudioProcessor:
    def start(self) -> None: ...                 # lanza el hilo de audio
    def stop(self) -> None: ...
    def set_mode(self, mode: CaptureMode, *, reopen_at: float | None = None) -> None: ...
    def current_level(self) -> float: ...        # último nivel del micrófono, 0–1

# Entradas que entrega al orquestador (con loop.call_soon_threadsafe):
WakeWordDetected(at) · Utterance(pcm, started_at, ended_at, epoch, restricted) · MicStatusChanged(available)
```

Las bibliotecas reales (`sounddevice`, `openwakeword`) se envuelven tras fábricas inyectables para probar sin hardware ni modelos.

## Criterios de aceptación

- `segmenter`: pruebas con secuencias sintéticas de bloques con y sin voz que cubren inicio, fin por pausa, fin por duración, orden mínima y abandono en modo restringido.
- `device_selection`: pruebas con una lista de dispositivos repetidos en varias API que cubren la exclusión de `WDM-KS`, el orden de preferencia, el nombre y la API pedidos, y la caída al predeterminado con aviso.
- Micrófono mudo: con bloques sintéticos a cero, aviso único, `MicStatusChanged(False)` y recuperación con el primer bloque con señal.
- Ganancia: se aplica antes de los detectores y satura sin desbordar.
- Verificador, con una fábrica falsa: presente y activado, se pasa a `openwakeword` con la puerta configurada; ausente o desactivado, no; ilegible, aviso y arranque normal.
- Casi detección: se registra entre 0,15 y el umbral, como máximo una vez cada 5 s.
- En `MUTED` no se entrega nada; al reabrir se reinician los detectores.
- Con modelos reales (marcador `models`): `hey_jarvis.wav` se detecta; los WAV de control (silencio, ruido, conversación) no.
- Con el micrófono real (lista manual): RNF-30 medido con `calibrate_wakeword.py`.
- Consumo en `WAKE_ONLY` dentro de RNF-04, con y sin verificador.

## Prohibiciones

- Ningún audio sale del dispositivo ni se escribe en disco, tampoco en los guiones de calibración y diagnóstico.
- No se usa ningún servicio en red.
- No se entrena desde cero ni se carga ningún modelo de palabra de activación distinto del preentrenado. La única adaptación admitida es el verificador personal.
- El verificador solo se carga desde la carpeta de datos del usuario y solo si lo generó `calibrate_wakeword.py` en el propio equipo: es un archivo `pickle`, y cargar uno de origen ajeno ejecutaría código ajeno.
