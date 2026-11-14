# Módulo de acción: Apertura de Aplicaciones y Páginas

- **Código:** `action_modules/app_launcher.py`. Nombre de módulo: `apertura`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Lanzar aplicaciones instaladas, abrir URLs de un catálogo predefinido en Microsoft Edge y abrir carpetas en el gestor de archivos nativo, sin interferir con el foco de las ventanas.

## Acciones

| Acción | Parámetros | Efecto |
|---|---|---|
| `abrir` | `objetivo: CATALOG` (aplicaciones y páginas) | Lanza la aplicación o abre la página (RF-22, RF-23). |
| `abrir_carpeta` | `ruta: DIR_PATH` (opcional; sin ella, el directorio de trabajo) | Abre la carpeta en el gestor de archivos (RF-58). |
| `traer_al_frente` | `objetivo: CATALOG` (elementos abiertos) | Trae al frente la ventana de un elemento abierto (RF-25). |

Todas se pueden invocar por voz y desde protocolos. Todas activan el panel de aperturas.

## Reglas

### Qué se puede abrir (RN-17, RN-49)

El nombre dicho se busca, en este orden, y gana la primera fuente con una coincidencia ≥ 75 ⚙:

1. **Catálogo de aplicaciones** (`catalog.toml`, sección `apps`): por `name` y `aliases`.
2. **Catálogo de páginas** (sección `pages`): por `name` y `aliases`. Solo se abren URLs del catálogo.
3. **Aplicaciones descubiertas** del sistema (accesos directos del menú Inicio), si `discover_installed_apps = true`. Se descubren al arrancar y al abrir cada sesión, en segundo plano.

Sin coincidencia: tarea en `error`, «No encuentro {nombre}.». El catálogo lo edita el usuario a mano; no se amplía por voz.

### Lanzamiento

- **Aplicación:** `ctx.platform.launch_app`. No se espera a que la aplicación termine.
- **Página:** `ctx.platform.open_url_in_edge(url)`. Siempre Microsoft Edge. Si Edge no está instalado: `error`, «Microsoft Edge no está instalado.».
- **Carpeta:** `ctx.platform.open_folder(path)`. Ruta relativa respecto al directorio de trabajo (RN-42). Ruta inválida o fallo del gestor: RN-41.
- La tarea queda `completado` en cuanto el lanzamiento tiene éxito, y `error` si falla. Voz: «Abriendo {nombre}.».

### Foco (RES-32)

El asistente no trae nada al frente por su cuenta ni recupera el foco tras abrir. La aplicación abierta toma el foco como decida el sistema; la pantalla de sesión queda detrás y el HUD flotante pasa a mostrarse.

### Elementos abiertos y «traer al frente» (RF-24, RF-25)

- El módulo mantiene en memoria la lista de elementos abiertos en la sesión (máximo 12; se descarta el más antiguo). Cada uno: nombre, tipo (aplicación, página, carpeta), estado y referencia a su ventana.
- Tras lanzar, busca en segundo plano la ventana nueva (`ctx.platform.wait_for_window`, hasta 10 s). Si la encuentra, el elemento pasa a `can_focus = True`. Para una página, la ventana es la de Edge.
- Cada cambio publica `OpenedItemsChanged` con la lista completa.
- **Traer al frente:** por clic (`FocusItemRequested`) o por voz. Llama a `ctx.platform.focus_window`. Si la ventana ya no existe, el elemento pasa a `can_focus = False` y se dice «Esa ventana ya no está abierta.».
- La lista se vacía al cerrar la sesión. Las aplicaciones abiertas no se cierran.
- Si el sistema no permite traer ventanas al frente (Wayland), el botón no se muestra.

## Datos

Catálogo de la configuración. Lista de elementos abiertos en memoria. Ningún dato propio en la base de datos.

## Eventos

`OpenedItemsChanged`. Consume `FocusItemRequested`.

## Criterios de aceptación

Con `FakePlatform`:

- Orden de resolución: catálogo de aplicaciones, páginas, descubiertas.
- Nombre sin coincidencia.
- Página: solo URLs del catálogo y solo con Edge; Edge ausente.
- Carpeta: relativa, absoluta, inexistente, no carpeta, fallo del gestor.
- La ventana localizada activa `can_focus`; una ventana cerrada lo desactiva.
- Ninguna acción de apertura llama a `bring_own_window_to_front`.

## Prohibiciones

- El asistente no roba el foco a las aplicaciones o páginas que abre.
- Las páginas no se abren con un navegador distinto de Microsoft Edge ni fuera del catálogo.
