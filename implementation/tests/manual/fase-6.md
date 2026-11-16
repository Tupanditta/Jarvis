# Lista manual de la fase 6. Protocolos

Se recorre en el equipo de referencia al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `--preview` muestra el panel «Protocolo»: «modo trabajo» con tres tareas que pasan de
      `pendiente` a su estado una a una, la barra de progreso llena y, después, el listado con
      dos protocolos (el primero con estrella).
- [ ] La ventana «Protocolo» se abre desde el dock y, sin protocolo en curso, pide el listado.
- [ ] En `%APPDATA%\Jarvis\config\protocols.toml` (o la carpeta de configuración del equipo),
      definir **un protocolo real del usuario con cinco tareas de tres módulos**, marcado como
      importante, con un alias. Por ejemplo: `comandos.cd`, `apertura.abrir` (una aplicación),
      `apertura.abrir` (una página), `comandos.ejecutar` (`git status`) y
      `recordatorio.crear` (`texto` y `avisos = "en una hora"`).

## Ejecutar (CU-13)

- [ ] Abrir una sesión nueva (la configuración se relee al abrirla). «Protocolo {nombre}»: el
      panel se abre con las cinco tareas en `pendiente` y se dice «Iniciando el protocolo …».
- [ ] Pregunta «¿Quiere llamar a esta sesión {nombre}?». «Sí»: la sesión toma ese nombre y pasa
      a importante (estrella en el historial).
- [ ] Las tareas se ejecutan en orden; cada una cambia de estado en el panel en cuanto termina
      (RNF-14, sin retardo apreciable) y no se dice ninguna frase intermedia.
- [ ] Al terminar: «Protocolo {nombre} completado.». «Qué he hecho» muestra el protocolo y sus
      tareas en el historial.
- [ ] Con el alias también se lanza.
- [ ] Desde la ventana, un clic en un protocolo del listado lo ejecuta.

## Flujos alternativos

- [ ] Sesión nombrada antes con «Llama a la sesión pruebas»: el protocolo no pregunta y el nombre
      no cambia.
- [ ] Ante la pregunta del nombre, «No», «cancelar» y 20 s sin respuesta: el nombre no cambia y
      el protocolo sigue.
- [ ] Una tarea que falla (p. ej. `cd` a una carpeta que no existe): se dice su motivo, queda en
      `error` con el motivo debajo y el protocolo sigue. Al final: «Protocolo … terminado con
      1 error.».
- [ ] Con `stop_on_error = true` en esa tarea: las restantes quedan en `error` con «protocolo
      detenido».
- [ ] Una tarea `creacion.crear_archivo` con un nombre que ya existe: el protocolo pregunta otro
      nombre y espera la respuesta.
- [ ] «Cancelar» durante una tarea larga: la tarea en curso y las restantes quedan en `error`
      con «cancelada»; se dice «Cancelado.».
- [ ] «Buenas noches Jarvis» durante el protocolo: las tareas sin terminar quedan con «sesión
      cerrada».
- [ ] Una orden escrita mientras el protocolo se ejecuta espera en la cola hasta que termina.
- [ ] «Protocolo vacaciones»: «No encuentro vacaciones.».
- [ ] «Qué protocolos hay»: muestra el listado y dice cuántos hay.

## Validación de `protocols.toml`

- [ ] Un protocolo con una acción que no existe, otro con `protocolos.ejecutar` y otro sin un
      parámetro obligatorio: al abrir la sesión se avisa del error de configuración de
      «protocols»; el registro indica protocolo, tarea y motivo; los protocolos válidos siguen
      disponibles.
