# CU-09. Crear un archivo o carpeta

- **Actor principal:** ACT-01.
- **Objetivo:** crear un archivo, una carpeta o un árbol de carpetas sin sobrescribir nada, resolviendo las colisiones por diálogo.
- **Requisitos:** RF-29 a RF-34, RF-97, RF-66, RF-67, RF-68, RF-84, RN-18, RN-19, RN-37, RN-38, RN-54, RES-22, RES-30.
- **Módulos:** [Creación](../../Modulos/Accion/creacion-archivos.md), [Máquina de estados](../../Modulos/Infraestructura/maquina-estados.md).

## Precondiciones

Sesión abierta y asistente en `LISTENING_COMMAND`.

## Disparador

El usuario escribe, p. ej., «Crea el archivo notas punto txt en documentos».

## Flujo principal

1. El sistema identifica `creacion.crear_archivo`, construye el nombre (`notas.txt`) y resuelve la ubicación; sin ubicación, el directorio de trabajo (RN-54).
2. El sistema crea la tarea en `pendiente` y comprueba que el destino no existe.
3. El sistema crea el archivo vacío.
4. La tarea pasa a `completado`. El sistema dice «Archivo notas.txt creado en Documentos.».

## Flujos alternativos

- **A1. Colisión** (paso 2): el destino ya existe.
  1. El sistema pausa la tarea y pasa a `AWAITING_PARAMETER`. Dice «Ya existe notas.txt. Escriba otro nombre o cancelar.» y muestra la pregunta en la interfaz.
  2. El usuario escribe otro nombre, sin repetir «Hey Jarvis»: «notas dos punto txt».
  3. El sistema vuelve al paso 2 con el nombre nuevo.
- **A2. El nombre nuevo también colisiona:** se repite A1. A la tercera colisión seguida, el sistema dice «Operación cancelada.»; la tarea queda en `error`.
- **A3. El usuario escribe «cancelar»** (en A1): «Operación cancelada.»; `error`, motivo «cancelada». No se crea nada.
- **A4. 20 s sin respuesta** (en A1): igual que A3.
- **A5. Ubicación inexistente** (paso 1): `error`; «La carpeta {nombre} no existe.».
- **A6. Carpeta:** «Crea la carpeta {nombre}» sigue el mismo flujo.
- **A7. Árbol:** «Crea las carpetas backend barra src barra modelos» crea la ruta anidada; hay colisión solo si la carpeta más profunda ya existe.
- **A8. Estructura:** «Crea la estructura proyecto python llamada analizador» crea la carpeta raíz y las subcarpetas de la estructura; hay colisión si la raíz existe.
- **A9. Sin permiso de escritura** (paso 3): `error`; «No he podido crear {nombre}.».

## Postcondiciones

- Éxito: el elemento existe; ningún archivo o carpeta anterior ha cambiado.
- Fallo o cancelación: el disco no ha cambiado.
