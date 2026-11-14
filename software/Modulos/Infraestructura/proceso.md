# Proceso y diagnóstico

- **Código:** `main.py`, `process/`, `scripts/`.
- **Origen:** Refuerzo (módulo nuevo).
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Gobernar la vida del proceso: arranque, instancia única, icono de la bandeja, registro de diagnóstico y salida ordenada (RF-75, RF-77, RF-86).

## Arranque

`main()` ejecuta, en orden:

1. Analizar los argumentos (`--preview`, `--ui-debug`, `--log-level`).
2. Elegir el adaptador de plataforma y crear las carpetas de datos, configuración y registro.
3. Configurar el registro de diagnóstico.
4. Adquirir la instancia única; si ya hay otra, registrar y salir sin hacer nada.
5. Cargar la configuración.
6. Comprobar que están todos los modelos (RES-46); si falta alguno, registrar el error, mostrar una notificación de la bandeja y salir.
7. Abrir la base de datos, aplicar las migraciones y recuperar las sesiones interrumpidas (RN-47).
8. Crear la aplicación Qt, las ventanas (ocultas) y el icono de la bandeja.
9. Lanzar el hilo del núcleo: registrar los módulos de acción, cargar la voz y presintetizar las frases del ciclo de vida, cargar `openwakeword`.
10. Lanzar el hilo de audio en modo `WAKE_ONLY`. El asistente queda en `DORMIDO`.
11. Entrar en el bucle de Qt.

`build_app(config, adapters)` construye y conecta todos los componentes sin lanzar hilos ni abrir dispositivos, para poder probar la composición. `main()` solo añade los hilos y los dispositivos reales.

Límite: listo en ≤ 10 s (RNF-25). El transcriptor no se carga en el arranque.

## Inicio automático (Windows)

`scripts/install_startup.ps1` crea un acceso directo en la carpeta Inicio del usuario que lanza `pythonw.exe -m jarvis_assistant` desde el entorno virtual, sin ventana de consola. `uninstall_startup.ps1` lo elimina. Ambos son idempotentes.

## Instancia única

Solo puede haber un proceso del asistente por usuario. Una segunda instancia sale de inmediato y lo registra.

## Icono de la bandeja

`process/tray.py`, con `QSystemTrayIcon`. Es lo único visible en modo dormido.

| Elemento | Comportamiento |
|---|---|
| Icono | Cambia con la actividad: dormido, reposo, escuchando, procesando o hablando, y micrófono no disponible. |
| Texto emergente | «Jarvis: {estado}» y el nombre de la sesión, si hay. |
| Menú: Abrir sesión | Visible en dormido. Publica `OpenSessionRequested`. Permite usar el asistente si la palabra de activación no responde. |
| Menú: Mostrar pantalla | Visible con sesión. Publica `ShowScreenRequested`. |
| Menú: Abrir configuración | Abre la carpeta de configuración en el gestor de archivos. |
| Menú: Abrir registro | Abre la carpeta del registro. |
| Menú: Salir | Publica `QuitRequested`. |

## Salida

Ninguna frase de voz termina el proceso (RF-77). Termina por:

- **Salir** del menú de la bandeja, o
- el **fin de la sesión de Windows** (cierre de sesión, apagado), que Qt comunica a la aplicación.

En ambos casos: si hay sesión, se cierra sin frase ni animación (RN-46, RN-47); se detienen el hilo de audio y los ejecutores; se cierra la base de datos; se libera la instancia única. Límite: 3 s; pasado ese tiempo el proceso termina igualmente y la sesión se recupera en el siguiente arranque (RN-47).

## Registro de diagnóstico

- Módulo `logging` estándar, a un archivo rotativo `jarvis.log` (5 archivos de 1 MB) en la carpeta del registro. Sin consola.
- Formato: fecha, nivel, hilo, componente, mensaje.
- `sys.excepthook`, `threading.excepthook` y el manejador de excepciones de `asyncio` escriben en el registro.
- **Privacidad (RES-48):** nunca audio. El texto transcrito y el de los recordatorios, solo en nivel `DEBUG`.
- Se registran en `INFO`: arranque y versión, cambios de estado de la FSM, cada detección de «Hey Jarvis» con su puntuación, cada intención reconocida con su puntuación (sin el texto), duración de cada transcripción y de cada síntesis, cambios del micrófono, errores de configuración.
- Las marcas de tiempo de inicio de animación y de inicio de audio se registran en `DEBUG` para verificar RNF-22.

## Herramientas

| Guion | Uso |
|---|---|
| `scripts/fetch_models.py` | Descarga los modelos a `models/` y verifica su suma SHA-256 con un manifiesto. Es la única operación del proyecto que usa la red, y solo se ejecuta al instalar. |
| `scripts/diagnose_mic.py` | Lista los dispositivos de entrada, graba 5 s de cada uno, informa del nivel y de la puntuación de «Hey Jarvis», y recomienda dispositivo y API. |
| `scripts/calibrate_wakeword.py` | Mide la activación con la voz del usuario, recomienda ganancia y umbral y, con `--train-verifier`, entrena y valida el verificador personal. Audio solo en memoria. |
| `scripts/measure.py` | Registra CPU y RAM del proceso durante un periodo y extrae las latencias del registro, para verificar los RNF. |

## Criterios de aceptación

- `build_app` con dobles construye el grafo completo y registra todos los módulos (prueba unitaria).
- Una segunda instancia sale sin efectos.
- Falta de un modelo: el proceso sale con un mensaje claro en el registro.
- Salir con una sesión abierta la deja cerrada en la base de datos.
- Las pruebas de los guiones de inicio automático usan un directorio temporal.

## Prohibiciones

- El proceso no abre conexiones de red.
- El proceso no se ejecuta con privilegios de administrador.
- No se muestra ninguna ventana en modo dormido; solo el icono de la bandeja.
