# Jarvis: instalación y uso

Asistente personal local para Windows. El usuario escribe sus órdenes en una caja de texto y el asistente responde con voz. Todo funciona sin conexión; la única operación que usa la red es la descarga de la voz durante la instalación.

La especificación completa está en [`../software/`](../software/README.md).

## Requisitos

- Windows 10 u 11, sin necesidad de GPU dedicada.
- Python 3.11 o posterior, en el `PATH`.
- Opcional: [*Everything*](https://www.voidtools.com/) con su línea de órdenes `es.exe`, para buscar en todo el disco. Sin él, la búsqueda recorre las carpetas con un límite.

## Instalación

Desde la carpeta `implementation/`, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -e .[dev]
.\.venv\Scripts\python.exe scripts\fetch_models.py       # descarga y verifica la voz (única operación con red)
.\.venv\Scripts\python.exe -m jarvis_assistant --preview  # comprueba la interfaz, sin voz ni modelos
```

`fetch_models.py` deja la voz de Piper en `models/piper/` y comprueba su suma SHA-256. Si se interrumpe, se vuelve a ejecutar: los archivos correctos no se descargan otra vez.

## Arrancar y parar

```powershell
.\scripts\start_jarvis.ps1            # sin consola; el proceso queda en la bandeja
.\scripts\start_jarvis.ps1 -Console   # con consola, para ver errores
.\scripts\stop_jarvis.ps1             # termina el proceso
```

Solo se ejecuta una instancia: lanzar otra no tiene efecto. Para salir de forma ordenada, use «Salir» en el menú de la bandeja.

## Inicio automático

```powershell
.\scripts\install_startup.ps1     # crea Jarvis.lnk en la carpeta Inicio del usuario
.\scripts\uninstall_startup.ps1   # lo elimina
```

Ambos guiones se pueden ejecutar varias veces sin efectos adicionales. No necesitan permisos de administrador.

## Carpetas del usuario

| Contenido | Carpeta |
|---|---|
| Configuración (TOML) | `%APPDATA%\Jarvis\config\` |
| Base de datos | `%LOCALAPPDATA%\Jarvis\data\jarvis.db` |
| Registro de diagnóstico | `%LOCALAPPDATA%\Jarvis\logs\jarvis.log` |

En el primer arranque se copian a la carpeta de configuración los archivos predeterminados, con cada clave explicada. Los cambios se aplican al abrir la siguiente sesión. Si un archivo es inválido, el asistente usa la versión anterior de ese archivo y lo dice. Referencia de claves: [configuracion.md](../software/Modulos/Infraestructura/configuracion.md).

Desde el menú de la bandeja se abren las carpetas de configuración y de registro.

## Diagnóstico y medidas

```powershell
.\.venv\Scripts\python.exe -m jarvis_assistant --log-level DEBUG   # marcas de tiempo para las medidas
.\.venv\Scripts\python.exe scripts\measure.py registro            # latencias (RNF-03), sincronía (RNF-22), arranque (RNF-25)
.\.venv\Scripts\python.exe scripts\measure.py proceso --estado dormido   # CPU y RAM durante 60 s (RNF-04)
.\.venv\Scripts\python.exe scripts\measure.py proceso --estado reposo
.\.venv\Scripts\python.exe scripts\measure.py proceso --estado uso       # RAM en uso (RNF-05)
```

`measure.py` sale con 0 si todo lo medido cumple y con 1 si algo no cumple. `--ui-debug` muestra el contador de frames (RNF-21).

## Privacidad

El asistente no abre conexiones de red ni captura audio. Las pruebas automáticas fallan si el código intenta abrir un socket. El texto de las órdenes y de los recordatorios solo aparece en el registro en nivel `DEBUG`. Para comprobarlo en el equipo, siga la lista de [`tests/manual/fase-7.md`](tests/manual/fase-7.md).

## Desarrollo

```powershell
.\.venv\Scripts\python.exe -m pytest                  # sin hardware ni modelos, en paralelo (-n 0: en serie)
.\.venv\Scripts\python.exe -m pytest -m models        # con la voz real
.\.venv\Scripts\python.exe -m pytest -m hardware      # con el altavoz real
.\.venv\Scripts\python.exe -m ruff check src scripts tests
```

Los paquetes se instalan siempre en el entorno virtual: `.\.venv\Scripts\pip.exe install <paquete>`.

## Desinstalar

1. Ejecute `.\scripts\uninstall_startup.ps1`.
2. Salga del asistente desde la bandeja.
3. Borre la carpeta `implementation\` y, si no quiere conservar los datos, `%APPDATA%\Jarvis\` y `%LOCALAPPDATA%\Jarvis\`.
