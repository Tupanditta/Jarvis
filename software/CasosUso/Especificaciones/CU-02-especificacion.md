# CU-02. Obtener el árbol de directorios de una carpeta

- **Actor principal:** ACT-01.
- **Objetivo:** que el usuario vea en la interfaz el árbol de una carpeta, o del directorio de trabajo, y oiga un resumen.
- **Requisitos:** RF-59, RF-73, RF-74, RF-69, RF-71, RN-40, RN-41, RN-42, RES-28.
- **Módulo:** [Comandos](../../Modulos/Accion/comandos.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario dice «Árbol», «Muestra el árbol» o «Árbol de {ruta}».

## Flujo principal

1. El sistema identifica `comandos.arbol` y resuelve la ruta; sin ruta, usa el directorio de trabajo.
2. El sistema crea la tarea en `pendiente`.
3. El sistema recorre la carpeta de forma nativa hasta 3 niveles y 200 entradas (RN-40), sin contar la raíz.
4. El sistema muestra el árbol en el panel de comandos, con sangría por nivel.
5. La tarea pasa a `completado`. El sistema dice el recuento, p. ej. «3 carpetas y 12 archivos.».

## Flujos alternativos

- **A1. Se alcanza un límite** (paso 3): el recorrido se detiene; el panel añade «… (árbol recortado)» y el sistema dice el recuento mostrado seguido de «Se muestra solo una parte.».
- **A2. La ruta no existe o no es una carpeta** (paso 1): `error`; el sistema dice el motivo (RN-41). No se muestra ningún árbol.
- **A3. Carpeta vacía:** el panel muestra «Carpeta vacía»; el sistema dice «0 carpetas y 0 archivos.».
- **A4. Subcarpeta sin permiso de lectura:** aparece como entrada, sin hijos; el recorrido continúa.

## Postcondiciones

Árbol visible en el panel de comandos; actividad registrada. El directorio de trabajo y el disco no cambian.
