# Contexto del proyecto: Asistente Personal Local (basado en intenciones)

Base del proyecto. El detalle de cada módulo está en `Modulos/` (ver el [índice de módulos](#9-índice-de-módulos)).

## 1. Visión general

Asistente personal que se ejecuta al 100 % en local en un ordenador portátil convencional. El usuario le escribe las órdenes en una caja de texto y el asistente responde hablando y en pantalla. No depende de servidores externos ni de conexión a internet, y no usa ninguna herramienta de pago.

A diferencia de los asistentes basados en IA generativa (LLM), usa una arquitectura **basada en intenciones (Command & Control)** y admite **diálogos de varios turnos**: preguntas de confirmación o peticiones de datos que quedan pendientes de la respuesta del usuario. Se apoya en cuatro pilares:

1. **Privacidad absoluta:** ningún dato sale del dispositivo, y el asistente no captura audio.
2. **Latencia mínima y eficiencia:** sin redes neuronales masivas; el consumo de CPU, RAM y batería es bajo.
3. **Determinismo:** el asistente ejecuta acciones precisas y programadas, sin riesgo de «alucinaciones».
4. **Ejecución 100 % offline:** entrada de órdenes, intenciones, síntesis de voz y persistencia funcionan sin red.

La única excepción a «sin red» es la instalación: descargar las dependencias y la voz una vez (ver [plan-implementacion.md](plan-implementacion.md)).

## 2. Capacidades principales

| Módulo | Capacidad |
|---|---|
| [Sesión](Modulos/Accion/sesion.md) | Gestionar la sesión de uso actual: nombre e importancia. El proceso arranca dormido, sin sesión, atendiendo solo «Hey Jarvis». Todas las frases se escriben. «Hey Jarvis» abre la sesión y pone el asistente a escuchar; «Gracias Jarvis» lo deja en reposo y «Hey Jarvis» vuelve a ponerlo a escuchar. «Buenas noches Jarvis», en cualquier momento con la sesión abierta, cierra la sesión y devuelve el asistente al modo dormido sin terminar el proceso. Las frases se aceptan diga quien las diga. |
| [Historial](Modulos/Accion/historial.md) | Consultar las sesiones recientes y sus actividades, y eliminar una sesión por su identificador. |
| [Comandos](Modulos/Accion/comandos.md) | Terminal con directorio de trabajo persistente (`cd`, `ls`, `clear`), árbol de directorios de una carpeta (mapeo de entorno) y ejecución de binarios externos, por ejemplo compilar con `gcc`, informando del resultado. |
| [Apertura de Aplicaciones y Páginas](Modulos/Accion/apertura-apps.md) | Lanzar aplicaciones instaladas, abrir URLs de un catálogo predefinido en Microsoft Edge y abrir carpetas en el gestor de archivos nativo (navegación de directorios). |
| [Búsqueda de Archivos/Carpetas](Modulos/Accion/busqueda.md) | Localizar archivos, carpetas o ambos en disco mediante herramientas indexadas. |
| [Creación de Archivos/Carpetas](Modulos/Accion/creacion-archivos.md) | Crear un archivo, una carpeta o un árbol de directorios sin sobrescribir nunca nada existente. |
| [Recordatorio](Modulos/Accion/recordatorio.md) | Crear recordatorios con fechas de aviso y una fecha límite opcional, notificarlos, posponerlos y confirmarlos. |
| [Protocolos](Modulos/Accion/protocolos.md) | Ejecutar secuencias predefinidas de tareas de varios módulos. |

Capacidades transversales:

- **Entrada por texto:** el usuario escribe cada orden en una caja de texto y la envía con Enter ([entrada-texto.md](Modulos/Infraestructura/entrada-texto.md)). El asistente no escucha.
- **Respuestas de estado:** el asistente informa por voz del resultado de cada acción.
- **Interfaz:** pantalla de sesión con un orbe holográfico animado y un HUD flotante que muestra el estado de las tareas sin robar el foco ([Interfaz/README.md](Interfaz/README.md)).

### Estados de tarea

Toda tarea que se muestra en la interfaz y se registra en el historial usa exactamente tres estados: `pendiente`, `error` y `completado`.

## 3. Stack tecnológico

Todo el stack es gratuito y de código abierto o de uso libre.

| Componente | Tecnología |
|---|---|
| Lenguaje base | Python 3.11+ con `asyncio`, `threading`, `pathlib`, `subprocess`, `sqlite3` y `tomllib`. |
| Entrada de órdenes (`ui/`) | Caja de texto de la interfaz. La frase de activación «Hey Jarvis» la reconoce el enrutador. |
| Altavoz | `sounddevice`. |
| Enrutador de intenciones (`intent_router/`) | Coincidencia difusa con `rapidfuzz` y extracción de entidades mediante patrones estructurados con huecos. |
| Persistencia (`core/database.py`) | `sqlite3` nativo en modo `WAL`. |
| Planificador | `APScheduler` (`AsyncIOScheduler`) sin almacén de trabajos propio; SQLite es la única fuente de verdad. |
| Síntesis de voz (`speaker/`) | `piper-tts`, voz `es_ES-davefx-medium`. |
| Interfaz gráfica (`ui/`) | Qt Quick (QML) con PySide6: pantalla de sesión y HUD flotante siempre encima, sin bordes y que no toma el foco por su cuenta; ambos con la caja de texto. |
| Configuración | Archivos TOML de solo lectura para el asistente. |
| Búsqueda en disco | `es.exe` de *Everything* (Windows). |

Frase de activación: «Hey Jarvis», escrita. Criterios de elección y restricciones asociadas: [restricciones.md](restricciones.md). Versiones: [arquitectura.md](arquitectura.md), sección 9.

## 4. Arquitectura de alto nivel

- **Prohibición del pipeline lineal:** no se permite un pipeline lineal sin estado (Texto → Router → Acción → Fin), porque muchos módulos necesitan una confirmación del usuario o resolver conflictos en varios turnos.
- **Máquina de estados (FSM):** un orquestador coordina las fases mediante una máquina de estados finitos, dentro de una arquitectura concurrente que no bloquea la entrada. Detalle en [Máquina de estados](Modulos/Infraestructura/maquina-estados.md).
- **Contexto de diálogo (`DialogueContext`):** cuando un módulo necesita una confirmación o un dato adicional, deja registrada la operación en pausa sin bloquear la ejecución, y la respuesta del siguiente turno se dirige a esa operación en lugar de interpretarse como una orden nueva.
- **Bus de eventos:** el backend y la interfaz se comunican solo por publicación/suscripción.
- **Adaptadores de plataforma:** todo lo que depende del sistema operativo está detrás de una interfaz única.

Diseño técnico completo en [arquitectura.md](arquitectura.md).

## 5. Diseño modular y estructura de directorios

El código no es un bloque monolítico. Cada funcionalidad es un módulo de acción desacoplado con una interfaz común, invocable por el enrutador y por los Protocolos.

```text
jarvis_assistant/
├── main.py                     # Punto de entrada y composición
├── config.py                   # Carga y validación de la configuración
├── core/
│   ├── state_machine.py        # Máquina de estados (FSM) y DialogueContext
│   ├── orchestrator.py         # Bucle de turnos
│   ├── event_bus.py            # Pub/sub entre backend e interfaz
│   ├── events.py               # Eventos tipados del bus
│   ├── action_api.py           # Interfaz común de los módulos de acción
│   ├── notices.py              # Cola de avisos
│   ├── clock.py                # Reloj inyectable
│   ├── database.py             # Gestor SQLite3 y migraciones
│   └── migrations/             # Scripts SQL numerados
├── intent_router/              # Patrones, entidades y coincidencia difusa
├── speaker/                    # Frases y motor Piper TTS
├── action_modules/             # Módulos de negocio desacoplados
│   ├── session_manager.py      # Módulos: Sesión e Historial
│   ├── command_runner.py       # Módulo: Comandos
│   ├── app_launcher.py         # Módulo: Apertura de aplicaciones y páginas
│   ├── file_manager.py         # Módulos: Búsqueda y Creación
│   ├── reminder_manager.py     # Módulo: Recordatorio
│   └── protocol_runner.py      # Módulo: Protocolos
├── os_adapters/                # Adaptadores de plataforma (Windows; Linux en la fase final)
├── process/                    # Instancia única, bandeja, registro de diagnóstico
└── ui/                         # Pantalla de sesión y HUD flotante (QML)
```

Árbol completo, con todos los archivos, en [arquitectura.md](arquitectura.md), sección 8.

## 6. Escalabilidad

Para añadir un comando nuevo basta con crear un módulo en `action_modules/` que declare sus intenciones y registrarlo en una única lista, sin tocar el resto del sistema (RNF-18). Un ejemplo de ampliación futura es la domótica, que queda fuera del alcance actual.

## 7. Plataforma

- **Windows 11** es la plataforma de la versión 1: Microsoft Edge para las páginas, *Everything* para la búsqueda indexada y las APIs de ventanas de Windows para traer ventanas al frente.
- **Linux** es una plataforma prevista. Todo el código dependiente del sistema operativo está aislado en `os_adapters/`; el adaptador de Linux se construye en la última fase del plan, con herramientas equivalentes (`fd`, `xdg-open`). En Wayland no se podrá traer ventanas al frente.
- **macOS queda fuera del alcance.**

## 8. Principio de borrado lógico

Toda eliminación de sesiones y recordatorios es lógica: las filas se conservan en la base de datos y no se usa `DELETE` físico.

- Eliminar una sesión significa marcarla con `is_deleted = 1`.
- Eliminar un recordatorio significa cambiar su `status` a `'eliminado'`.

## 9. Índice de módulos

### Módulos de acción

| Módulo | Documento | Código |
|---|---|---|
| Sesión | [Modulos/Accion/sesion.md](Modulos/Accion/sesion.md) | `action_modules/session_manager.py` |
| Historial | [Modulos/Accion/historial.md](Modulos/Accion/historial.md) | `action_modules/session_manager.py` |
| Comandos | [Modulos/Accion/comandos.md](Modulos/Accion/comandos.md) | `action_modules/command_runner.py` |
| Apertura de Aplicaciones y Páginas | [Modulos/Accion/apertura-apps.md](Modulos/Accion/apertura-apps.md) | `action_modules/app_launcher.py` |
| Búsqueda de Archivos/Carpetas | [Modulos/Accion/busqueda.md](Modulos/Accion/busqueda.md) | `action_modules/file_manager.py` |
| Creación de Archivos/Carpetas | [Modulos/Accion/creacion-archivos.md](Modulos/Accion/creacion-archivos.md) | `action_modules/file_manager.py` |
| Recordatorio | [Modulos/Accion/recordatorio.md](Modulos/Accion/recordatorio.md) | `action_modules/reminder_manager.py` |
| Protocolos | [Modulos/Accion/protocolos.md](Modulos/Accion/protocolos.md) | `action_modules/protocol_runner.py` |

### Módulos de infraestructura

| Módulo | Documento | Código | Origen |
|---|---|---|---|
| Máquina de estados y contexto de diálogo | [maquina-estados.md](Modulos/Infraestructura/maquina-estados.md) | `core/state_machine.py`, `core/orchestrator.py` | Idea |
| Bus de eventos | [bus-eventos.md](Modulos/Infraestructura/bus-eventos.md) | `core/event_bus.py`, `core/events.py` | Idea |
| Persistencia | [persistencia.md](Modulos/Infraestructura/persistencia.md) | `core/database.py` | Idea |
| Entrada por texto | [entrada-texto.md](Modulos/Infraestructura/entrada-texto.md) | `ui/`, `core/events.py`, `core/orchestrator.py` | Refuerzo |
| Enrutador de intenciones | [enrutador-intenciones.md](Modulos/Infraestructura/enrutador-intenciones.md) | `intent_router/` | Idea |
| Sintetizador de voz (TTS) | [sintetizador.md](Modulos/Infraestructura/sintetizador.md) | `speaker/` | Idea |
| Interfaz HUD | [hud.md](Modulos/Infraestructura/hud.md) | `ui/` | Idea |
| Configuración | [configuracion.md](Modulos/Infraestructura/configuracion.md) | `config/` | Refuerzo |
| Ventana de configuración | [configurador.md](Modulos/Infraestructura/configurador.md) | `configurator/` | Refuerzo |
| Plataforma | [plataforma.md](Modulos/Infraestructura/plataforma.md) | `os_adapters/` | Refuerzo |
| Proceso y diagnóstico | [proceso.md](Modulos/Infraestructura/proceso.md) | `process/`, `main.py` | Refuerzo |

## 10. Glosario

| Término | Significado |
|---|---|
| Dormido | Proceso en marcha sin sesión abierta. Solo se atiende «Hey Jarvis». Estado `DORMIDO`. |
| Reposo | Sesión abierta sin escuchar órdenes. Estado `IDLE`. |
| Escucha | Sesión abierta escuchando órdenes. Estado `LISTENING_COMMAND`. |
| Espera | Sesión abierta esperando la respuesta a una pregunta del asistente. Estados `AWAITING_*`. |
| Sesión | Periodo de uso entre un «Hey Jarvis» dicho en dormido y el cierre. Agrupa las actividades del historial. |
| Turno | Una frase del usuario y todo lo que el asistente hace con ella. |
| Orden | Frase del usuario capturada mientras el asistente escucha. |
| Intención | Lo que el usuario quiere hacer, identificado a partir del texto de la orden. |
| Entidad | Dato sobre el que recae la intención (ruta, nombre, índice, fecha). |
| Patrón | Plantilla de frase con texto fijo y huecos para entidades. |
| Tarea | Unidad de trabajo de un módulo de acción, con uno de los tres estados de tarea. |
| Actividad | Registro de una tarea en el historial de la sesión. |
| Aviso | Mensaje que el asistente inicia por su cuenta (recordatorio, fin de un binario). |
| Pantalla de sesión | Ventana a pantalla completa con el orbe. |
| HUD flotante | Ventana compacta siempre encima que no toma el foco. |
| Panel | Bloque de contenido de un módulo; el mismo componente se usa en la pantalla de sesión y en el HUD. |
| Lugar con nombre | Carpeta a la que el usuario se refiere por un nombre hablado («escritorio», «proyectos»). |
