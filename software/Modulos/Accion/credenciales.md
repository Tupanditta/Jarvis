# Módulo de acción: Credenciales

- **Código:** `action_modules/administration.py` (`CredentialVault`); custodia en `core/custody.py`. Nombre de módulo: `credenciales`.
- **Volver a:** [contexto](../../contexto.md) · [Perfiles protegidos y Acedor](perfiles-protegidos.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Mostrar al Acedor las contraseñas de los perfiles protegidos, para que pueda devolver el acceso a quien la olvide.

## Acciones

Módulo de administración (`admin = True`): solo lo usa el Acedor (RN-61); en otra sesión sus órdenes se rechazan con `permisos.denegado` ([permisos.md](permisos.md)).

| Acción | Parámetros | Panel | Efecto |
|---|---|---|---|
| `ver` | — | Credenciales | Publica `CredentialsShown` con cada perfil protegido y su contraseña (RF-113). No se registra como actividad. |

No es invocable desde protocolos.

## Reglas (RN-63)

1. Se abren los sellos de `credential_escrow` con la clave privada del Acedor, que vive en memoria durante su sesión ([perfiles-protegidos.md](perfiles-protegidos.md)).
2. Solo aparecen los perfiles de `profiles.toml` que tienen contraseña.
3. Una contraseña sin sello (puesta antes de activar al Acedor) aparece sin valor: no se puede ver hasta que su dueño vuelva a entrar con ella.
4. Respuesta: «Aquí tiene las credenciales. Están ocultas hasta que decida mostrarlas.»; sin perfiles protegidos, «Ningún perfil tiene contraseña.».
5. En la ventana cada contraseña está oculta hasta pulsar su ojo, y vuelve a ocultarse al pulsarlo otra vez.
6. Al cerrar la sesión, y al abrir una sesión que no es del Acedor, se publica `CredentialsShown` vacío: la ventana las olvida.

## Datos

Tablas `profile_credentials` (qué perfiles están protegidos) y `credential_escrow` (sellos), a través de `ProfileVault`.

## Eventos

`CredentialsShown`. Su `repr` no incluye las contraseñas.

## Criterios de aceptación

- Fuera de la sesión del Acedor la orden queda en `error` con `permisos.denegado`; ejecutada directamente con `ctx.admin` vacío, responde `permisos.solo_acedor` y no publica nada.
- Con perfiles protegidos con y sin sello, y sin ninguno.
- Al cerrar la sesión la ventana queda vacía.
- Ninguna contraseña aparece en el registro de diagnóstico ni en el texto de los subtítulos.

## Prohibiciones

- Las contraseñas nunca se dicen en voz alta.
- Las contraseñas nunca se escriben en el registro ni en la base de datos en claro.
- La ventana no conserva las contraseñas después de la sesión del Acedor.
