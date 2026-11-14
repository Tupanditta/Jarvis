# WAV de prueba

Formato: 16 kHz, mono, int16. Todos son sintéticos y se generan con
`implementation/scripts/make_fixture_audio.py` (reproducible; semilla fija para el ruido):

    .\implementation\.venv\Scripts\python.exe implementation\scripts\make_fixture_audio.py

La voz es Piper `es_ES-davefx-medium` (`implementation/models/piper/`), remuestreada de 22 050 Hz a 16 kHz.
Las voces llevan 0,5 s de silencio digital al inicio y al final. Silencio y ruido se crean con numpy.

| Archivo | Origen | Contenido | Qué espera la prueba |
|---|---|---|---|
| `hey_jarvis.wav` | Piper | «Hey Jarvis» | Activa la detección de `hey_jarvis` (no está garantizado con voz sintética) |
| `gracias_jarvis.wav` | Piper | «Gracias Jarvis» | Frase de cierre por voz: orden esperada del usuario |
| `control_conversacion.wav` | Piper | Frase de conversación sin la palabra Jarvis | No activa nada |
| `control_muchas_gracias_jarvis_por_todo.wav` | Piper | «Muchas gracias Jarvis por todo» | No activa nada (la frase no es una orden aislada) |
| `control_silencio.wav` | numpy | Silencio digital, 5 s | No activa nada; el VAD no detecta voz |
| `control_ruido.wav` | numpy | Ruido blanco de bajo nivel (sigma 300, aprox. -40 dBFS), 5 s | No activa nada; el VAD no detecta voz |
| `largo_stt.wav` | Piper | Cuatro frases concatenadas, unos 20 s (>= 10 s de voz) | Se transcribe en paralelo en la prueba de rendimiento |

`buenas_noches_jarvis.wav` no existe: el modelo y el WAV son opcionales en el prototipo (DEF-30, D-42).

Pendiente: las grabaciones reales del usuario con su micrófono. Pueden sustituir a los sintéticos
con los mismos nombres; no deben contener datos personales ni salir del equipo.
