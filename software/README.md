# Especificación del Asistente de Voz Personal «Jarvis»

Especificación formal y completa del producto. Es la única fuente de verdad para implementar: no quedan puntos «por definir». Si el código y esta carpeta discrepan, manda esta carpeta.

## Cómo leerla

| Orden | Documento | Contenido |
|---|---|---|
| 1 | [contexto.md](contexto.md) | Visión, pilares, capacidades, glosario e índice de módulos. |
| 2 | [restricciones.md](restricciones.md) | Límites de alcance, plataforma, stack y arquitectura (`RES-XX`). |
| 3 | [reglas-negocio.md](reglas-negocio.md) | Políticas del dominio, independientes de la tecnología (`RN-XX`). |
| 4 | [Requisitos/funcionales.md](Requisitos/funcionales.md) | Qué hace el sistema (`RF-XX`). |
| 5 | [Requisitos/no-funcionales.md](Requisitos/no-funcionales.md) | Cualidades medibles (`RNF-XX`). |
| 6 | [arquitectura.md](arquitectura.md) | Diseño técnico: hilos, flujo de un turno, interfaz común de módulos, estructura de código, dependencias. |
| 7 | [catalogo-intenciones.md](catalogo-intenciones.md) | Todas las frases que entiende el asistente y todas las que dice. |
| 8 | [Modulos/](Modulos/) | Un documento por módulo: 8 de acción y 11 de infraestructura. |
| 9 | [BaseDatos/especificacion-base-datos.md](BaseDatos/especificacion-base-datos.md) | Esquema SQLite y reglas de integridad. |
| 10 | [Interfaz/README.md](Interfaz/README.md) | Diseño visual: pantalla de sesión, orbe, animaciones, HUD flotante y sistema de diseño. |
| 11 | [CasosUso/](CasosUso/catalogo-cu.md) | Casos de uso y matriz de trazabilidad. |
| 12 | [plan-implementacion.md](plan-implementacion.md) | Fases, tareas y criterios de aceptación, en orden de construcción. |

## Convenciones

- **Identificadores:** `RF` requisito funcional, `RNF` no funcional, `RN` regla de negocio, `RES` restricción, `CU` caso de uso, `F` fase del plan. Los identificadores que ya existían conservan su número; los nuevos continúan la numeración. Un identificador retirado se lista como «Retirado» con su motivo y no se reutiliza.
- **Marcas de origen:** en las tablas, la columna **Origen** vale `Idea` (definido por el autor del proyecto), `Refuerzo` (añadido para completar o proteger una idea) o `Técnico` (decisión de implementación, sustituible sin cambiar el producto).
- **Idioma:** documentación, frases y nombres de dominio en español; identificadores de código en inglés, salvo los valores de dominio que el autor fijó en español (`pendiente`, `error`, `completado`, `activo`, `vencido`, `eliminado`, `DORMIDO`).
- **Valores configurables:** todo umbral o tiempo marcado con ⚙ se lee de la configuración ([Modulos/Infraestructura/configuracion.md](Modulos/Infraestructura/configuracion.md)); el valor escrito es el predeterminado.

## Qué cambió respecto a la especificación anterior

La versión anterior completa está en [_obsoleto/especificacion-anterior/](_obsoleto/especificacion-anterior/). No debe usarse para implementar.

### Ideas conservadas sin cambios

Ejecución 100 % local y sin IA generativa; arquitectura por intenciones con diálogos de varios turnos; máquina de estados con `DORMIDO`, `IDLE`, `LISTENING_COMMAND`, `AWAITING_CONFIRMATION` y `AWAITING_PARAMETER`; ciclo de vida con «Hey Jarvis», «Gracias Jarvis» y «Buenas noches Jarvis» y sus frases de respuesta; los 8 módulos de acción y los 8 de infraestructura; los tres estados de tarea; borrado lógico; reglas de sesión (nombre, importancia, límite de 10, desbordamiento); reglas completas de recordatorios (avisos, fecha límite, posposición, autoconfirmación a 300 s); protocolos; directorio de trabajo persistente; nunca sobrescribir; páginas solo del catálogo y solo con Microsoft Edge; pantalla de sesión con el orbe holográfico y sus animaciones de 2 s; HUD flotante que no roba el foco; stack (Python, `openwakeword`, `faster-whisper`, `rapidfuzz`, SQLite en WAL, `APScheduler`, `piper-tts`).

### Ideas modificadas (y por qué)

| Antes | Ahora | Motivo |
|---|---|---|
| «Buenas noches Jarvis» detectada con un modelo propio de `openwakeword` entrenado a mano. | Se reconoce como orden transcrita, igual que «Gracias Jarvis». En reposo se atiende con una escucha restringida que solo acepta esa frase (RF-02, RN-43). | Entrenar y mantener un modelo propio disparaba el coste de desarrollo y dejaba el cierre por voz sin funcionar. El comportamiento para el usuario es el mismo: la frase cierra la sesión en reposo y en escucha. |
| Al volver a escuchar desde reposo, la pantalla de sesión vuelve al frente y toma el foco. | Predeterminado: si la pantalla de sesión no está en primer plano, el despertar se muestra en el HUD flotante sin tocar el foco. El comportamiento anterior queda disponible con ⚙ `ui.wake_brings_screen_to_front`. | Contradecía el principio «el asistente no roba el foco» mientras el usuario trabaja en otra aplicación. Al abrir la sesión la pantalla sí pasa al frente. |
| Tomar el foco con `AttachThreadInput`. | La pantalla pasa al frente de forma garantizada (ventana superior temporal) y pide el foco; si Windows lo deniega, no se fuerza. | Técnica frágil, bloqueada por Windows en varios casos y costosa de probar. |
| Fluidez medida por frame (99 % en un intervalo, ±1 frame) y sincronía voz-animación de 45 ms. | 60 fps como objetivo y 30 fps como mínimo; animaciones de 2 s ± 0,1 s; sincronía de 150 ms (RNF-21, RNF-22). | Las medidas anteriores no son perceptibles y bloqueaban el desarrollo con pruebas inestables. |
| Linux soportado desde el principio (X11 y Wayland). | Windows 11 en la versión 1. Linux queda preparado mediante la capa de adaptadores de plataforma y se construye en la última fase (RES-06). | Duplicaba el coste de desarrollo y pruebas de cada módulo. |
| Fechas guardadas con la zona horaria local. | Fechas guardadas con zona horaria, normalizadas a UTC; se muestran y se dicen en hora local (RES-35). | Con desplazamientos distintos (cambio de hora) el orden de las fechas era incorrecto. |
| Identificador de sesión de tipo texto. | Número entero correlativo. | Un número se puede dictar por voz; un texto arbitrario no. |
| Excepción temporal: arrancar con la sesión abierta. | Retirada. El proceso arranca dormido (RF-75). Queda como ajuste de desarrollo ⚙ `startup.open_session_on_start`. | Era un parche del prototipo. |
| Toolkit PyQt6. | PySide6 (mismo Qt, binding oficial, licencia LGPL, herramientas incluidas). | Menos restricciones de licencia y mejores herramientas; el coste de cambio es mínimo. |

### Ideas añadidas

Cancelar por voz («cancelar»), interrumpir al asistente con «Hey Jarvis» mientras habla, icono en la bandeja del sistema (estado, abrir sesión, salir), subtítulos de lo que se oye y se responde, ayuda por voz generada del registro de intenciones, «repite», lugares con nombre y resolución difusa de rutas dictadas, lista cerrada de binarios ejecutables, descubrimiento de aplicaciones del menú Inicio, abrir un resultado de búsqueda por su número, plantillas de estructuras de carpetas, recuperación de sesiones interrumpidas, configuración en archivos TOML, capa de adaptadores de plataforma, registro de diagnóstico.

### Documentos retirados

`design.md`, `tasks.md`, `alcance-prototipo-1.md`, `guia-entrenamiento-buenas-noches.md` y `especificaci_n_de_arquitectura_y_refactorizaci_n.md` se sustituyen por [arquitectura.md](arquitectura.md) y [plan-implementacion.md](plan-implementacion.md).
