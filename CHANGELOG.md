# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [2.0.0] - 2026-11-22

### Añadido

#### Perfiles y plantillas
- **Perfiles de usuario** (`profiles.toml`): cada perfil tiene su nombre y su plantilla de pantalla. La última sesión recuerda el perfil con el que se abrió.
- **Selector de perfiles** en la pantalla dormida, bajo el orbe. Se cambia con el ratón o con ←/→ cuando la caja de texto está vacía. Solo aparece con dos perfiles o más.
- **Plantillas de pantalla** (`layouts.toml`): definen qué ventanas flotantes se abren al iniciar sesión, su posición y tamaño, y dónde van el selector de ventanas y la caja de texto.
- Botón **«Restablecer disposición»** en el selector de ventanas para volver a la plantilla del perfil.

#### Ventana de configuración
- Nueva **ventana de configuración** que se abre desde la pantalla dormida o desde la bandeja del sistema. Permite cambiar el funcionamiento del asistente con el ratón, sin editar archivos.
- Secciones: **Perfiles**, **Plantillas** (con editor visual de la disposición) y **Sonido**.
- Opción para activar o desactivar el sonido del asistente (`[sound] enabled` en `settings.toml`). Con el sonido desactivado se siguen mostrando los subtítulos.
- Mientras la ventana está abierta no se puede iniciar sesión.

#### Perfiles protegidos y Acedor
- **Contraseña por perfil**: tras «Hey Jarvis», un perfil protegido pide su contraseña en una caja que no muestra lo que se escribe. Los perfiles protegidos llevan un candado en el selector.
- **Avisos de intrusión**: al tercer fallo seguido se registra un aviso. El dueño del perfil lo ve al abrir sesión con una tarjeta crítica y un aviso por voz.
- **Acedor**: perfil administrador opcional, con autoridad sobre todos los demás. Se activa desde la configuración con una contraseña.
- Opción de línea de comandos `--reiniciar-acedor` para desactivar al Acedor si olvida su contraseña (con el asistente cerrado).
- Las contraseñas de los perfiles se guardan como hash scrypt con sal. Para que el Acedor pueda consultarlas, se guarda además una copia sellada con su clave pública (X25519 + AES-GCM, nueva dependencia `cryptography`).

#### Ventanas exclusivas del Acedor
- **Permisos**: tabla con una fila por perfil y una casilla por módulo o medidor. El Acedor decide qué puede usar cada perfil.
- **Credenciales**: muestra las contraseñas de los perfiles protegidos, ocultas hasta pulsar el ojo.
- **Perfiles**: lista los perfiles y permite eliminar uno, con sus datos, tras confirmación.

#### Módulo Catálogo
- Nueva ventana para **ver, añadir y eliminar** aplicaciones, páginas web y comandos de terminal sin editar `catalog.toml` ni `commands.toml` a mano.
- Filtro por tipo y validación de los datos antes de guardar.

#### Medidores en la pantalla de sesión
- **Recursos**: consumo de CPU y RAM del proceso del asistente, actualizado cada segundo.
- **Ruido**: ruido de fondo en decibelios aproximados (mediana de los últimos 30 s) y un rótulo con el nivel de concentración que permite. No graba ni guarda audio.
- Cada medidor se muestra u oculta desde el selector de ventanas y cambia de esquina con un triple clic.
- Los medidores solo miden mientras están a la vista; el micrófono se cierra al ocultar el de ruido.

#### Historial de sesiones
- **Eliminar varias sesiones a la vez**: «Elimina sesiones» muestra el historial y pide cuáles, por lista («1, 3, 5») o por intervalo («1-5»).
- Aviso antes de eliminar si alguna de las sesiones elegidas está marcada como importante.

#### Comandos y protocolos
- Cada tarea trabaja en **su propia consola**: carpeta de trabajo, panel y programa en marcha independientes.
- Un protocolo con tareas de Comandos abre su propia ventana de Comandos, y otra nueva cada vez que cambia de carpeta.

#### Interfaz
- Nuevos componentes del HUD: arcos, marcas y lecturas para los medidores.
- Nueva fuente **Orbitron** (licencia OFL) y nuevos iconos.

### Cambiado
- **Borrado real de sesiones**: eliminar una sesión ahora la borra de la base de datos junto con sus actividades (antes era un borrado lógico).
- **Renumeración de sesiones**: tras eliminar, los identificadores se renumeran de 1 a N sin huecos.
- Las **sesiones vacías** ya no se guardan en el historial.
- Las órdenes de consulta de Comandos («Dónde estoy», «Qué hay aquí», «Limpia la consola») ya no se registran como actividad.
- El nombre del usuario lo da ahora cada perfil. El campo de nombre de `settings.toml` queda obsoleto y solo se usa si no hay perfiles.
- Mejoras en la fluidez de las animaciones. Los paneles se cargan de forma asíncrona para no frenar la animación de despertar.
- **Refactorización de la configuración**: `config.py` se divide en el paquete `config/` (lectura, escritura, perfiles, plantillas, catálogo, comandos y protocolos).
- Documentación de `software/` actualizada: requisitos RF-100 a RF-118, nuevas reglas de negocio, base de datos y módulos nuevos.

### Eliminado
- Archivos generados que no debían estar en el repositorio: `__pycache__/`, `*.pyc`, `.coverage` y `*.egg-info/`. Ahora están en `.gitignore`.

### Actualizar desde la 1.0

1. Reinstale las dependencias en el entorno virtual: la versión 2.0 añade `tomlkit` y `cryptography`.
   ```
   .\implementation\.venv\Scripts\pip.exe install -e .\implementation
   ```
2. La base de datos se actualiza sola al arrancar, con las migraciones `0002_perfiles_protegidos`, `0003_acedor` y `0004_sesiones_renumeradas`. Haga una copia de seguridad de la carpeta de datos antes del primer arranque: la migración 0004 renumera las sesiones.

## [1.0.0] - 2026-11-16

- Primera versión: asistente de voz para Windows con activación por «Hey Jarvis», pantalla de sesión con orbe, apertura de aplicaciones y páginas, comandos de terminal, protocolos, recordatorios, búsqueda y creación de archivos, e historial de sesiones.

[2.0.0]: https://github.com/Tupanditta/Jarvis/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/Tupanditta/Jarvis/releases/tag/v1.0.0
