# Configuración

- **Código:** `config.py`, `resources/config_defaults/`.
- **Origen:** Refuerzo (módulo nuevo).
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Reunir en archivos editables todo lo que el usuario puede querer ajustar sin tocar el código (RNF-26): catálogos, lugares, binarios permitidos, protocolos, estructuras, alias, umbrales y tiempos.

## Comportamiento

- **Formato:** TOML, leído con `tomllib`. El asistente nunca escribe estos archivos (RES-36).
- **Ubicación:** `%APPDATA%\Jarvis\config\` en Windows. En el primer arranque se copian ahí los archivos predeterminados de `resources/config_defaults/`, con comentarios que explican cada clave.
- **Valores predeterminados:** toda clave ausente toma el valor predeterminado del código. Un archivo vacío es válido.
- **Validación:** al cargar, cada archivo se convierte en `dataclass` inmutables con comprobación de tipos y rangos. Un error indica archivo, clave y motivo. Una clave o sección desconocida solo produce un aviso: un `settings.toml` anterior, con las secciones `[audio]` y `[stt]` de la entrada por voz retirada, se sigue cargando.
- **Carga:** al arrancar el proceso y al abrir cada sesión (RF-96). Si al recargar un archivo es inválido, se conserva la configuración anterior de ese archivo, se publica `ConfigReloadFailed` y el asistente dice, tras la frase de apertura, «Hay un error en la configuración de {archivo}. Uso la anterior.». Si es inválido en el arranque, se usan los valores predeterminados de ese archivo y se registra.
- **Protocolos:** al cargar, cada tarea se valida contra el registro de intenciones: el módulo y la acción deben existir y admitir protocolos, y los parámetros obligatorios deben estar presentes.

## Archivos

### `settings.toml`

| Clave | Predeterminado | Significado |
|---|---|---|
| `input.inactivity_to_idle_seconds` | `30` | Segundos sin escribir que pasan a reposo (5–600). |
| `tts.voice` | `"es_ES-davefx-medium"` | Voz de Piper. |
| `tts.volume` | `1.0` | Volumen (0–1). |
| `tts.cache_size` | `64` | Frases en caché. |
| `router.intent_threshold` | `80` | Umbral de intención. |
| `router.wake_threshold` | `80` | Umbral de la frase de activación «Hey Jarvis». |
| `router.control_threshold` | `80` | Umbral de las frases de control. |
| `router.idle_closing_threshold` | `85` | Umbral del cierre en reposo. |
| `router.catalog_threshold` | `75` | Umbral de entidades de lista. |
| `router.path_threshold` | `80` | Umbral de carpetas escritas. |
| `router.default_hour` | `9` | Hora de una fecha sin hora. |
| `dialogue.timeout_seconds` | `20` | Tiempo de espera de una respuesta. |
| `dialogue.max_collisions` | `3` | Colisiones seguidas antes de cancelar. |
| `commands.default_timeout_seconds` | `120` | Tiempo máximo de un binario. |
| `commands.output_lines` | `200` | Líneas de salida mostradas. |
| `search.max_results` | `10` | Resultados mostrados. |
| `search.fallback_timeout_seconds` | `5` | Corte de la búsqueda limitada. |
| `reminders.snooze_minutes` | `10` | Posposición por defecto. |
| `reminders.max_triggers` | `5` | Fechas de aviso por recordatorio. |
| `reminders.autoconfirm_seconds` | `300` | Plazo de autoconfirmación. |
| `ui.hud_corner` | `"top-right"` | Esquina del HUD. |
| `ui.hud_collapse_seconds` | `8` | Inactividad antes de contraer el HUD. |
| `ui.quality` | `"high"` | `high`, `medium` o `low`: cantidad de partículas y efectos. |
| `ui.reduce_motion` | `false` | Sustituye las animaciones por fundidos. |
| `startup.open_session_on_start` | `false` | Solo desarrollo: abrir sesión al arrancar. |
| `logging.level` | `"INFO"` | Nivel del registro. |
| `user.name` | `""` | Nombre del usuario que dice «preséntate». Vacío: no lo dice. |

### `catalog.toml`

```toml
discover_installed_apps = true      # añadir las aplicaciones del menú Inicio

[[apps]]
name = "Visual Studio Code"
aliases = ["code", "vs code", "el editor"]
path = "C:/Users/…/Code.exe"        # ejecutable, acceso directo o nombre en el PATH
args = []

[[pages]]
name = "GitHub"
aliases = ["git hub"]
url = "https://github.com"
```

### `places.toml`

Lugares con nombre para escribir rutas. Escritorio, Documentos, Descargas, Imágenes, Música y Vídeos se añaden solos con las carpetas reales del sistema.

```toml
[places]
proyectos = "D:/Proyectos"
universidad = "D:/Universidad"
```

### `commands.toml`

Lista cerrada de binarios (RN-45).

```toml
[[binaries]]
name = "git"
executable = "git"                  # nombre en el PATH o ruta absoluta
aliases = ["guit"]
timeout_seconds = 60

[[binaries]]
name = "gcc"
executable = "gcc"
aliases = ["ge ce ce"]
```

Predeterminados: `git`, `gcc`, `g++`, `make`, `python`, `pip`, `node`, `npm`.

### `aliases.toml`

Sustituciones aplicadas al normalizar el texto escrito ([enrutador-intenciones.md](enrutador-intenciones.md)): abreviaturas y formas alternativas de escribir una palabra.

```toml
[aliases]
"ce de" = "cd"
"ele ese" = "ls"
"guit" = "git"
```

### `protocols.toml`

Ver [protocolos.md](../Accion/protocolos.md).

### `structures.toml`

Estructuras de carpetas predefinidas (RF-97).

```toml
[[structures]]
name = "proyecto python"
folders = ["src", "tests", "docs", "scripts"]
```

## Interfaz

```python
@dataclass(frozen=True)
class Config:
    settings: Settings
    catalog: Catalog
    places: Mapping[str, Path]
    binaries: tuple[Binary, ...]
    aliases: Mapping[str, str]
    protocols: tuple[ProtocolDef, ...]
    structures: tuple[StructureDef, ...]

def load(config_dir: Path, *, previous: Config | None = None) -> tuple[Config, list[ConfigError]]: ...
```

## Criterios de aceptación

- Archivos ausentes, vacíos, con claves desconocidas (aviso), con tipos erróneos y fuera de rango: pruebas unitarias.
- Los archivos predeterminados del paquete se cargan sin errores.
- Recarga con un archivo inválido: conserva el anterior y devuelve el error.

## Prohibiciones

- El asistente no escribe en los archivos de configuración.
- No se guardan en la configuración sesiones, actividades ni recordatorios (RES-33).
