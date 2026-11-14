# CU-01. Abrir una carpeta en el gestor de archivos

- **Actor principal:** ACT-01. **Secundario:** ACT-02.
- **Objetivo:** que el usuario vea una carpeta en el gestor de archivos nativo.
- **Requisitos:** RF-58, RF-24, RF-25, RF-69, RF-71, RN-41, RN-42, RES-32.
- **Módulo:** [Apertura](../../Modulos/Accion/apertura-apps.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario dice «Abre la carpeta {ruta}» o «Abre esta carpeta».

## Flujo principal

1. El sistema transcribe la orden e identifica `apertura.abrir_carpeta`.
2. El sistema resuelve la ruta: lugar con nombre, subcarpeta del directorio de trabajo o ruta dictada; sin ruta, el directorio de trabajo (RN-42).
3. El sistema crea la tarea en `pendiente` y la muestra en el panel de actividad.
4. El sistema abre la carpeta en el gestor de archivos. La ventana del gestor toma el foco; el asistente no lo recupera (RES-32).
5. La tarea pasa a `completado`. El sistema dice «Abriendo {nombre}.» y añade la carpeta al panel de aperturas.
6. El sistema localiza la ventana abierta y activa su botón «traer al frente» (RF-25).

## Flujos alternativos

- **A1. La ruta no existe** (paso 2): la tarea queda en `error`; el sistema dice «La carpeta {nombre} no existe.». No se abre ninguna ventana.
- **A2. La ruta no es una carpeta** (paso 2): `error`; «{nombre} no es una carpeta.».
- **A3. El gestor de archivos no se puede abrir** (paso 4): `error`; «No he podido abrir el gestor de archivos.».

## Postcondiciones

- Éxito: carpeta visible en el gestor; actividad `completado` en la sesión.
- Fallo: actividad `error`; ningún otro efecto. El directorio de trabajo no cambia en ningún caso.
