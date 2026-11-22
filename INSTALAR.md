# Instalar Jarvis

Procedimiento completo para instalar Jarvis en Windows. Lo puede seguir una persona o ejecutarlo un agente de IA de principio a fin.

## Lo esencial

- **La forma más fácil:** pida a su agente de IA (Claude Code, Codex, Copilot u otro con acceso a la terminal): «Instala Jarvis en este equipo siguiendo INSTALAR.md». Usted solo responde a sus preguntas y aprueba los permisos que pida.
- **Qué necesita:** Windows 10 u 11 y Python 3.11 o posterior. El resto se instala solo.
- **Red solo durante la instalación:** después, Jarvis funciona sin conexión.
- **Al terminar:** escriba «Hey Jarvis» en la ventana de Jarvis. Siga con [MANUAL.md](MANUAL.md).
- **¿Ya tiene la versión 1.0?** Siga [Actualizar desde una versión anterior](#actualizar-desde-una-versión-anterior).

**Si es usted un agente**, siga los pasos en orden. Cada paso dice cómo comprobar que ha salido bien. No pase al siguiente si la comprobación falla: consulte [Problemas frecuentes](#problemas-frecuentes).

## Resumen

| Paso | Qué hace | Necesita red |
|---|---|---|
| [0](#0-preguntar-al-usuario) | Preguntar al usuario sus preferencias. | No |
| [1](#1-comprobar-los-requisitos) | Comprobar Windows, Python y Git. Instalar lo que falte. | Solo si falta algo |
| [2](#2-obtener-el-código) | Obtener el código. | Sí |
| [3](#3-crear-el-entorno-e-instalar-las-dependencias) | Crear el entorno virtual e instalar las dependencias. | Sí |
| [4](#4-descargar-la-voz) | Descargar la voz. | Sí |
| [5](#5-arrancar-y-comprobar) | Arrancar Jarvis y comprobar que funciona. | No |
| [6](#6-inicio-automático-opcional) | Inicio automático con Windows (opcional). | No |
| [7](#7-personalizar-opcional) | Personalizar (opcional). | No |
| [8](#8-informar-al-usuario) | Informar al usuario. | No |

Tiempo aproximado: de 5 a 15 minutos, según la conexión. Se descargan varios cientos de MB; la mayor parte es PySide6 (Qt).

## Reglas para el agente

1. Ejecute todas las órdenes en **PowerShell**. Las rutas usan `\`.
2. Instale los paquetes de Python **solo dentro del entorno virtual**: `.\.venv\Scripts\pip.exe install …`. Nunca use `pip install` global.
3. No pida permisos de administrador. Nada de este procedimiento los necesita, salvo instalar Python o Git para todo el equipo, cosa que se evita con `--scope user`.
4. Ejecute los guiones `.ps1` con `powershell -NoProfile -ExecutionPolicy Bypass -File …`. `Bypass` solo afecta a esa ejecución; no cambie la política del sistema.
5. No escriba datos del usuario en el repositorio. Su configuración va en `%APPDATA%\Jarvis\config\` ([PERSONALIZAR.md](PERSONALIZAR.md)). No pida ni ponga contraseñas de perfiles: las pone el usuario en la ventana de configuración.
6. No haga commits ni cambie la configuración de Git.

## 0. Preguntar al usuario

Haga estas preguntas **todas juntas, al principio**, para no interrumpir después:

1. ¿En qué carpeta quiere instalar Jarvis? (Predeterminado: `%USERPROFILE%\Jarvis`. Si el repositorio ya está descargado, use esa carpeta.)
2. ¿Quiere que Jarvis arranque solo al iniciar Windows? (Sí / No)
3. ¿Qué nombre quiere que use Jarvis al presentarse? (Opcional.)
4. ¿Quiere instalar *Everything* para buscar archivos en todo el disco? (Opcional. Sin él, la búsqueda se limita a sus carpetas personales.)
5. ¿Quiere añadir ya sus aplicaciones, páginas web o carpetas favoritas? (Opcional. Se puede hacer después.)

## 1. Comprobar los requisitos

### Windows

```powershell
[System.Environment]::OSVersion.Version
```

Debe ser Windows 10 u 11 (versión `10.0`). Jarvis no funciona en Linux ni en macOS.

### Python 3.11 o posterior

```powershell
py -3 --version
python --version
```

Basta con que una de las dos órdenes muestre `Python 3.11` o posterior. Use para los pasos siguientes la orden que funcione (`py -3` o `python`). La versión probada es la 3.11.

- Si `python` abre Microsoft Store o no muestra nada, es el acceso directo de la tienda, no un Python real.
- Si no hay ninguna versión válida, instálela para el usuario actual:

  ```powershell
  winget install --id Python.Python.3.11 -e --scope user --accept-package-agreements --accept-source-agreements
  ```

  Después abra una **terminal nueva**, para que se actualice el `PATH`, y repita la comprobación.

### Git

```powershell
git --version
```

Solo hace falta si el código no está descargado todavía. Si falta:

```powershell
winget install --id Git.Git -e --scope user --accept-package-agreements --accept-source-agreements
```

Abra una terminal nueva después de instalarlo.

## 2. Obtener el código

Si el repositorio ya está en el equipo (por ejemplo, porque el agente se ejecuta dentro de él), salte este paso.

```powershell
git clone <URL-del-repositorio> "$env:USERPROFILE\Jarvis"
```

`<URL-del-repositorio>` es la dirección del repositorio en GitHub (botón «Code»). Sustituya la carpeta de destino por la que eligió el usuario.

**Comprobación:** existe el archivo `implementation\pyproject.toml` dentro de la carpeta.

## 3. Crear el entorno e instalar las dependencias

Desde la carpeta `implementation\` del repositorio:

```powershell
cd "<carpeta-del-repositorio>\implementation"
py -3.11 -m venv .venv          # o: python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -e .
```

`-e .` instala solo lo necesario para usar Jarvis. Para desarrollar y ejecutar las pruebas, use `-e .[dev]` ([implementation/README.md](implementation/README.md)).

**Comprobación:**

```powershell
.\.venv\Scripts\python.exe -c "import jarvis_assistant, PySide6, piper, tomlkit, cryptography; print('OK')"
```

Debe mostrar `OK`.

## 4. Descargar la voz

```powershell
.\.venv\Scripts\python.exe scripts\fetch_models.py
```

Descarga la voz `es_ES-davefx-medium` a `implementation\models\piper\` y comprueba su suma SHA-256. Es la única vez que Jarvis usa la red.

**Comprobación:** la última línea es `Modelos completos en …` y la orden termina con código 0. Si falla, vuelva a ejecutarla: los archivos ya correctos no se descargan otra vez.

## 5. Arrancar y comprobar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_jarvis.ps1
```

Jarvis arranca sin consola. Aparecen un icono en la bandeja del sistema y la pantalla de sesión. En el primer arranque crea sus carpetas y copia la configuración predeterminada a `%APPDATA%\Jarvis\config\`.

**Comprobación**, unos 20 segundos después:

```powershell
$log = "$env:LOCALAPPDATA\Jarvis\logs\jarvis.log"
$ultimo = (Select-String -Path $log -Pattern 'arranca$' -Encoding UTF8 | Select-Object -Last 1).LineNumber
Get-Content $log -Encoding UTF8 | Select-Object -Skip ($ultimo - 1)
```

- Debe aparecer una línea con `Listo en … s` después de la línea `Jarvis … arranca`.
- No debe aparecer `Faltan modelos` ni ninguna línea `ERROR`. Excepción: las líneas `ERROR` que terminan en `clave desconocida` son avisos inofensivos de una configuración de una versión anterior.

Si no aparece `Listo en`, arranque con consola para ver el error:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop_jarvis.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_jarvis.ps1 -Console
```

## 6. Inicio automático (opcional)

Solo si el usuario lo ha pedido:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_startup.ps1
```

**Comprobación:** existe `Jarvis.lnk` en `shell:startup`:

```powershell
Test-Path "$([Environment]::GetFolderPath('Startup'))\Jarvis.lnk"
```

Debe mostrar `True`.

## 7. Personalizar (opcional)

Haga solo lo que el usuario haya pedido en el paso 0. Siga [PERSONALIZAR.md](PERSONALIZAR.md), sección «Instrucciones para agentes».

- **Nombre:** en `%APPDATA%\Jarvis\config\profiles.toml`, añada un perfil con `user_name = "<nombre>"` ([PERSONALIZAR.md](PERSONALIZAR.md#9-perfiles-profilestoml)). El usuario también puede hacerlo después en la ventana de configuración.
- **Everything:** instálelo desde [voidtools.com](https://www.voidtools.com/) junto con su línea de órdenes `es.exe`, que debe quedar en el `PATH`. Si no está seguro de cómo hacerlo, deje que el usuario lo instale.
- **Aplicaciones, páginas y carpetas:** añádalas a `catalog.toml` y `places.toml` como explica PERSONALIZAR.md.

Los cambios se aplican al abrir la siguiente sesión.

## 8. Informar al usuario

Diga al usuario, con sus palabras:

1. Jarvis está instalado y en marcha, y en qué carpeta.
2. Para empezar, escriba «Hey Jarvis» en la caja de texto de la ventana de Jarvis y pulse Enter. Después escriba «ayuda» para ver las órdenes.
3. Para cerrar la sesión, escriba «Buenas noches Jarvis». Para salir del todo, use «Salir» en el icono de la bandeja.
4. Si ha activado el inicio automático, Jarvis arrancará solo con Windows.
5. Para crear perfiles, ponerles contraseña, diseñar plantillas o quitar el sonido, pulse «Configuración» en la pantalla dormida.
6. La guía de uso es [MANUAL.md](MANUAL.md) y la de configuración, [PERSONALIZAR.md](PERSONALIZAR.md).

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| «la ejecución de scripts está deshabilitada en este sistema» | Política de ejecución de PowerShell. | Lance el guion con `powershell -NoProfile -ExecutionPolicy Bypass -File …`. |
| `python` abre Microsoft Store. | Acceso directo de la tienda, sin Python real. | Use `py -3` o instale Python con `winget` (paso 1). |
| `pip install` falla al compilar un paquete. | Versión de Python sin paquetes precompilados para alguna dependencia. | Cree el entorno con Python 3.11: borre `.venv` y repita el paso 3 con `py -3.11`. |
| `fetch_models.py` termina con `Error:` | Sin conexión o descarga interrumpida. | Compruebe la red y vuelva a ejecutarlo. |
| El registro dice `Faltan modelos`. | No se completó el paso 4. | Ejecute el paso 4 y arranque de nuevo. |
| Lanzar Jarvis no hace nada. | Ya hay una instancia en marcha: solo puede haber una. | Busque el icono en la bandeja o termine el proceso con `stop_jarvis.ps1`. |
| Jarvis no habla. | Sonido desactivado en la configuración, sin altavoz o volumen a cero. | Active el apartado Sonido de la configuración y compruebe el sonido de Windows. Los subtítulos funcionan sin voz. |
| `ModuleNotFoundError: No module named 'tomlkit'` o `'cryptography'` | Entorno de la versión 1.0 sin las dependencias nuevas. | Repita `.\.venv\Scripts\pip.exe install -e .` (paso 3). |

Para desinstalar, siga [implementation/README.md](implementation/README.md#desinstalar).

## Actualizar desde una versión anterior

1. Cierre Jarvis: «Salir» en el icono de la bandeja, o `stop_jarvis.ps1`.
2. **Haga una copia de seguridad** de la carpeta de datos, `%LOCALAPPDATA%\Jarvis\data\`. Al primer arranque, la base de datos se actualiza sola y renumera las sesiones; no se puede deshacer.
3. Actualice el código, por ejemplo con `git pull` en la carpeta del repositorio.
4. Desde `implementation\`, reinstale las dependencias: `.\.venv\Scripts\pip.exe install -e .`. La versión 2.0 añade `tomlkit` y `cryptography`.
5. Siga desde el [paso 5](#5-arrancar-y-comprobar). Su configuración de `%APPDATA%\Jarvis\config\` se conserva; los archivos nuevos (`profiles.toml`, `layouts.toml`) se crean solos.

Los cambios de cada versión están en [CHANGELOG.md](CHANGELOG.md).
