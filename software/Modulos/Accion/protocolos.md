# Módulo de acción: Protocolos

- **Código:** `action_modules/protocol_runner.py`. Nombre de módulo: `protocolos`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Ejecutar secuencias predefinidas de tareas de varios módulos de acción con una sola orden.

## Acciones

| Acción | Parámetros | Efecto |
|---|---|---|
| `ejecutar` | `protocolo: CATALOG` (protocolos) | Ejecuta el protocolo (RF-52 a RF-57). |
| `listar` | — | Publica `ProtocolsListed` y dice cuántos hay (RF-99). |

Solo con una orden del usuario: un protocolo no puede invocar a otro protocolo.

## Definición (RN-33, RES-36)

Los protocolos se definen en `protocols.toml`, un archivo estático que el asistente solo lee. El usuario lo edita a mano; no se crean ni se editan con órdenes.

```toml
[[protocols]]
id = "modo-trabajo"
name = "modo trabajo"                 # nombre que se escribe y que se propone para la sesión
aliases = ["a trabajar"]
important = true

  [[protocols.tasks]]
  module = "comandos"
  action = "cd"
  params = { ruta = "proyectos barra jarvis" }

  [[protocols.tasks]]
  module = "apertura"
  action = "abrir"
  params = { objetivo = "Visual Studio Code" }

  [[protocols.tasks]]
  module = "comandos"
  action = "ejecutar"
  params = { comando = "git status" }
  stop_on_error = true                # opcional; predeterminado false

  [[protocols.tasks]]
  module = "apertura"
  action = "abrir"
  params = { objetivo = "GitHub" }
```

- `id` único. `name` y `aliases` son el catálogo con el que se reconoce el protocolo escrito.
- Cada tarea: `module` (nombre de módulo), `action`, `params` y, opcionalmente, `stop_on_error` y `description` (texto que se muestra; si falta, se genera).
- Los parámetros se escriben como se escribirían en una orden y se resuelven con la misma lógica que las entidades (`IntentRouter.resolve_params`), **en el momento de ejecutar cada tarea**, no al cargar: así una ruta relativa usa el directorio de trabajo que dejó la tarea anterior.
- **Validación al cargar** ([configuracion.md](../Infraestructura/configuracion.md)): módulo y acción existentes y admitidos en protocolos, parámetros obligatorios presentes, `id` y nombres sin repetir. Un protocolo no válido se descarta con un error de configuración; los demás se cargan. La estructura se comprueba al leer el archivo; la parte que depende del registro (`config.validate_protocols`) la aplica el orquestador cada vez que aplica la configuración, al arrancar y al abrir cada sesión.

El archivo predeterminado incluye un protocolo de ejemplo, comentado, para que el usuario lo adapte.

## Ejecución

1. **Panel:** se publica `ProtocolStarted` con todas las tareas, y cada una se crea como subtarea en `pendiente` (RF-53). El asistente dice «Iniciando el protocolo {nombre}.».
2. **Nombre de la sesión:** `ctx.invoke("sesion", "proponer_nombre", {nombre})`. Si el usuario no había fijado el nombre, se le pregunta; con un sí, la sesión toma el nombre del protocolo (RN-04, RF-54). Un no o el vencimiento del tiempo no detienen el protocolo. «Cancelar» sí lo detiene: se dice «Operación cancelada.», no se ejecuta ninguna tarea (tampoco la importancia) y todas quedan en `error` con el motivo «cancelada».
3. **Importancia:** si el protocolo es importante, `ctx.invoke("sesion", "importante_por_protocolo")` (RN-36, RF-55). Nunca se degrada una sesión importante.
4. **Tareas:** en orden (RN-34). Para cada una: se resuelven sus parámetros y se ejecuta con `ctx.invoke(module, action, params)`, es decir, con la misma interfaz y el mismo `run_task` que una orden del usuario. Su estado se actualiza en el panel en cuanto cambia (RF-57).
   - Las respuestas de voz de cada tarea **no se dicen**, salvo los errores y las preguntas de diálogo: un protocolo no debe ser una sucesión de frases.
   - Si una tarea necesita un diálogo (p. ej. una colisión de nombre), lo formula cuando le llega el turno y el protocolo espera (RN-35).
   - Una tarea en `error` no detiene el protocolo, salvo que tenga `stop_on_error = true`; entonces las restantes quedan en `error` con el motivo «protocolo detenido».
   - Un binario externo se espera en línea ([comandos.md](comandos.md)).
5. **Fin:** se publica `ProtocolFinished` y se dice el resumen: «Protocolo {nombre} completado.» o «Protocolo {nombre} terminado con {n} errores.». La tarea del protocolo queda `completado` si todas sus tareas lo están; si no, `error`.

### Otras reglas

- **Uno a la vez (RN-55):** el protocolo ocupa el turno (`IntentSpec.exclusive`): no se puede iniciar otro hasta que termine, y las órdenes escritas mientras tanto esperan en la cola. Las frases de control y las respuestas a un diálogo se atienden igualmente.
- **Panel:** `protocolo`. Muestra el protocolo en curso o el último, con su progreso, o el listado de `listar`.
- **Cancelación:** «cancelar» detiene el protocolo tras la tarea en curso, que se cancela; las restantes quedan en `error` con el motivo «cancelada» (RN-52). El cierre de sesión hace lo mismo (RN-46).
- **Historial:** el protocolo y cada una de sus tareas se registran como actividades de la sesión.

## Datos

Definiciones de la configuración. Tabla `sessions` a través del módulo Sesión. Tabla `session_activities` a través de `run_task`.

## Eventos

`ProtocolStarted`, `ProtocolFinished`, `ProtocolsListed`; `TaskUpdated` de cada subtarea.

## Criterios de aceptación

Con módulos falsos registrados:

- Las tareas se ejecutan en orden y con los parámetros resueltos en su momento.
- Tarea en `error` sin y con `stop_on_error`.
- Renombrado: nombre fijado por el usuario (no pregunta), no fijado con sí, con no y con «cancelar» (detiene el protocolo).
- Protocolo importante con la sesión no importante, ya importante, y con desbordamiento.
- Tarea con diálogo en mitad del protocolo.
- Cancelación a mitad.
- Una prueba recorre todas las acciones con `in_protocols = True` de todos los módulos reales y las invoca desde un protocolo (RNF-19).

## Prohibiciones

- No sobrescribe el nombre de la sesión si lo fijó el usuario.
- No renombra la sesión sin confirmación.
- Nunca degrada una sesión importante.
- El archivo de protocolos es de solo lectura para el asistente.
- Un protocolo no invoca a otro protocolo.
