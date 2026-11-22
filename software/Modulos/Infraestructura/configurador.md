# Ventana de configuración

- **Código:** `configurator/`.
- **Origen:** Refuerzo (módulo nuevo).
- **Diseño:** [docs/superpowers/specs/2026-11-17-ventana-configuracion-design.md](../../../docs/superpowers/specs/2026-11-17-ventana-configuracion-design.md).
- **Volver a:** [contexto](../../contexto.md) · [configuracion.md](configuracion.md).

## Propósito

Que cualquier usuario cambie el funcionamiento del asistente con el ratón, sin editar archivos ni tocar el código. La ventana no habla con el asistente: no se le dan órdenes ni responde. Solo edita la configuración, y el asistente la aplica al abrir la siguiente sesión.

## Acceso y ciclo de vida

- **Solo desde la pantalla dormida:** botón «Configuración», junto al selector de perfiles, encima de la caja de texto ([hud.md](hud.md), sección 2.1). No hay otra forma de configurar el asistente desde la interfaz (la bandeja solo abre la carpeta de los archivos).
- La ventana pertenece a la pantalla de sesión (`setTransientParent`): queda siempre encima de ella, aunque esté a pantalla completa.
- **Mientras está abierta no se puede iniciar sesión:** la caja de texto se desactiva y la bandeja oculta «Abrir sesión». Al cerrarla vuelven.
- **Se crea al abrirla y se destruye al cerrarla** (`ConfigWindow.closed`; `main.py` la libera con su motor QML y sus dos ventanas). Durante la sesión no queda nada de ella en memoria ni hace ningún trabajo: rendimiento igual que sin ella.
- Lo que se guarda se aplica al abrir la siguiente sesión.

## Ventana

Ventana normal de 960 × 640 px. A la izquierda, los apartados; a la derecha, el apartado elegido; abajo, **Cancelar** y **Guardar**.

- El título acaba en ● y Guardar se activa cuando hay cambios sin guardar. Cada apartado con cambios lleva un punto ámbar.
- **Guardar** valida todos los apartados. Con problemas, no escribe nada y los lista abajo. Sin problemas, escribe solo los archivos de los apartados con cambios y muestra «Guardado. Se aplicará al abrir la próxima sesión.».
- **Cancelar**, Esc o ✕: sin cambios, cierra. Con cambios, pregunta dentro de la ventana: «Seguir editando» o «Salir sin guardar», que descarta el borrador sin tocar ningún archivo.
- Un apartado cuyo archivo tenía errores al abrir la ventana queda **bloqueado**: explica el error y no deja editar. Guardar sobre él borraría lo que el asistente no ha podido leer.

## Apartados

| Apartado | Archivo | Qué edita |
|---|---|---|
| Plantillas | `layouts.toml` | Crear (botón «+»), editar, duplicar y eliminar plantillas. La de fábrica siempre está, primera; solo se duplica. Eliminar una plantilla en uso pide confirmación y sus perfiles pasan a la de fábrica. |
| Perfiles | `profiles.toml` | Nombre del perfil, nombre del usuario (el de «preséntate») y plantilla, elegida con chips. Añadir, duplicar y eliminar; siempre queda uno. Sin `profiles.toml`, empieza con el perfil «Predeterminado» de `user.name`. |
| Sonido | `settings.toml` (`sound.enabled`) | Activar o desactivar el sonido del asistente. |
| Aplicaciones | `catalog.toml` | Las aplicaciones y páginas añadidas a mano (no las descubiertas). «Añadir» pide primero Aplicación o Página web. Aplicación: nombre, programa (con «Examinar…»), argumentos y otros nombres. Página: nombre, dirección (`http://` o `https://`) y otros nombres. Un nombre u otro nombre repetido no se acepta; una ruta que no existe solo avisa. |

Los nombres se comparan sin mayúsculas, sin tildes y sin espacios sobrantes. Los ids de perfiles y plantillas se generan a partir del nombre y no cambian al renombrar.

## Editor de plantillas

Crear o editar una plantilla abre una pantalla inerte a pantalla completa:

- El fondo de la pantalla de sesión, un círculo que marca el sitio del orbe, las ventanas que la plantilla muestra (con su marco y sin contenido) y las dos barras.
- Las ventanas se mueven, se redimensionan y se cierran como en la sesión. El selector de ventanas se arrastra; la caja de texto se arrastra y cambia de ancho desde sus extremos (mínimo 300 px). Las barras no responden a nada más, y si al soltar una tapa la otra, vuelve a donde estaba.
- Una paleta arrastrable con el nombre, un interruptor por ventana («mostrar al abrir sesión»), **Restablecer** (disposición de fábrica), **Cancelar** (o Esc) y **Aceptar**. Una ventana oculta conserva su sitio.
- **Aceptar** valida el nombre (obligatorio y único) y deja la plantilla en el borrador. Solo queda registrada al pulsar Guardar.

El editor usa el mismo `WorkspaceModel` y los mismos componentes (`FloatingWindow`, `Dock`, `CommandInput`) y la misma área de trabajo que la pantalla de sesión: lo que se ve es lo que se verá.

## Estructura

```text
configurator/
├── window.py      # ConfigWindow: crea el motor QML, muestra la ventana, Guardar/Cancelar
├── draft.py       # Draft: abre, valida y guarda (sin QML)
├── editor.py      # LayoutEditor: el editor de plantillas
├── registry.py    # SECTIONS: los apartados, en orden
├── sections/      # base.py (Section) y un archivo por apartado
└── qml/           # ConfigWindow.qml, LayoutEditor.qml, sections/, controls/
```

- **Apartado** (`sections/base.py`, `Section`): `files` (los archivos que escribe), `load(config)`, `validate()` (problemas en frases para el usuario), `dump(documentos)` y `touch()` en cada cambio.
- **Añadir un apartado** es añadir su clase en `sections/`, su página en `qml/sections/` y su `SectionSpec` en `registry.SECTIONS`. `create` recibe el editor y los apartados ya creados, por si depende de alguno (Perfiles depende de Plantillas).
- **Guardado** (`Draft.save`): valida todos los apartados; vuelca los que tienen cambios en sus documentos `tomlkit`; comprueba cada documento con `config.check`, la misma regla que usa el asistente al cargar; y escribe con `config.writer`, que conserva comentarios y formato y sustituye cada archivo desde un temporal. Después vuelve a cargar todo.
- **Dependencias:** `config`, `core.events` (solo los tipos), `ui.app`, `ui.view_models`, `ui.workspace`. Nadie importa `configurator` salvo `main.py`. `ConfigWindow` recibe `on_saved` (`main.py` publica `ConfigSaved`) y `owner` (la pantalla de sesión). `UiApp` recibe `open_settings` y expone `settingsAvailable`, `configuring` y `openSettings()` a QML.

## Criterios de aceptación

- Unitarias (`tests/unit/configurator/`): nada se escribe hasta guardar; guardar sin cambios no escribe; solo se escriben los archivos cambiados; se conservan los comentarios; con problemas no se escribe nada; un archivo con errores bloquea su apartado; perfiles, plantillas (editor, eliminar en uso, duplicar la de fábrica), sonido y catálogo.
- Integración (`tests/integration/test_configurator_qml.py`): la ventana y todos sus apartados cargan sin avisos de QML; Guardar escribe y avisa; cerrar con cambios pregunta y «Salir sin guardar» los descarta; el editor se abre y acepta.
- Manual: crear una plantilla moviendo ventanas y barras, asignarla a un perfil, guardar, elegir el perfil en la pantalla dormida, abrir sesión y comprobar la disposición y el nombre de «preséntate».

## Prohibiciones

- Escribir un archivo antes de pulsar Guardar.
- Escribir un archivo cuyo apartado está bloqueado.
- Importar `configurator` desde el núcleo o la interfaz del asistente.
