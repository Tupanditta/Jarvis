# Catálogo de casos de uso

Actores y casos de uso del asistente. La especificación de cada uno está en `Especificaciones/CU-XX-especificacion.md`. Los casos de uso describen los flujos representativos; el comportamiento completo de cada módulo está en [Modulos/](../Modulos/).

## Actores

| ID | Nombre | Descripción |
|---|---|---|
| ACT-01 | Usuario | Persona que escribe órdenes al asistente y ve su interfaz. |
| ACT-02 | Gestor de archivos del sistema | Aplicación nativa que muestra el contenido de una carpeta (el Explorador en Windows). |
| ACT-03 | Planificador | Componente interno que dispara los avisos de los recordatorios a su hora. |
| ACT-04 | Sistema operativo | Lanza aplicaciones, páginas y binarios, y gestiona las ventanas. |

## Casos de uso

| ID | Título | Actores | Objetivo | Fase |
|---|---|---|---|---|
| [CU-01](Especificaciones/CU-01-especificacion.md) | Abrir una carpeta en el gestor de archivos | ACT-01, ACT-02 | Ver una carpeta en el gestor de archivos nativo. | 3 |
| [CU-02](Especificaciones/CU-02-especificacion.md) | Obtener el árbol de directorios de una carpeta | ACT-01 | Ver el árbol de una carpeta y oír un resumen. | 3 |
| [CU-03](Especificaciones/CU-03-especificacion.md) | Abrir sesión | ACT-01 | Abrir con «Hey Jarvis» una sesión nueva y dejar el asistente escuchando. | 1 |
| [CU-04](Especificaciones/CU-04-especificacion.md) | Pasar a reposo | ACT-01 | Hacer que el asistente deje de escuchar, con la sesión abierta. | 1 |
| [CU-05](Especificaciones/CU-05-especificacion.md) | Cerrar sesión | ACT-01 | Cerrar la sesión con «Buenas noches Jarvis» y volver al modo dormido. | 1 |
| [CU-06](Especificaciones/CU-06-especificacion.md) | Ejecutar un binario externo | ACT-01, ACT-04 | Ejecutar un programa permitido y conocer su resultado. | 3 |
| [CU-07](Especificaciones/CU-07-especificacion.md) | Abrir una aplicación o página y traerla al frente | ACT-01, ACT-04 | Lanzar algo sin perder el foco y recuperarlo después. | 3 |
| [CU-08](Especificaciones/CU-08-especificacion.md) | Buscar y abrir un resultado | ACT-01, ACT-04 | Localizar un archivo o carpeta y abrirlo. | 3 |
| [CU-09](Especificaciones/CU-09-especificacion.md) | Crear un archivo o carpeta | ACT-01 | Crear sin sobrescribir, resolviendo colisiones por diálogo. | 4 |
| [CU-10](Especificaciones/CU-10-especificacion.md) | Gestionar la sesión y el historial | ACT-01 | Nombrar la sesión, marcar su importancia, consultar el historial y eliminar una sesión. | 4 |
| [CU-11](Especificaciones/CU-11-especificacion.md) | Crear un recordatorio | ACT-01 | Guardar un recordatorio con sus avisos y su fecha límite. | 5 |
| [CU-12](Especificaciones/CU-12-especificacion.md) | Atender un recordatorio | ACT-01, ACT-03 | Recibir el aviso, leerlo, posponerlo o confirmarlo. | 5 |
| [CU-13](Especificaciones/CU-13-especificacion.md) | Ejecutar un protocolo | ACT-01 | Lanzar una secuencia de tareas con una sola orden. | 6 |

## Convenciones de las especificaciones

- Las precondiciones citan el estado de la máquina de estados.
- Todo paso «el sistema dice» usa una frase de [catalogo-intenciones.md](../catalogo-intenciones.md), sección 5.
- En todos los casos de uso con sesión abierta valen, sin repetirlas, estas alternativas comunes:
  - **AC-1. Orden no reconocida:** se ignora en silencio (RN-51).
  - **AC-2. «Cancelar»:** detiene la orden o el diálogo en curso (RN-52).
  - **AC-3. «Gracias Jarvis» o «Buenas noches Jarvis»:** se aplican CU-04 o CU-05 (RN-43, RN-46).
  - **AC-4. Entidad no resuelta:** la tarea queda en `error` y el sistema dice el motivo ([enrutador-intenciones.md](../Modulos/Infraestructura/enrutador-intenciones.md), sección 4).
  - **AC-5. Error inesperado:** la tarea queda en `error`, el sistema dice «Ha ocurrido un error» y sigue atendiendo órdenes (RNF-23).
