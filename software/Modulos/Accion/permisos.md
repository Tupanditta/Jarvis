# Módulo de acción: Permisos

- **Código:** `action_modules/administration.py` (`PermissionManager`, compartido con [Credenciales](credenciales.md) y [Perfiles](perfiles.md)); reglas de alcance en `core/permissions.py`. Nombre de módulo: `permisos`.
- **Volver a:** [contexto](../../contexto.md) · [Perfiles protegidos y Acedor](perfiles-protegidos.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Permitir al Acedor decidir qué módulos y medidores puede usar cada perfil.

## Acciones

Módulo de administración (`admin = True`): solo lo usa el Acedor (RN-61). En cualquier otra sesión sus órdenes se rechazan con `permisos.denegado`, como las de cualquier módulo no permitido; si aun así llegara a ejecutarse, responde «Esa función solo está al alcance del Acedor.» y no hace nada.

| Acción | Parámetros | Panel | Efecto |
|---|---|---|---|
| `conceder` | `modulo: CATALOG` (módulos restringibles), `perfil: CATALOG` (perfiles de `profiles.toml`) | Permisos | Permite el módulo al perfil (RF-110). |
| `restringir` | Igual que `conceder` | Permisos | Restringe el módulo al perfil (RF-110). |
| `ver` | — | Permisos | Publica la tabla perfil × módulo (RF-111). No se registra como actividad. |

Ninguna es invocable desde protocolos. En la ventana, pulsar una casilla publica `PermissionChangeRequested`, que el orquestador convierte en `conceder` o `restringir` con el id del perfil y del módulo.

## Reglas

### Qué se puede restringir (RN-62)

- Los módulos de acción normales, salvo los marcados `always_allowed` (el módulo Sesión: nombrar y marcar la sesión no se restringe).
- Los medidores de la pantalla de sesión (`config.METERS`: Recursos y Ruido), que no son módulos pero se restringen igual; su id es el del permiso.
- No se pueden conceder ni restringir el núcleo ni los módulos de administración.

### Permiso por defecto

Sin fila en `profile_permissions`, el módulo está permitido. Restringir es `allowed = 0`; conceder, `allowed = 1`. El perfil y el módulo se buscan por id (ventana) o por nombre (orden escrita); si alguno no existe: `error`, «No encuentro ese perfil o ese módulo.».

### Alcance de una sesión (RF-112, `core/permissions.session_scope`)

Al abrir sesión el orquestador calcula los módulos que el perfil puede usar:

| Perfil | Módulos permitidos |
|---|---|
| Acedor | Núcleo, módulos `always_allowed` y módulos de administración. Ninguno más. |
| Cualquier otro | Núcleo, módulos `always_allowed` y los demás módulos normales que no tenga restringidos. Nunca los de administración. |

Con ese alcance:

- La ayuda no muestra las intenciones de los módulos no permitidos. El enrutador las reconoce igual, sin buscar otra parecida de un módulo permitido («busca el archivo notas» no acaba creándolo).
- `run_task` rechaza sus acciones sin ejecutarlas, vengan de una orden, de una ventana o de un protocolo: la tarea queda en `error` con «No tiene autorización para usar {módulo} en este entorno.».
- Se publica `PermissionsApplied` con los paneles que se ocultan: los de módulos no permitidos que ningún módulo permitido comparte, y los medidores restringidos. Esas ventanas no se muestran ni se pueden abrir; un medidor restringido no se ve ni se ofrece en el selector.

Un cambio hecho por el Acedor se aplica en la siguiente sesión de ese perfil.

## Datos

Tabla `profile_permissions` (`profile_id`, `module`, `allowed`, `updated_at`), mediante `PermissionRepository`.

## Eventos

`PermissionsShown` (perfiles, módulos restringibles y pares perfil–módulo restringidos), `PermissionChangeRequested`, `PermissionsApplied`.

## Criterios de aceptación

- Fuera de la sesión del Acedor, las tres acciones quedan en `error` con `permisos.denegado`; ejecutadas directamente con `ctx.admin` vacío, con `permisos.solo_acedor`.
- `conceder` y `restringir` por orden escrita y desde la ventana; perfil o módulo inexistente.
- Un perfil con un módulo restringido: la orden queda en `error` con `permisos.denegado`, no aparece en la ayuda, su ventana está oculta y una tarea de protocolo de ese módulo queda en `error` con `permisos.denegado`.
- Un medidor restringido no se ve aunque la plantilla lo muestre.
- El módulo Sesión, el núcleo y los módulos de administración no aparecen como restringibles.
- El Acedor no puede usar los módulos normales.

## Prohibiciones

- Ningún perfil distinto del Acedor usa este módulo.
- No se concede un módulo de administración a ningún perfil.
- No se restringen el núcleo ni el módulo Sesión.
