# Plan de implementación

Orden de construcción del asistente. Sustituye a los antiguos `tasks.md` y `alcance-prototipo-1.md`. Cada fase termina en algo que funciona y se puede probar; ninguna fase depende de una posterior.

## Reglas de trabajo

1. **La especificación manda.** Ante una duda, se resuelve en la especificación antes de escribir código.
2. **Primero la prueba.** Cada tarea se cierra con sus pruebas automáticas en verde. La lógica (FSM, enrutador, analizadores, reglas de módulos) se escribe con la prueba delante.
3. **Sin hardware en las pruebas por defecto.** `pytest` sin marcadores no necesita altavoz, modelos, red ni pantalla, y tarda menos de 60 s (RNF-24).
4. **Una fase, una lista manual.** Al cerrar cada fase se recorre su lista de `tests/manual/` en el equipo de referencia.
5. **Instalación de paquetes** siempre en el entorno virtual: `.\implementation\.venv\Scripts\pip.exe install <paquete>`.
6. **Reutilización.** El código que ya existe en `implementation/` se conserva donde cumple la especificación y se reescribe donde no. No se mantiene código que la contradiga.
7. **Hecho** significa: pruebas en verde, `ruff` sin avisos, criterios de aceptación del documento del módulo cumplidos, lista manual de la fase recorrida.

## Vista general

| Fase | Resultado | Casos de uso | Depende de |
|---|---|---|---|
| 0 | Base del proyecto: estructura, configuración, bus, reloj, base de datos, dobles de prueba. | — | — |
| 1 | Ciclo de vida por texto: «Hey Jarvis», «Gracias Jarvis», «Buenas noches Jarvis» escritas en una caja de texto, con respuesta hablada, bandeja y una ventana mínima. | CU-03, CU-04, CU-05 | 0 |
| 2 | Interfaz completa: orbe, animaciones, pantalla de sesión, HUD flotante, panel de actividad, subtítulos. | — | 1 |
| 3 | Órdenes sin diálogo: Comandos, Apertura, Búsqueda, consulta del Historial, ayuda. | CU-01, CU-02, CU-06, CU-07, CU-08 | 2 |
| 4 | Diálogo de varios turnos: Creación, eliminación en Historial, Sesión. | CU-09, CU-10 | 3 |
| 5 | Recordatorios. | CU-11, CU-12 | 4 |
| 6 | Protocolos. | CU-13 | 5 |
| 7 | Endurecimiento: rendimiento, consumo, inicio automático, revisión visual; escalabilidad, mantenibilidad e independencia entre módulos. | todos | 6 |
| 8 | Adaptador de Linux. | todos | 7 |

Las fases 0 a 7 forman la versión 1. La fase 1 es el corte mínimo que demuestra toda la cadena, del texto escrito a la respuesta hablada; a partir de la fase 3, cada fase añade módulos sin tocar el núcleo.

---

## Fase 0. Base del proyecto

**Objetivo:** el esqueleto sobre el que se apoya todo, sin voz ni interfaz.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-0.1 | `pyproject.toml` con las dependencias de [arquitectura.md](arquitectura.md), sección 9; marcadores de `pytest` (`models`, `hardware`); `ruff`. Estructura de carpetas de la sección 8. | `pip install -e .[dev]` y `pytest` funcionan con cero pruebas. |
| T-0.2 | `tests/conftest.py`: bloqueo de sockets en todas las pruebas. | Una prueba que abre un socket falla. |
| T-0.3 | `core/clock.py` y `tests/fakes/clock.py`: reloj real y reloj falso con temporizadores controlables. | Pruebas del reloj falso. |
| T-0.4 | `os_adapters/base.py` y `tests/fakes/platform.py`. `paths.py` con las carpetas de datos, configuración, registro y modelos. | Prueba de conformidad del doble con el `Protocol`. |
| T-0.5 | `config.py` y los TOML predeterminados ([configuracion.md](Modulos/Infraestructura/configuracion.md)). | Criterios de aceptación de Configuración (sin la validación de protocolos, que llega en la fase 6). |
| T-0.6 | `core/event_bus.py` y `core/events.py` con los eventos del ciclo de vida y de estado. | Criterios de aceptación del Bus. |
| T-0.7 | `core/database.py`, migración `0001`, y los repositorios de sesiones y actividades. | Criterios de aceptación de Persistencia. |
| T-0.8 | `process/logging_setup.py` y `process/single_instance.py`. | Registro rotativo; segunda instancia detectada. |
| T-0.9 | `scripts/fetch_models.py` con manifiesto y verificación de sumas. | Prueba con descarga simulada; ejecución real que deja `models/` completo. |

---

## Fase 1. Ciclo de vida por texto

**Objetivo:** escribir «Hey Jarvis», oír «Sesión iniciada. Le escucho.», escribir «Gracias Jarvis», «Hey Jarvis» y «Buenas noches Jarvis», con el comportamiento exacto de CU-03, CU-04 y CU-05. La interfaz es todavía mínima: una ventana de fondo oscuro con el estado en texto y la caja de texto.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-1.1 | `core/state_machine.py`: estados, entradas, efectos y tabla de transiciones del ciclo de vida (sin diálogo). | Una prueba por fila de la tabla de [maquina-estados.md](Modulos/Infraestructura/maquina-estados.md) que no sea de diálogo. |
| T-1.2 | `intent_router/normalizer.py` y la parte de `router.py` de la frase de activación, las frases de control y el cierre en reposo. | Frase de activación con erratas, frases de control y controles negativos del juego de pruebas. |
| T-1.3 | Retirada: entrada por texto (captura de audio). | — |
| T-1.4 | Retirada: entrada por texto (micrófono, palabra de activación por audio, calibración). | — |
| T-1.5 | Retirada: entrada por texto (transcriptor). | — |
| T-1.6 | `speaker/`: catálogo con las frases del ciclo de vida y generales, Piper, reproductor, cola, nivel. | Criterios de aceptación del Sintetizador. |
| T-1.7 | `core/orchestrator.py`: bucle de turnos, recepción de `TextSubmitted` y `UserTyping`, cuenta de inactividad de 30 s, ejecución de efectos, publicación del nivel de la voz a 20 Hz. | CU-03, CU-04 y CU-05 completos con dobles, incluidas todas sus alternativas. |
| T-1.8 | Sesión mínima: `open_session`, `close_session`, `recover_interrupted` sobre la base de datos. | Abrir y cerrar deja las filas correctas; recuperación de una sesión huérfana. |
| T-1.9 | `main.py` (`build_app` y `main`), `process/tray.py`, ventana mínima con la caja de texto ([entrada-texto.md](Modulos/Infraestructura/entrada-texto.md)), `scripts/install_startup.ps1` y `uninstall_startup.ps1`. | Criterios de aceptación de Proceso y de Entrada por texto. |

**Lista manual de la fase:** el ciclo completo escribiendo en el equipo real; lo enviado durante una locución del ciclo de vida se atiende al terminar; 30 s sin escribir pasan a reposo; cierre desde reposo; salir desde la bandeja; red desactivada; la ventana visible en modo dormido y oculta, con el proceso en la bandeja, al cerrarla.

---

## Fase 2. Interfaz completa

**Objetivo:** la interfaz definitiva, con el diseño de [Interfaz/README.md](Interfaz/README.md), aunque todavía no existan módulos que llenen los paneles.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-2.1 | `ui/bridge.py`, `ui/view_models.py` (asistente, tareas, diálogo), `Theme.qml` con todos los tokens, fuentes e iconos. | Los modelos reflejan sus eventos (`pytest-qt`). |
| T-2.2 | `ui/preview.py`: modo `--preview` con una secuencia de eventos simulados que recorre todos los estados; `--ui-debug` con contador de frames. | La vista previa arranca sin voz ni modelos. |
| T-2.3 | El orbe: capas, propiedades de control, aspecto por actividad y reacción al nivel de la voz del asistente. | Secciones 3 de Interfaz, revisadas con la vista previa. |
| T-2.4 | Animaciones de despertar y dormirse (variantes de reposo y de cierre) y fundido entre ellas. | Sección 4 de Interfaz; 2 s ± 0,1 s. |
| T-2.5 | `SessionScreen.qml`: barra superior, columnas, subtítulos, cursor oculto. Componentes comunes (`PanelFrame`, `TaskCard`, `StatusDot`, `Subtitles`, `StateLabel`, `Badge`, `EmptyState`). Panel de actividad. | Sección 5 de Interfaz. |
| T-2.6 | `HudOverlay.qml`: mini orbe, cabecera, cuerpo, contraer y expandir, ventana que no se activa. | Sección 6 de Interfaz; el HUD nunca toma el foco. |
| T-2.7 | `ui/window_controller.py` y su conexión con las ventanas: qué se muestra y cuándo; pantalla al frente al abrir sesión. Intenciones `nucleo.mostrar_pantalla` y `nucleo.ocultar_pantalla`. | Una prueba por fila de la tabla de [hud.md](Modulos/Infraestructura/hud.md), sección 2. |
| T-2.8 | Sincronía de la animación con la frase (RNF-22) e iconos de estado de la bandeja. | Desfase ≤ 150 ms en el registro. |
| T-2.9 | Prueba de integración que carga todo el QML sin pantalla. | Sin errores ni avisos de QML. |

**Lista manual de la fase:** lista de comprobación visual de Interfaz, sección 11; fluidez (RNF-21); foco (RNF-13).

---

## Fase 3. Órdenes sin diálogo

**Objetivo:** el asistente ya hace cosas útiles. Se construye la interfaz común y los módulos que no necesitan preguntar.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-3.1 | `core/action_api.py`; `run_task` en el orquestador con registro de actividades y `TaskUpdated`; `core/workdir.py`. | Una tarea falsa recorre `pendiente` → `completado` y `error`; un módulo que lanza una excepción no rompe nada (RNF-23). |
| T-3.2 | `intent_router/patterns.py` y `router.py` completos: registro, coincidencia, elección entre candidatos, reintento con el siguiente candidato. | Pruebas de coincidencia y de desambiguación. |
| T-3.3 | Analizadores de entidades: `numbers`, `catalogs`, `paths`, `names`, y `COMMAND_LINE`. | Pruebas de cada analizador. |
| T-3.4 | `os_adapters/windows.py`. | Criterios de aceptación de Plataforma. |
| T-3.5 | Módulo **Comandos** y su panel. | Criterios de aceptación de Comandos; CU-02 y CU-06. |
| T-3.6 | `core/notices.py` y la entrega de avisos en el orquestador (para el fin de un binario). | Un aviso espera a que termine la locución. |
| T-3.7 | Módulo **Apertura** y su panel, con «traer al frente». | Criterios de aceptación de Apertura; CU-01 y CU-07. |
| T-3.8 | Módulo **Búsqueda** y su panel. | Criterios de aceptación de Búsqueda; CU-08. |
| T-3.9 | Módulo **Historial**: `mostrar` y `actividades`, y su panel. | Orden y límite de RN-10. |
| T-3.10 | Intenciones del núcleo: ayuda (generada del registro) y repetir. Interrupción de la locución con «Hey Jarvis» y con el botón de silencio. Recarga de la configuración al abrir sesión. | RF-70, RF-85, RF-92, RF-94, RF-96. |
| T-3.11 | Juego de frases de prueba de las intenciones de esta fase y pruebas de arquitectura (importaciones prohibidas, registro). | RNF-11, RNF-18, RNF-20. |

**Lista manual de la fase:** cada orden de los módulos de la fase, escrita; rutas escritas con lugares con nombre y subcarpetas; latencia (RNF-03).

---

## Fase 4. Diálogo de varios turnos

**Objetivo:** el asistente pregunta y espera la respuesta.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-4.1 | `DialogueContext`, `ctx.ask`, estados `AWAITING_*`, tiempo de espera, repetición de la pregunta, validación por tipo en el enrutador, «cancelar». | Una prueba por fila de diálogo de la tabla de transiciones. |
| T-4.2 | Panel de diálogo (`DialogCard`) y aspecto «esperando» del orbe. | Visible en la vista previa. |
| T-4.3 | Módulo **Creación**. | Criterios de aceptación de Creación; CU-09. |
| T-4.4 | **Historial**: `eliminar`. | CU-10, flujo secundario. |
| T-4.5 | Módulo **Sesión**: nombrar, importancia, desbordamiento, restauración, eliminación al cerrar; acciones internas para protocolos. | Criterios de aceptación de Sesión; CU-10. |
| T-4.6 | Cierre de sesión con operaciones en curso (RN-46) y cancelación de un turno en curso (RN-52). | Pruebas de integración. |

**Lista manual de la fase:** colisión resuelta escribiendo la respuesta, sin repetir «Hey Jarvis»; cancelación; tiempo agotado; eliminación de una sesión.

---

## Fase 5. Recordatorios

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-5.1 | Analizadores `datetimes` (con `find_suffix`) y `durations`; formateadores de fechas y duraciones para la voz. | Pruebas con reloj falso de toda la gramática de [enrutador-intenciones.md](Modulos/Infraestructura/enrutador-intenciones.md), sección 5. |
| T-5.2 | `ReminderRepository`. | Pruebas del repositorio. |
| T-5.3 | Creación con una orden escrita, con su diálogo (`DATETIME`, `REMINDER_ACTION`). | CU-11. |
| T-5.4 | Programación con `APScheduler`: al abrir y al cerrar sesión; avisos y fechas límite; agrupación. | Avisos con y sin sesión abierta. |
| T-5.5 | Panel de recordatorios; leer, confirmar, posponer aviso, posponer fecha límite, mostrar, eliminar. | CU-12. |
| T-5.6 | Autoconfirmación a los 300 s. | Pruebas con reloj falso. |

**Lista manual de la fase:** un recordatorio «en un minuto» de principio a fin; uno que vence con el asistente dormido; posponer interrumpiendo la lectura.

---

## Fase 6. Protocolos

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-6.1 | Carga y validación de `protocols.toml` contra el registro de intenciones; `resolve_params`. | Protocolos válidos e inválidos. |
| T-6.2 | Módulo **Protocolos**: ejecución, subtareas, `stop_on_error`, cancelación, resumen. | Criterios de aceptación de Protocolos. |
| T-6.3 | Integración con Sesión: propuesta de nombre e importancia. | CU-13. |
| T-6.4 | Panel de protocolo y listado. | Progreso en tiempo real (RNF-14). |
| T-6.5 | Prueba que invoca desde un protocolo todas las acciones admitidas de todos los módulos. | RNF-19. |

**Lista manual de la fase:** un protocolo real del usuario con cinco tareas de tres módulos.

---

## Fase 7. Endurecimiento

**Objetivo:** que el asistente se pueda usar a diario y que su código se pueda ampliar sin romperse.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-7.1 | `scripts/measure.py` y medida de todos los RNF de rendimiento en el equipo de referencia. Ajuste de `beam_size`, hilos y calidad de la interfaz si hace falta. | RNF-03, RNF-04, RNF-05, RNF-21, RNF-22, RNF-25 cumplidos y anotados. |
| T-7.2 | Uso real durante varios días: ajuste de umbrales, alias y patrones según el registro. Medida de RNF-31. Cada frase no reconocida que debería haberlo sido se añade al juego de pruebas. | RNF-11 sobre el juego ampliado. |
| T-7.3 | Robustez: altavoz ausente, base de datos dañada, configuración inválida, falta de un modelo. | Cada caso con el comportamiento especificado. |
| T-7.4 | Revisión visual completa y `ui.reduce_motion`, `ui.quality`. | Lista de Interfaz, sección 11. |
| T-7.5 | Inicio automático, instrucciones de instalación en `implementation/README.md` y comprobación de privacidad con la red desactivada y con un monitor de conexiones. | RNF-01, RNF-02, RF-75. |
| T-7.6 | Cobertura y limpieza: código muerto fuera, cobertura ≥ 80 % en el núcleo. | RNF-24. |
| T-7.7 | Escalabilidad, mantenibilidad e independencia entre módulos, sin cambiar funcionalidades ni conceptos (detalle debajo). | Mapa de dependencias en verde; contratos entre paquetes tipados; el resto de pruebas sin cambios. |

### T-7.7. Escalabilidad, mantenibilidad e independencia

Revisión del código con tres criterios. Ningún cambio altera el comportamiento: las pruebas existentes siguen igual y en verde.

- **Independencia entre módulos.** Cada paquete solo importa lo que permite el mapa de dependencias de [arquitectura.md](arquitectura.md), sección 8.1. Lo comprueba `tests/unit/test_architecture.py` (`ALLOWED_DEPENDENCIES`): una dependencia nueva entre paquetes se añade al mapa a propósito, o la prueba falla. Un paquete nuevo sin reglas también la hace fallar.
- **Mantenibilidad.** Los contratos entre paquetes se anotan con sus `Protocol` en lugar de `Any`: `ActionContext.platform` y `Orchestrator(platform=…)` son `PlatformAdapter`; `scheduler`, `Scheduler`; `modules` y `ACTION_MODULES`, `ActionModule`. Las importaciones que solo sirven para anotar van bajo `TYPE_CHECKING`, sin crear dependencias en tiempo de ejecución.
- **Escalabilidad.** Añadir un módulo sigue siendo añadirlo a `ACTION_MODULES` (RNF-18). Pendiente, por orden de valor, y siempre sin cambio de comportamiento:
  1. `core/orchestrator.py` (unas 1 200 líneas) concentra el bucle de turnos, el diálogo y el registro de tareas. Extraer el diálogo (`_ask`, su temporizador y su cierre) a `core/dialogue.py` y el registro de tareas (`run_task`, subtareas, segundo plano) a `core/tasks.py`. `run_task` sigue siendo la única función que ejecuta acciones (AD-13).
  2. La configuración propia de cada módulo (`Catalog`, `StructureDef`, `ProtocolDef`…) vive en `config.py`: un módulo nuevo con configuración obliga a tocarlo. Si llegan más módulos, cada uno declara su sección y `config.py` solo la carga y valida.
  3. Los módulos de acción usan funciones puras de texto del enrutador y de la voz (`normalize`, `tokenize`, `slots.datetimes`, `count`, `formats`). Están permitidas en el mapa; si la lista crece, se mueven a un paquete neutro de texto del que dependan los tres.

---

## Fase 8. Linux

Posterior a la versión 1. No requiere cambios fuera de `os_adapters/`, de los guiones de instalación y de los ajustes de ventana de `ui/`.

| Tarea | Contenido | Hecho cuando |
|---|---|---|
| T-8.1 | `os_adapters/linux.py` según la tabla de [plataforma.md](Modulos/Infraestructura/plataforma.md). | Criterios de aceptación de Plataforma en Ubuntu LTS. |
| T-8.2 | Inicio automático y carpetas según XDG. | El asistente arranca al iniciar sesión. |
| T-8.3 | Ventanas: HUD sin foco en X11 y Wayland; «traer al frente» ausente en Wayland. | RNF-17. |

---

## Instalación (referencia para T-0.1 y T-7.5)

```powershell
cd implementation
python -m venv .venv
.\.venv\Scripts\pip.exe install -e .[dev]
.\.venv\Scripts\python.exe scripts\fetch_models.py      # única operación con red
.\.venv\Scripts\python.exe -m jarvis_assistant --preview # comprobar la interfaz
.\scripts\install_startup.ps1                            # inicio automático
```

Opcional: instalar *Everything* y su `es.exe` para la búsqueda en todo el disco.

## Riesgos del plan

| Riesgo | Señal | Respuesta |
|---|---|---|
| La latencia no cumple RNF-03. | Medida en T-1.7 y T-7.1. | `beam_size = 1`; después, modelo `base`. Ambos son configuración, no código. |
| El orbe cuesta más de lo previsto. | T-2.3 se alarga. | Calidad `medium` como base; las partículas y el sombreador aditivo se dejan para T-7.4. |
| Órdenes escritas con erratas en nombres propios. | Frases no reconocidas en el registro (T-7.2). | Alias y umbrales: configuración, no código. |
| Rutas, nombres y comandos escritos no se resuelven. | RNF-31 bajo en T-7.2. | Alias y umbrales (configuración); revisar la gramática de entidades para texto escrito. |
