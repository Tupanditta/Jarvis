# CU-07. Abrir una aplicación o página y traerla al frente

- **Actor principal:** ACT-01. **Secundario:** ACT-04.
- **Objetivo:** lanzar una aplicación o una página sin que el asistente interfiera con el foco, y poder recuperarla después.
- **Requisitos:** RF-22, RF-23, RF-24, RF-25, RF-87, RNF-13, RN-17, RN-49, RES-17, RES-32.
- **Módulo:** [Apertura](../../Modulos/Accion/apertura-apps.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario escribe «Abre {nombre}», p. ej. «Abre Visual Studio Code» o «Abre GitHub».

## Flujo principal

1. El sistema identifica `apertura.abrir` y busca el nombre en el catálogo de aplicaciones, en el de páginas y en las aplicaciones descubiertas, por ese orden (RN-49).
2. El sistema crea la tarea en `pendiente` y lanza la aplicación, o abre la URL en Microsoft Edge.
3. La tarea pasa a `completado`. El sistema dice «Abriendo {nombre}.» y añade una tarjeta al panel de aperturas.
4. La aplicación abierta toma el foco. La pantalla de sesión queda detrás y aparece el HUD flotante, que no toma el foco (RF-87).
5. El sistema localiza la ventana nueva y activa el botón «traer al frente» de su tarjeta.
6. Más tarde, el usuario hace clic en ese botón o dice «Trae al frente {nombre}»: la ventana pasa al primer plano.

## Flujos alternativos

- **A1. Nombre no encontrado** (paso 1): `error`; «No encuentro {nombre}.».
- **A2. Edge no instalado** (paso 2, página): `error`; «Microsoft Edge no está instalado.».
- **A3. Fallo al lanzar** (paso 2): `error`; «No he podido abrir {nombre}.».
- **A4. No se localiza la ventana** (paso 5): la tarjeta queda sin botón activo; la tarea sigue `completado`.
- **A5. La ventana ya se cerró** (paso 6): el botón se desactiva; con la orden, «Esa ventana ya no está abierta.».
- **A6. Sistema sin soporte para traer al frente** (Wayland): el botón no se muestra; con la orden, «No está disponible en este sistema.».

## Postcondiciones

Aplicación o página abierta; actividad registrada; el asistente no ha cambiado el foco por su cuenta.
