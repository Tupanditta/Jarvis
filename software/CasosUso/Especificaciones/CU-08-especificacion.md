# CU-08. Buscar y abrir un resultado

- **Actor principal:** ACT-01. **Secundario:** ACT-04.
- **Objetivo:** localizar un archivo o una carpeta en disco y abrirlo.
- **Requisitos:** RF-26, RF-27, RF-28, RF-90, RNF-09, RN-50, RES-18, RES-31.
- **Módulo:** [Búsqueda](../../Modulos/Accion/busqueda.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario dice «Busca {consulta}», «Busca el archivo {consulta}» o «Busca la carpeta {consulta}».

## Flujo principal

1. El sistema identifica `busqueda.buscar` con el tipo que indica el patrón (ambos, archivos o carpetas).
2. El sistema crea la tarea en `pendiente` y consulta la herramienta indexada.
3. El sistema ordena los resultados y muestra los 10 primeros, numerados, en el panel de búsqueda.
4. La tarea pasa a `completado`. El sistema dice «He encontrado {n} resultados. El primero es {nombre}, en {carpeta}.».
5. El usuario dice «Abre el resultado {n}».
6. El sistema abre ese archivo con su aplicación predeterminada, o esa carpeta en el gestor de archivos, y dice «Abriendo {nombre}.».

## Flujos alternativos

- **A1. Sin resultados** (paso 3): `completado`; «No he encontrado nada para {consulta}.».
- **A2. Un solo resultado** (paso 4): «He encontrado {nombre} en {carpeta}.».
- **A3. Herramienta indexada no disponible** (paso 2): búsqueda limitada a la carpeta del usuario y a los lugares con nombre, cortada a los 5 s. El panel la marca como «limitada» y el sistema añade «Búsqueda limitada a sus carpetas.».
- **A4. Abrir la ubicación** (paso 5): «Abre la carpeta del resultado {n}» abre la carpeta que lo contiene.
- **A5. Índice fuera de rango o sin búsqueda previa** (paso 5): `error`; «No hay ningún elemento {n}.».
- **A6. El archivo ya no existe** (paso 6): `error`; «Ese archivo ya no existe.».

## Postcondiciones

Resultados visibles en el panel; actividades registradas. La búsqueda no modifica nada en el disco.
