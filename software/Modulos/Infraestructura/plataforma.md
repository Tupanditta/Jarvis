# Plataforma

- **Código:** `os_adapters/`.
- **Origen:** Refuerzo (módulo nuevo).
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Aislar todo lo que depende del sistema operativo detrás de una interfaz única, de modo que el resto del código sea portable y que añadir Linux sea escribir un adaptador, sin tocar los módulos (RES-06).

## Comportamiento

- `base.py` define `PlatformAdapter` como `Protocol`. `main.py` elige el adaptador según `sys.platform` y lo inyecta.
- La versión 1 implementa `WindowsAdapter`. `LinuxAdapter` se construye en la última fase.
- Las pruebas usan `FakePlatform` (`tests/fakes/`), que registra las llamadas y simula ventanas y resultados.
- Las llamadas que pueden tardar (búsqueda, descubrimiento de aplicaciones, espera de una ventana) son corrutinas o se ejecutan con `asyncio.to_thread`.
- Las APIs de Windows se llaman con `ctypes`.

## Interfaz

```python
class PlatformAdapter(Protocol):
    # Carpetas
    def data_dir(self) -> Path: ...
    def config_dir(self) -> Path: ...
    def log_dir(self) -> Path: ...
    def default_places(self) -> Mapping[str, Path]: ...        # escritorio, documentos, descargas…

    # Lanzamiento
    async def launch_app(self, target: AppTarget) -> LaunchHandle: ...
    async def open_url_in_edge(self, url: str) -> LaunchHandle: ...   # lanza EdgeNotFound si no está
    async def open_folder(self, path: Path) -> LaunchHandle: ...
    async def open_terminal(self, cwd: Path) -> LaunchHandle: ...
    async def open_with_default(self, path: Path) -> None: ...
    def discover_apps(self) -> Sequence[DiscoveredApp]: ...

    # Ventanas externas
    async def wait_for_window(self, handle: LaunchHandle, timeout: float = 10) -> WindowRef | None: ...
    def window_exists(self, ref: WindowRef) -> bool: ...
    def focus_window(self, ref: WindowRef) -> bool: ...
    @property
    def can_focus_windows(self) -> bool: ...

    # Ventanas propias
    def bring_own_window_to_front(self, native_id: int) -> None: ...
    def make_non_activating(self, native_id: int) -> None: ...

    # Búsqueda
    async def indexed_search(self, query: str, kind: SearchKind, limit: int) -> SearchOutcome | None: ...
        # None = herramienta indexada no disponible

    # Proceso
    def acquire_single_instance(self) -> bool: ...
```

## Implementación por sistema

| Operación | Windows 11 (versión 1) | Linux (fase final) |
|---|---|---|
| Carpetas de datos, configuración y registro | `%LOCALAPPDATA%\Jarvis\data`, `%APPDATA%\Jarvis\config`, `%LOCALAPPDATA%\Jarvis\logs` | `~/.local/share/jarvis`, `~/.config/jarvis`, `~/.local/state/jarvis` |
| Lugares predeterminados | Carpetas conocidas del sistema (`SHGetKnownFolderPath`), que respetan la redirección a OneDrive | `xdg-user-dir` |
| Lanzar una aplicación | `subprocess.Popen` para ejecutables; `os.startfile` para accesos directos | `subprocess.Popen`; `gtk-launch` para `.desktop` |
| Descubrir aplicaciones | Accesos directos `.lnk` de las dos carpetas del menú Inicio (usuario y sistema), por su nombre | Archivos `.desktop` de `/usr/share/applications` y `~/.local/share/applications` |
| Abrir una URL en Edge | Ruta de `msedge.exe` del registro (`App Paths`) o de las rutas habituales; `Popen([msedge, url])` | `microsoft-edge` del `PATH` |
| Abrir una carpeta | `explorer.exe <ruta>` | `xdg-open <ruta>` |
| Abrir una terminal | `wt.exe -d <cwd>`; si no existe, `cmd.exe` en una consola nueva | `x-terminal-emulator` con el directorio de trabajo |
| Abrir con la aplicación predeterminada | `os.startfile` | `xdg-open` |
| Localizar la ventana de lo lanzado | Lista de ventanas de primer nivel visibles antes de lanzar (`EnumWindows`); después se sondea cada 250 ms, hasta 10 s, una ventana nueva, prefiriendo la del proceso lanzado y, si no, la primera nueva cuyo título contenga el nombre | X11: `wmctrl -l -p`; Wayland: no disponible |
| Traer una ventana al frente | `ShowWindow(SW_RESTORE)` si está minimizada y `SetForegroundWindow`; el clic del usuario en el HUD autoriza el cambio. Si falla, la ventana parpadea en la barra de tareas (`FlashWindowEx`) y devuelve `False` | X11: `wmctrl -i -a`; Wayland: `can_focus_windows = False` |
| Pantalla de sesión al frente | `SetWindowPos(HWND_TOPMOST)` y, 1 s después, `HWND_NOTOPMOST` | Petición de activación de Qt |
| Ventana que no se activa | Estilo extendido `WS_EX_NOACTIVATE`, además de los indicadores de Qt | Indicadores de Qt |
| Búsqueda indexada | `es.exe` (*Everything*), buscado en el `PATH` y en su carpeta de instalación; salida con rutas completas | `fd` |
| Instancia única | Mutex con nombre en `Local\` | Archivo de bloqueo con `fcntl` |
| Inicio automático | Acceso directo en la carpeta Inicio del usuario que lanza `pythonw.exe -m jarvis_assistant` (`scripts/install_startup.ps1`) | Archivo `.desktop` en `~/.config/autostart` |

**Traer al frente en Wayland:** cuando `can_focus_windows` es `False`, el botón «traer al frente» no se muestra y la orden de voz responde «No está disponible en este sistema».

## Criterios de aceptación

- `FakePlatform` cumple el `Protocol` (prueba de conformidad).
- Ningún archivo fuera de `os_adapters/`, `ui/`, `process/` y `scripts/` importa `ctypes`, `winreg` ni usa `sys.platform` (prueba automática de importaciones).
- Con marcador `hardware`, en Windows: abrir el Bloc de notas, localizar su ventana, traerla al frente y cerrarla.

## Prohibiciones

- Los módulos de acción no llaman a APIs del sistema operativo directamente.
- El adaptador no contiene reglas de negocio: solo ejecuta operaciones y devuelve resultados.
- No se requieren privilegios de administrador.
