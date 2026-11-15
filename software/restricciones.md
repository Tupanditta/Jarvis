# Restricciones

Condiciones que delimitan el alcance del asistente o que deben respetarse en su diseño, implementación y distribución. Columna **Origen**: ver [README.md](README.md).

## Alcance

| ID | Restricción | Origen |
|---|---|---|
| RES-01 | **Módulos incluidos.** Sesión, Historial, Comandos, Apertura de Aplicaciones y Páginas, Búsqueda, Creación, Recordatorio y Protocolos, más las respuestas de estado por voz. El usuario da las órdenes por escrito ([entrada-texto.md](Modulos/Infraestructura/entrada-texto.md)). Ningún módulo existente se elimina. | Idea |
| RES-02 | **Navegación de directorios y mapeo de entorno.** La navegación de directorios (RF-58) pertenece a Apertura; el mapeo de entorno (RF-59) pertenece a Comandos. | Idea |
| RES-03 | **Domótica fuera de alcance.** Ampliación futura. | Idea |
| RES-04 | **Sin IA generativa.** No se usan modelos generativos (LLM). El sistema funciona por intenciones, con resultados deterministas. | Idea |
| RES-42 | **Identificación del usuario fuera de alcance.** Las órdenes se aceptan las escriba quien las escriba; no hay control de acceso. | Idea |
| RES-44 | **Sin tecnología de pago.** Ninguna dependencia, modelo, herramienta o servicio requiere pago, cuenta o clave. | Idea |

## Plataforma

| ID | Restricción | Origen |
|---|---|---|
| RES-05 | **Windows 11 es la plataforma de la versión 1.** | Idea |
| RES-06 | **Linux es plataforma prevista.** Todo el código dependiente del sistema operativo vive en `os_adapters/` detrás de la interfaz `PlatformAdapter`. La versión 1 implementa solo el adaptador de Windows; el de Linux se construye en la última fase. Ningún módulo fuera de `os_adapters/` y `ui/` importa APIs específicas de un sistema operativo. | Idea, modificada |
| RES-07 | **macOS fuera de alcance.** | Idea |
| RES-45 | **Equipo objetivo: ordenador portátil sin GPU dedicada.** El diseño prioriza el consumo de CPU, RAM y batería (RNF-04, RNF-05, RNF-06). | Idea |

## Stack

| ID | Restricción | Origen |
|---|---|---|
| RES-08 | **Stack fijado.** Las tecnologías de RES-09 a RES-16 no se sustituyen sin actualizar esta especificación. | Idea |
| RES-09 | **Lenguaje.** Python 3.11 o superior. | Idea |
| RES-10 | **Entrada por texto.** El usuario escribe sus órdenes en una caja de texto; el asistente no captura audio ni abre el micrófono. «Hey Jarvis», «Gracias Jarvis» y «Buenas noches Jarvis» se reconocen en el enrutador por similitud con la frase completa (RES-12). No se usan `openwakeword`, Silero VAD ni `pvporcupine`. Sustituye a la palabra de activación por audio, retirada. | Idea, modificada |
| RES-11 | **Transcripción.** Retirada: entrada por texto. No se usan `faster-whisper` ni `vosk`. | Idea, modificada |
| RES-12 | **Enrutador.** La intención se clasifica por coincidencia difusa con `rapidfuzz` y las entidades se extraen con patrones estructurados declarados por cada módulo ([enrutador-intenciones.md](Modulos/Infraestructura/enrutador-intenciones.md)). | Idea |
| RES-13 | **Persistencia.** `sqlite3` nativo en modo `WAL`. | Idea |
| RES-14 | **Planificador.** `APScheduler` (`AsyncIOScheduler`) sin almacén de trabajos propio; SQLite es la única fuente de verdad. Al abrir cada sesión se leen los recordatorios, se disparan los avisos vencidos y se programan los futuros; sin sesión abierta no se dispara ninguna notificación (RN-22). | Idea |
| RES-15 | **Síntesis de voz.** `piper-tts` con la voz `es_ES-davefx-medium`. | Idea |
| RES-16 | **Interfaz.** Qt Quick (QML) con PySide6. Dos superficies: la pantalla de sesión (pantalla completa) y el HUD flotante (siempre encima, sin bordes; no toma el foco salvo con un clic en su caja de texto). Ambas tienen la caja donde el usuario escribe. | Idea + Técnico |
| RES-17 | **Navegador.** Las páginas se abren con Microsoft Edge, nunca con otro navegador. | Idea |
| RES-18 | **Búsqueda indexada.** `es.exe` de *Everything* en Windows; `fd` en Linux. | Idea |
| RES-19 | **Traer ventanas al frente.** En Windows, con las APIs de ventanas del sistema. En Linux, solo con X11. | Idea |
| RES-20 | **Sin GPU obligatoria.** Toda la inferencia se ejecuta en CPU. La GPU integrada solo se usa para dibujar la interfaz. | Idea |
| RES-46 | **Modelos incluidos.** El único modelo es la voz de Piper, en la carpeta `models/` del asistente. Se descarga una sola vez durante la instalación con `scripts/fetch_models.py`; el asistente no descarga nada al arrancar ni al funcionar. Si falta, el proceso no arranca y lo registra. | Idea |

## Arquitectura

| ID | Restricción | Origen |
|---|---|---|
| RES-21 | **Prohibido el pipeline lineal.** Las fases se coordinan con una máquina de estados finitos con los estados `DORMIDO`, `IDLE`, `LISTENING_COMMAND`, `AWAITING_CONFIRMATION` y `AWAITING_PARAMETER`. | Idea |
| RES-22 | **Diálogo sin espera bloqueante.** Un módulo que necesita una confirmación o un dato registra un `DialogueContext` y suspende su corrutina; nunca espera de forma síncrona (`input()` o equivalente). | Idea |
| RES-23 | **Arquitectura concurrente.** La ejecución no bloquea la escucha ni la interfaz. Modelo de hilos en [arquitectura.md](arquitectura.md), sección 3. | Idea |
| RES-24 | **Bus de eventos.** El backend y la interfaz se comunican solo mediante el bus; los módulos de acción no manipulan ventanas. | Idea |
| RES-25 | **Sin regex complejas para lenguaje natural.** La interpretación del lenguaje se hace con patrones por palabras y analizadores por tokens. Se admiten expresiones regulares solo para normalizar texto (quitar signos, colapsar espacios). El prefijo de un recordatorio se separa con un patrón del enrutador, no con una regex. | Idea |
| RES-26 | **Sin reglas de conjugación verbal** (RN-20). | Idea |
| RES-27 | **Respuestas de voz parametrizadas.** Texto estático con valores insertados; sin generación libre. | Idea |
| RES-28 | **`cd`, `ls`, `clear` y el árbol sin subprocesos.** Se implementan de forma nativa en Python. | Idea |
| RES-29 | **Binarios externos asíncronos**, sin intérprete de órdenes (`shell=False`) y solo de la lista permitida (RN-45). | Idea + Refuerzo |
| RES-30 | **Colisiones sin regex.** La existencia del destino se comprueba con `Path.exists()`. | Idea |
| RES-31 | **Sin recorrido lento del disco** cuando la raíz es amplia (RNF-09). | Idea |
| RES-32 | **No robar el foco.** El asistente no quita el foco a las aplicaciones que abre ni a la que el usuario está usando. Única excepción: la pantalla de sesión pasa al frente y pide el foco al abrir la sesión (RF-82). | Idea |
| RES-47 | **Lógica separada de los efectos.** La máquina de estados, el enrutador, los analizadores de entidades y las reglas de los módulos son código puro y probado sin hardware, modelos ni interfaz. El hardware, los modelos, el reloj y el sistema operativo se inyectan como dependencias. | Técnico |

## Datos y privacidad

| ID | Restricción | Origen |
|---|---|---|
| RES-33 | **Sin texto plano ni JSON** para sesiones, actividades y recordatorios: solo SQLite. La configuración sí se guarda en archivos TOML, que el asistente solo lee. | Idea |
| RES-34 | **Sin `DELETE` físico** de sesiones ni recordatorios. Las claves ajenas usan `ON DELETE RESTRICT`. | Idea |
| RES-35 | **Fechas con zona horaria.** Todas las fechas se guardan en ISO-8601 con zona horaria, normalizadas a UTC (`+00:00`); nunca fechas sin zona. Se muestran y se dicen en la hora local del sistema. | Idea, modificada |
| RES-36 | **Protocolos de solo lectura.** Se definen en un archivo de configuración estático que el asistente nunca escribe. | Idea |
| RES-37 | **Marca de desbordamiento persistida.** La tabla `sessions` incluye la columna `pending_purge_on_close` (RN-08). | Refuerzo |
| RES-48 | **Privacidad del registro.** El asistente no captura ni guarda audio. El texto de las órdenes escritas solo aparece en el registro de diagnóstico en nivel `DEBUG`. | Refuerzo |

## Conectividad

| ID | Restricción | Origen |
|---|---|---|
| RES-38 | **Ejecución 100 % offline** (RNF-02). | Idea |
| RES-39 | **Sin servicios en red.** El asistente no abre conexiones de red (RNF-01). Las páginas las abre Edge, no el asistente. | Idea |

## Distribución y licencias

| ID | Restricción | Origen |
|---|---|---|
| RES-43 | **Uso personal, no comercial.** `piper-tts` tiene licencia GPL-3.0. Cualquier uso comercial obliga a revisar antes esta licencia. | Idea |

## Organización de archivos

| ID | Restricción | Origen |
|---|---|---|
| RES-40 | **Estructura de directorios.** El código sigue la estructura de [arquitectura.md](arquitectura.md), sección 8, que amplía la de [contexto.md](contexto.md), sección 5. | Idea |
| RES-41 | **Código no monolítico.** Cada funcionalidad es un módulo de acción desacoplado con la interfaz común (RNF-19). | Idea |
