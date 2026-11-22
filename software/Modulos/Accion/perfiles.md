# Módulo de acción: Perfiles

- **Código:** `action_modules/administration.py` (`ProfileManager`); la eliminación la completa el orquestador (`_remove_profile`) y `ProfileVault.retire`. Nombre de módulo: `perfiles`.
- **Volver a:** [contexto](../../contexto.md) · [Perfiles protegidos y Acedor](perfiles-protegidos.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Permitir al Acedor eliminar un perfil y sus datos, también uno cuya contraseña nadie recuerda.

## Acciones

Módulo de administración (`admin = True`): solo lo usa el Acedor (RN-61); en otra sesión sus órdenes se rechazan con `permisos.denegado` ([permisos.md](permisos.md)).

| Acción | Parámetros | Panel | Efecto |
|---|---|---|---|
| `eliminar` | `perfil: CATALOG` (perfiles de `profiles.toml`) | Perfiles | Elimina el perfil tras confirmación (RF-114, RN-64). |
| `ver` | — | Perfiles | Publica `ProfilesListed` con los perfiles que se pueden eliminar. No se registra como actividad. |

Ninguna es invocable desde protocolos. En la ventana, el botón «Eliminar» de cada fila publica `ProfileRemovalRequested`, que el orquestador convierte en `eliminar` con el id del perfil.

## Reglas (RN-64)

1. El perfil se busca por id (ventana) o por nombre (orden escrita). Si no existe: `error`, «No encuentro ese perfil o ese módulo.».
2. Si es el último perfil: `error`, «No puedo eliminar el último perfil.». El Acedor no está en la lista: no se puede eliminar.
3. Se pregunta (`BOOLEAN`) «¿Elimino el perfil {perfil}? Se perderán sus recordatorios.», con el perfil como `subject`.
4. Solo con un sí:
   - se quita de `profiles.toml`, conservando sus comentarios;
   - sus recordatorios pasan a `eliminado` (RN-13);
   - su contraseña y su sello se marcan como borrados, y sus avisos de intrusión pendientes como confirmados;
   - la configuración en memoria deja de tenerlo y el selector de perfiles se actualiza al cerrar la sesión.

   Un perfil nuevo con el mismo id empieza sin recordatorios, contraseña ni avisos; los permisos guardados para ese id se conservan.
5. Con un no, una cancelación o el vencimiento del tiempo, no se elimina y la tarea queda en `error` con el motivo «cancelada».
6. Si no se puede escribir el archivo: `error`, «No he podido eliminar el perfil.».

Desde la ventana de configuración se añaden perfiles, pero ninguno se elimina: solo este módulo los elimina.

## Datos

`profiles.toml`, a través del orquestador. Tablas `reminders`, `profile_credentials`, `credential_escrow` e `intrusion_alerts`, a través de `ProfileVault.retire`.

## Eventos

`ProfilesListed`, `ProfileRemovalRequested`.

## Criterios de aceptación

- Fuera de la sesión del Acedor la orden queda en `error` con `permisos.denegado`; ejecutada directamente con `ctx.admin` vacío, responde `permisos.solo_acedor`.
- `eliminar`: perfil inexistente, último perfil, confirmación afirmativa, negativa y vencida; por orden escrita y desde la ventana.
- Tras eliminar: el perfil no está en `profiles.toml`, sus recordatorios están en `eliminado`, ya no pide contraseña y sus filas siguen en la base de datos (RNF-12).
- Fallo al escribir `profiles.toml`: no se retira ningún dato.

## Prohibiciones

- No se elimina ningún perfil sin confirmación explícita.
- No se elimina el Acedor ni el último perfil.
- No se usa `DELETE` físico en la base de datos.
