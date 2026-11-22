# Módulo de acción: Catálogo

- **Código:** `action_modules/catalog_manager.py`. Nombre de módulo: `catalogo`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Ver, añadir y eliminar las aplicaciones y páginas que se abren con «abre {nombre}» ([Apertura](apertura-apps.md)) y los comandos de terminal que se pueden ejecutar ([Comandos](comandos.md)), sin editar los archivos a mano.

## Acciones

| Acción | Parámetros | Panel | Efecto |
|---|---|---|---|
| `ver` | — | Catálogo | Publica `CatalogShown` con todas las entradas (RF-100). No se registra como actividad. |
| `añadir` | Desde la ventana: `tipo` (`aplicacion`, `pagina` o `comando`), `nombre`, `destino`, `alias` y, para una aplicación, `argumentos` | Catálogo | Con la orden escrita, sin datos, solo abre la ventana y dice «Complete los datos en la ventana del catálogo». Con el formulario de la ventana, valida y añade la entrada (RF-101, RN-65, RN-66). |
| `eliminar` | `entrada: CATALOG` (nombres y alias de las entradas) o, desde la ventana, su id `{tipo}:{nombre}` | Catálogo | Elimina la entrada tras confirmación (RF-102). |

Ninguna acción es invocable desde protocolos. `añadir` y `eliminar` cambian el recurso `catalogo.entradas`: la cola de órdenes no ejecuta a la vez otra orden que lo use.

## Reglas

### Qué entra en el catálogo (RN-65)

| Tipo | Archivo | Campos | Lo usa |
|---|---|---|---|
| Aplicación | `catalog.toml`, `[[apps]]` | `name`, `path` (ejecutable, acceso directo o nombre en el PATH), `aliases`, `args` | `apertura.abrir` |
| Página | `catalog.toml`, `[[pages]]` | `name`, `url`, `aliases` | `apertura.abrir`, siempre en Microsoft Edge (RN-17) |
| Comando | `commands.toml`, `[[binaries]]` | `name`, `executable`, `aliases` | `comandos.ejecutar` (RN-45) |

Las aplicaciones descubiertas en el menú Inicio no se ven ni se editan aquí.

### Añadir

1. La ventana envía el formulario completo. Los alias y los argumentos se escriben uno por línea o separados por comas; las líneas vacías se ignoran.
2. **Validación (RN-66).** Si falla, la tarea queda en `error`, el asistente dice «No puedo añadirlo. Tiene el motivo en la ventana del catálogo.» y la ventana muestra el motivo:
   - sin nombre: «Escriba un nombre.»;
   - aplicación sin ruta: «Escriba la ruta del programa o su nombre en el PATH.»;
   - página cuya dirección no empieza por `http://` o `https://`;
   - comando sin ejecutable: «Escriba el ejecutable: su nombre en el PATH o su ruta.»;
   - nombre o alias ya usado: ««{nombre}» ya es el nombre de otra aplicación o página.» (o «de otro comando»).
3. **Guardado.** La entrada se escribe en su archivo con `tomlkit`, que conserva comentarios y formato, y se aplica en la sesión en curso (`ctx.save_launchers`): se puede abrir o ejecutar enseguida. Si no se puede escribir, `error`, «No he podido guardar el catálogo.» y el motivo en la ventana.

### Eliminar

1. La entrada se busca por su id (desde la ventana) o por su nombre o un alias (orden escrita). Si el mismo nombre existe en varios tipos, gana la aplicación y después la página.
2. Si no existe: `error`, «No encuentro eso en el catálogo.» y el motivo en la ventana.
3. Se pregunta (`BOOLEAN`) «¿Elimino {nombre} del catálogo?», con la entrada como `subject`. Desde la ventana se pregunta igual.
4. Solo con un sí se quita del archivo y de la sesión. Con un no, una cancelación o el vencimiento del tiempo, no se elimina y la tarea queda en `error` con el motivo «cancelada».

### Comparación de nombres

Dos nombres son iguales si coinciden sin mayúsculas, sin tildes y sin espacios sobrantes. Las aplicaciones y las páginas comparten nombres, porque las dos se abren con «abre {nombre}»; los comandos tienen los suyos.

## Datos

`catalog.toml` y `commands.toml`, a través del orquestador (`save_launchers`). Ninguna tabla de la base de datos.

## Eventos

`CatalogShown` (entradas y, si lo hay, el motivo de un fallo); `PanelActivated`; `TaskUpdated` de cada tarea.

## Criterios de aceptación

- `ver` publica las tres clases de entradas.
- `añadir` por orden escrita, sin datos: abre la ventana y no cambia nada.
- `añadir` de cada tipo con datos válidos: queda en el archivo, conserva sus comentarios y la entrada se abre o se ejecuta en la misma sesión.
- Cada motivo de validación de RN-66, incluido un alias repetido entre aplicación y página y un nombre de comando igual al de una aplicación (se admite).
- `eliminar`: inexistente, confirmación afirmativa, negativa y vencida; nombre repetido en varios tipos.
- Fallo al escribir el archivo: la sesión conserva el catálogo anterior.

## Prohibiciones

- No se añade nada sin pasar la validación.
- No se elimina ninguna entrada sin confirmación explícita.
- No se editan las aplicaciones descubiertas del sistema.
- No se ejecuta ni se abre nada al añadirlo.
