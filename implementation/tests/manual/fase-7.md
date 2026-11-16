# Lista manual de la fase 7. Endurecimiento

Se recorre en el equipo de referencia al cerrar la fase
([plan-implementacion.md](../../../software/plan-implementacion.md)). Marque cada punto y anote
la fecha y la cifra medida. El registro está en `%LOCALAPPDATA%\Jarvis\logs\jarvis.log`.

## Preparación

- [ ] `.\.venv\Scripts\python.exe -m pytest` en verde en ≤ 60 s y
      `.\.venv\Scripts\python.exe -m ruff check src scripts tests` sin avisos (RNF-24).
- [ ] `.\.venv\Scripts\python.exe -m pytest -n 0 --cov=jarvis_assistant` muestra ≥ 80 % en
      `core/`, `intent_router/` y `action_modules/` (RNF-24).
- [ ] `-m models` y `-m hardware` en verde.

## Rendimiento (T-7.1)

Arrancar con `--log-level DEBUG` (`.\scripts\start_jarvis.ps1 -Console` y añadir el argumento,
o `python -m jarvis_assistant --log-level DEBUG`).

- [ ] Dormido, sin tocar nada: `python scripts\measure.py proceso --estado dormido` cumple
      (CPU media ≤ 2 %, RAM ≤ 400 MB; RNF-04).
- [ ] En reposo («Gracias Jarvis»): `measure.py proceso --estado reposo` cumple (RNF-04).
- [ ] En uso, escribiendo órdenes de todos los módulos durante la medida:
      `measure.py proceso --estado uso` cumple (RAM ≤ 600 MB; RNF-05).
- [ ] Tras una sesión con al menos 30 órdenes de todos los módulos y varios cambios de estado:
      `measure.py registro` cumple RNF-03 (mediana ≤ 0,5 s, p95 ≤ 1 s, activación → animación
      ≤ 0,5 s), RNF-22 (≤ 150 ms) y RNF-25 (≤ 10 s).
- [ ] Con `--ui-debug`, el contador de frames no baja de 30 fps y ronda 60 fps durante las
      animaciones y mientras se atiende una orden (RNF-21). Cada transición dura 2 s ± 0,1 s.
- [ ] Si algo no cumple: bajar `ui.quality` a `medium` y repetir. Anotar el valor elegido.

## Uso real (T-7.2)

- [ ] Varios días de uso diario. Cada orden no reconocida que debería haberlo sido se añade al
      juego de frases de prueba (`tests/unit/intent_router/`) y se ajustan alias o umbrales.
- [ ] RNF-31: 30 órdenes escritas con entidades (rutas, nombres con extensión, comandos con
      opciones); ≥ 95 % resueltas bien a la primera. Anotar las que fallan.
- [ ] RNF-11 sobre el juego ampliado: `pytest tests/unit/intent_router` en verde.
- [ ] Confirmar tras el uso real que 120 s (`input.inactivity_to_idle_seconds`) es cómodo; si
      cambia, cambiarlo a la vez en `config.py`, `settings.toml` y `configuracion.md`.

## Robustez (T-7.3)

- [ ] Sin altavoz (desactivado en Sonido de Windows): la sesión funciona, los subtítulos
      muestran las respuestas y el registro dice «No se puede abrir el dispositivo de salida».
- [ ] Con `jarvis.db` sustituida por un archivo de texto: el asistente arranca, aparece
      `jarvis.db.corrupt-<fecha>` y el registro dice «dañada».
- [ ] Con `settings.toml` inválido al arrancar: arranca con los predeterminados de ese archivo y
      lo registra. Al corregirlo y abrir sesión, se usa el nuevo.
- [ ] Sin `models\piper\…onnx`: el proceso sale, la bandeja avisa y el registro dice qué falta y
      que se ejecute la descarga de modelos.

## Revisión visual (T-7.4)

- [ ] Lista de [Interfaz/README.md](../../../software/Interfaz/README.md), sección 11, completa.
- [ ] `ui.reduce_motion = true`: sin movimiento continuo; las transiciones siguen siendo
      reconocibles.
- [ ] `ui.quality` en `high`, `medium` y `low`: sin errores y con el aspecto de cada nivel.

## Instalación y privacidad (T-7.5)

- [ ] En un usuario de Windows limpio, seguir [README.md](../../README.md) de principio a fin sin
      pasos que falten.
- [ ] `install_startup.ps1`, reiniciar sesión de Windows: el asistente arranca en la bandeja, en
      dormido. `uninstall_startup.ps1` lo retira.
- [ ] Con la red desactivada, recorrer todas las funciones: todo funciona (RNF-02).
- [ ] Con un monitor de conexiones (p. ej. `Get-NetTCPConnection -OwningProcess <pid>` repetido
      o Monitor de recursos → Red) durante una sesión que recorra todas las funciones: 0
      conexiones del proceso (RNF-01, RF-75).
- [ ] En nivel `INFO`, el registro no contiene el texto de ninguna orden ni recordatorio.
