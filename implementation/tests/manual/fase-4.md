# Lista manual de la fase 4. Diálogo de varios turnos

Se recorre en el equipo de referencia al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde y `.\.venv\Scripts\ruff.exe check .` sin avisos.
- [ ] `--preview` muestra la tarjeta de diálogo (pregunta, sesión 12, «Sí», «No», «Cancelar» y
      la barra que se vacía) en la pantalla y en el HUD, y el orbe en ámbar («esperando»).

## Creación (CU-09)

- [ ] «Crea el archivo notas punto txt en documentos» crea `notas.txt` vacío y la voz dice la
      carpeta real.
- [ ] «Crea la carpeta apuntes» sin ubicación la crea en el directorio de trabajo (tras «ve a
      …», en esa carpeta).
- [ ] «Crea las carpetas backend barra src barra modelos» crea la ruta; con `backend` ya
      existente, la reutiliza sin tocar lo que había dentro.
- [ ] «Crea la estructura proyecto python llamada analizador» crea la raíz y sus subcarpetas.
- [ ] **Colisión resuelta escribiendo la respuesta:** repetir la primera orden. El asistente dice
      «Ya existe notas.txt…», la tarjeta de diálogo aparece y el orbe pasa a ámbar. Escribir
      «notas dos punto txt», **sin** «Hey Jarvis»: se crea `notas dos.txt` y `notas.txt` conserva
      su contenido y su fecha.
- [ ] Tres colisiones seguidas: «Operación cancelada.»; no se crea nada.
- [ ] **Cancelación:** ante la pregunta, escribir «cancelar»: «Operación cancelada.» una sola vez;
      la tarea queda en error con el motivo «cancelada».
- [ ] **Tiempo agotado:** ante la pregunta, no escribir nada. A los 20 s (contados desde que
      termina la pregunta) se cancela; «Hey Jarvis» durante la espera reinicia la cuenta sin
      decir nada.
- [ ] «Crea el archivo x en {carpeta inexistente}»: «La carpeta … no existe.»; no se crea nada.
- [ ] «Abre la carpeta {carpeta inexistente}» no crea ninguna carpeta.

## Sesión e historial (CU-10)

- [ ] «Llama a la sesión práctica de redes»: la barra superior muestra el nombre nuevo.
- [ ] «Marca la sesión como importante»: aparece la estrella. «La sesión no es importante» la
      quita.
- [ ] Con 10 sesiones importantes, marcar la actual: aviso de desbordamiento con el nombre de la
      que sale; al desmarcarla, la desplazada vuelve a ser importante.
- [ ] **Eliminación de una sesión:** «Muestra el historial», «Elimina la sesión {id}»: el panel
      muestra solo esa sesión y pregunta. «Sí»: «Sesión {id} eliminada.» y ya no aparece en el
      historial. La fila sigue en la base de datos con `is_deleted = 1`.
- [ ] Ante la pregunta, «No», «cancelar» y 20 s sin respuesta: no se elimina.
- [ ] Una respuesta no válida («quizá»): «No le he entendido.» y la pregunta otra vez; a la
      segunda, «Operación cancelada.».
- [ ] «Elimina la sesión {actual}» y «elimina la sesión 999»: error sin pregunta.

## Cierre y cancelación con diálogo abierto (T-4.6)

- [ ] Ante una pregunta, «Gracias Jarvis»: reposo, sin crear ni eliminar nada.
- [ ] Ante una pregunta y con un `git status` largo en marcha, «Buenas noches Jarvis»: la tarjeta
      desaparece, las dos tareas quedan en error y la sesión se cierra. «Hey Jarvis» abre una
      sesión nueva sin pregunta pendiente.
- [ ] Un aviso que llega durante la pregunta se dice después de responderla.
