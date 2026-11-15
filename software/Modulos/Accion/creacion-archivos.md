# Módulo de acción: Creación de Archivos/Carpetas

- **Código:** `action_modules/file_manager.py` (compartido con [Búsqueda](busqueda.md)). Nombre de módulo: `creacion`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Crear un archivo, una carpeta o un árbol de directorios sin sobrescribir nunca nada existente.

## Acciones

| Acción | Parámetros | Efecto |
|---|---|---|
| `crear_archivo` | `nombre: NEW_NAME`, `ruta: DIR_PATH` (opcional) | Crea un archivo vacío (RF-29). |
| `crear_carpeta` | `nombre: NEW_NAME`, `ruta: DIR_PATH` (opcional) | Crea una carpeta (RF-30). |
| `crear_arbol` | `arbol: NEW_PATH`, `ruta: DIR_PATH` (opcional) | Crea una ruta anidada, p. ej. «backend barra src barra modelos» (RF-31). |
| `crear_estructura` | `estructura: CATALOG` (estructuras), `nombre: NEW_NAME`, `ruta: DIR_PATH` (opcional) | Crea una carpeta raíz con las subcarpetas de una estructura predefinida en `structures.toml` (RF-97). |

Todas se pueden invocar con una orden escrita y desde protocolos. No tienen panel propio: se ven en el panel de actividad y, si hay colisión, en el de diálogo.

## Reglas

### Ubicación

- Sin `ruta`, la ubicación es el directorio de trabajo (RN-54). Una ruta relativa se resuelve respecto a él (RN-42).
- La ubicación debe existir y ser una carpeta; si no, RN-41.
- Destino = ubicación + nombre.

### Nunca sobrescribir (RN-18)

- La colisión se comprueba con `destino.exists()`, nunca con expresiones regulares (RES-30).
- **Archivo:** se crea con `open(destino, "x")`, que falla si el destino existe; así tampoco se sobrescribe si algo lo crea entre la comprobación y la creación.
- **Carpeta:** `destino.mkdir(exist_ok=False)`.
- **Árbol:** hay colisión si la carpeta más profunda de la ruta ya existe. Las carpetas intermedias que ya existan se reutilizan, sin modificarlas: `destino.mkdir(parents=True, exist_ok=False)`.
- **Estructura:** hay colisión si la carpeta raíz ya existe. Si no, se crea la raíz y, dentro, cada subcarpeta de la estructura (que pueden ser rutas anidadas).

### Colisión: diálogo de varios turnos (RN-19)

1. La tarea se pausa.
2. `await ctx.ask(…, ExpectedType.NEW_FILENAME, metadata={"destino": destino, "ubicacion": ubicacion})`: el sistema pasa a `AWAITING_PARAMETER`.
3. El asistente dice que ya existe y pide otro nombre o cancelar.
4. Con un nombre nuevo, se vuelve a comprobar. Si también colisiona, se repite. Tras 3 ⚙ colisiones seguidas, se cancela.
5. Con «cancelar», tiempo agotado o demasiadas colisiones: no se crea nada y la tarea queda en `error` con el motivo «cancelada».

En `crear_arbol`, el nombre nuevo sustituye a la carpeta más profunda; en `crear_estructura`, a la carpeta raíz.

### Otros errores

- Nombre no válido para el sistema de archivos: lo rechaza el enrutador ([enrutador-intenciones.md](../Infraestructura/enrutador-intenciones.md), sección 7).
- Sin permiso de escritura u otro error del sistema: tarea en `error`, «No he podido crear {nombre}.».

### Voz

Éxito: «{Tipo} {nombre} creado en {carpeta}.», con el nombre real creado.

## Datos

Sistema de archivos local. Ningún dato propio en la base de datos.

## Criterios de aceptación

Con un sistema de archivos temporal y respuestas de diálogo simuladas:

- Creación de archivo, carpeta, árbol y estructura, con y sin ubicación.
- Colisión resuelta con otro nombre; segunda colisión; tercera colisión y cancelación; cancelación explícita; tiempo agotado.
- Árbol con carpetas intermedias existentes: se reutilizan.
- Ubicación inexistente.
- En ningún caso cambia el contenido ni la fecha de un archivo existente.
- El código del módulo no contiene llamadas de borrado ni de escritura sobre rutas existentes (prueba que inspecciona el código).

## Prohibiciones

- Prohibido sobrescribir, mover o borrar un archivo o carpeta existente.
- Prohibido usar expresiones regulares para comprobar si algo ya existe.
