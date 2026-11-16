# Jarvis: asistente personal local

Asistente personal para Windows que funciona al 100 % en local. El usuario escribe sus órdenes en una caja de texto y el asistente responde con voz y en pantalla. No usa servidores externos, ni conexión a internet, ni IA generativa, ni herramientas de pago.

## Qué es

Jarvis es un asistente **basado en intenciones** (*Command & Control*), no en un modelo de lenguaje. Cada frase escrita se compara con un catálogo cerrado de patrones. Si encaja, se ejecuta una acción concreta y programada. Si no encaja, se ignora. El resultado es siempre el mismo para la misma orden: no hay «alucinaciones».

Se apoya en cuatro pilares:

1. **Privacidad:** ningún dato sale del equipo y el asistente no captura audio.
2. **Eficiencia:** consumo bajo de CPU, RAM y batería en un portátil sin GPU dedicada.
3. **Determinismo:** acciones precisas, con respuestas de texto fijo y valores insertados.
4. **Sin conexión:** entrada, intenciones, voz y datos funcionan sin red. Solo la instalación descarga la voz, una vez.

## Cómo se usa

El proceso arranca **dormido**, con un icono en la bandeja y una ventana con la caja de texto. El ciclo de vida se controla con tres frases escritas:

| Frase | Efecto |
|---|---|
| «Hey Jarvis» | Abre una sesión y pone el asistente a escuchar. En reposo, vuelve a escuchar. |
| «Gracias Jarvis» | Deja el asistente en reposo, con la sesión abierta. |
| «Buenas noches Jarvis» | Cierra la sesión y vuelve al modo dormido, sin terminar el proceso. |

Con la sesión abierta, el usuario escribe órdenes como «abre el escritorio», «busca el archivo informe», «recuérdame mañana a las 9 llamar al dentista» o «ayuda». Si una orden necesita un dato o una confirmación, el asistente pregunta y espera la respuesta en el turno siguiente. «Cancelar» detiene la orden o el diálogo en curso.

Documentación para el usuario:

- [MANUAL.md](MANUAL.md): guía de uso, con ejemplos de cada orden y problemas frecuentes.
- [PERSONALIZAR.md](PERSONALIZAR.md): cómo configurar sus aplicaciones, páginas web, carpetas y protocolos sin subirlos al repositorio. Incluye instrucciones para agentes de IA.

El catálogo completo de frases está en [software/catalogo-intenciones.md](software/catalogo-intenciones.md).

## Qué sabe hacer

| Módulo | Capacidad |
|---|---|
| Sesión | Nombrar la sesión actual y marcarla como importante. |
| Historial | Consultar las sesiones recientes y sus actividades, y eliminar una sesión. |
| Comandos | Terminal con directorio de trabajo persistente (`cd`, `ls`, `clear`), árbol de una carpeta y ejecución de binarios de una lista permitida (por ejemplo, `gcc`). |
| Apertura | Lanzar aplicaciones instaladas, abrir páginas de un catálogo en Microsoft Edge y abrir carpetas en el Explorador. |
| Búsqueda | Localizar archivos y carpetas en disco, con *Everything* si está instalado. |
| Creación | Crear archivos, carpetas o árboles de carpetas sin sobrescribir nunca nada. |
| Recordatorio | Crear recordatorios con avisos y fecha límite, notificarlos, posponerlos y confirmarlos. |
| Protocolos | Ejecutar con una sola orden una secuencia predefinida de tareas de varios módulos. |

Además, el asistente informa por voz del resultado de cada acción, repite su última respuesta, muestra la ayuda y se presenta.

## Interfaz

- **Pantalla de sesión:** ventana a pantalla completa con un orbe holográfico animado que reacciona a la voz del asistente.
- **HUD flotante:** ventana compacta, siempre encima, que muestra el estado de las tareas sin robar el foco a la aplicación que el usuario está usando.
- **Bandeja del sistema:** estado, abrir la sesión, abrir las carpetas de configuración y registro, y salir.

Diseño visual: [software/Interfaz/README.md](software/Interfaz/README.md).

## Arquitectura en breve

- **Máquina de estados:** `DORMIDO`, `IDLE`, `LISTENING_COMMAND`, `AWAITING_CONFIRMATION` y `AWAITING_PARAMETER`. Un orquestador coordina los turnos sin bloquear la entrada ni la interfaz.
- **Diálogos de varios turnos:** un módulo que necesita un dato deja la operación en pausa y la respuesta siguiente se dirige a ella.
- **Bus de eventos:** el backend y la interfaz solo se comunican por publicación y suscripción.
- **Módulos de acción desacoplados:** todos tienen la misma interfaz. Añadir uno nuevo es registrarlo en una lista.
- **Adaptadores de plataforma:** todo lo que depende del sistema operativo está en `os_adapters/`.

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ con `asyncio` |
| Enrutador de intenciones | `rapidfuzz` y patrones con huecos |
| Persistencia | SQLite en modo WAL, con borrado lógico |
| Planificador | `APScheduler` |
| Voz | `piper-tts`, voz `es_ES-davefx-medium` |
| Interfaz | Qt Quick (QML) con PySide6 |
| Configuración | Archivos TOML |

Diseño técnico completo: [software/arquitectura.md](software/arquitectura.md).

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| [software/](software/README.md) | Especificación formal: requisitos, reglas de negocio, módulos, base de datos, interfaz, casos de uso y plan de implementación. Es la fuente de verdad. |
| [implementation/](implementation/README.md) | Código (`src/jarvis_assistant/`), pruebas, guiones de instalación y medida. |
| [docs/](docs/) | Diseños y planes de cambios concretos. |

## Instalación rápida

Requisitos: Windows 10 u 11 y Python 3.11 o posterior. Desde `implementation/`, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -e .[dev]
.\.venv\Scripts\python.exe scripts\fetch_models.py
.\scripts\start_jarvis.ps1
```

Instrucciones completas (inicio automático, carpetas del usuario, diagnóstico, pruebas y desinstalación): [implementation/README.md](implementation/README.md).

## Alcance de la versión 1

La versión 1 corresponde a las fases 0 a 7 del [plan de implementación](software/plan-implementacion.md).

### Incluido

- Ciclo de vida completo por texto: dormido, sesión, reposo y cierre, con respuesta hablada.
- Los ocho módulos de acción: Sesión, Historial, Comandos, Apertura, Búsqueda, Creación, Recordatorio y Protocolos.
- Diálogos de varios turnos: confirmaciones, datos pendientes, colisiones de nombres y cancelación.
- Recordatorios con avisos, fecha límite, posposición y autoconfirmación. Solo se notifican con una sesión abierta.
- Interfaz completa: pantalla de sesión con el orbe, HUD flotante, subtítulos, panel de actividad, ventanas que se pueden apartar a los bordes y ayuda generada del registro de intenciones.
- Bandeja del sistema, instancia única, inicio automático con Windows y registro de diagnóstico.
- Configuración en archivos TOML: aplicaciones, páginas, lugares con nombre, binarios permitidos, plantillas de carpetas y protocolos.
- Robustez ante altavoz ausente, base de datos dañada, configuración inválida y voz no descargada.
- Pruebas automáticas sin hardware ni modelos, y guion de medida de rendimiento y consumo.

### Plataforma

- **Windows 11** es la plataforma objetivo de esta versión. Las instrucciones de instalación admiten también Windows 10.
- **Linux:** previsto para la fase 8, posterior a la versión 1. El código ya aísla lo que depende del sistema operativo.
- **macOS:** fuera de alcance.

### Fuera de alcance

- **Entrada por voz.** El asistente no escucha ni abre el micrófono; las órdenes se escriben. Se retiró porque el reconocimiento de voz no interpretaba bien las órdenes.
- **IA generativa.** No entiende frases libres: solo las del catálogo de intenciones, con tolerancia a erratas.
- **Identificación del usuario.** No hay control de acceso; las órdenes se aceptan las escriba quien las escriba.
- **Domótica.** Queda como ampliación futura.
- **Navegadores distintos de Edge** y páginas fuera del catálogo configurado.
- **Uso comercial.** `piper-tts` tiene licencia GPL-3.0; un uso comercial obliga a revisarla antes.

### Pendiente de cerrar

La fase 7 está hecha en el código. Quedan tareas que solo se pueden hacer en el equipo de referencia ([lista manual](implementation/tests/manual/fase-7.md)):

- Medir y anotar los requisitos de rendimiento y consumo con `scripts/measure.py`.
- Uso real durante varios días para ajustar umbrales, alias y patrones.
- Repetir los casos de robustez y la revisión visual en el equipo.
- Instalar en limpio y comprobar la privacidad con la red desactivada y con un monitor de conexiones.
