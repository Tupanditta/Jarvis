# Función del núcleo: Perfiles protegidos y aviso de intrusión

- **Código:** `core/security.py` (contraseñas, intentos y avisos), `core/custody.py` (custodia para el Acedor), `core/orchestrator.py` (caja de la contraseña al abrir sesión), `configurator/sections/profiles.py` (contraseñas en la configuración). No es un módulo de acción: no tiene intenciones ni está en `ACTION_MODULES`.
- **Volver a:** [contexto](../../contexto.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md) · módulos del Acedor: [Permisos](permisos.md), [Credenciales](credenciales.md), [Perfiles](perfiles.md).

## Propósito

Impedir que otra persona abra sesión o edite la configuración en un perfil que no es suyo, avisar a su dueño de los intentos fallidos, y dar a un perfil único, el Acedor, autoridad sobre todos los demás.

## Conceptos

- **Perfil** (`profiles.toml`, RN-56): entorno de trabajo (Trabajo, Casa, Estudio…). Da el nombre del usuario que dice «preséntate» y la plantilla de la pantalla de sesión ([hud.md](../Infraestructura/hud.md), sección 2.1). Se elige en la pantalla dormida. Los recordatorios son de un perfil: cada sesión solo ve y crea los del suyo.
- **Perfil protegido** (RN-57): perfil con contraseña. La pide antes de abrir sesión y antes de editarlo en la configuración.
- **Acedor** (RN-60): perfil fijo y único, con id `acedor` y nombre «Acedor», reservados. No está en `profiles.toml`: existe en cuanto se activa con su contraseña. Solo aparece en el selector de perfiles si está activado, el último.

## Contraseñas

- Mínimo 4 caracteres. Se ponen, cambian o quitan en la ventana de configuración ([configurador.md](../Infraestructura/configurador.md)), apartado Perfiles, y se aplican al guardar.
- Un perfil protegido está bloqueado en la configuración: no se edita ni se duplica hasta desbloquearlo con su contraseña, y sigue desbloqueado hasta cerrar la ventana.
- Nunca se guardan en claro (RNF-32): en la tabla `profile_credentials` solo está su hash scrypt con sal (`scrypt$n$r$p$sal$clave`). Hasta guardar, la ventana solo guarda el hash y el sello en memoria. La comparación es en tiempo constante; un hash con formato desconocido no deja pasar a nadie.
- No hay recuperación. Un perfil con la contraseña olvidada solo lo elimina el Acedor ([Perfiles](perfiles.md)) o su dueño quitándolo a mano de `profiles.toml`.

## Acceso al abrir sesión (RF-104)

1. «Hey Jarvis» en dormido con un perfil protegido elegido no llega a la máquina de estados. Se publica `AccessChallenged` y aparece la caja de la contraseña en el centro de la pantalla dormida. La primera vez, el asistente dice «Esta área está protegida por un nivel de seguridad superior. Introduzca la clave correcta para obtener acceso.», sin despertar.
2. La caja no muestra lo que se escribe, ni puntos. Enter envía la clave (`AccessAttempted`, que no pasa por el enrutador y no muestra la clave en su `repr`); Esc la cierra (`AccessCancelled`).
3. **Acierto:** la caja se cierra (`AccessClosed(granted=True)`) y la sesión se abre (`AccessGranted` en la máquina de estados). La frase de apertura es `ciclo.apertura_protegida` en lugar de `ciclo.apertura`.
4. **Fallo:** `AccessDenied`; la caja se sacude, se pone roja y sigue abierta. El asistente dice «Clave incorrecta. Acceso denegado.».
5. **Tercer fallo seguido** (RN-58): misma respuesta que los demás, y la caja se cierra. Se registra un aviso de intrusión.

## Intentos y avisos de intrusión (RN-58, RN-59)

- La cuenta de fallos es por perfil y no distingue dónde se pidió la contraseña (`AccessOrigin`: `inicio` o `configuracion`). Cancelar entre medias no la reinicia; un acierto sí.
- Al tercer fallo seguido se inserta un aviso en `intrusion_alerts` (perfil, momento, intentos, origen) y la cuenta vuelve a cero.
- Quien falla no sabe nada del aviso ni de cuántos intentos le quedan.
- **Entrega al dueño (RF-107):** al abrir sesión en el perfil, sus avisos sin confirmar van los primeros de la cola de avisos, tras la frase de apertura. Se dice `seguridad.intrusion` (uno) o `seguridad.intrusiones` (varios) y aparece la tarjeta crítica (`IntrusionAlertsShown`), por encima de todo, hasta pulsar «Entendido» (`IntrusionAcknowledged`). Si la sesión se cierra sin confirmarla, vuelve a salir en la siguiente.
- **Entrega al Acedor:** recibe los avisos de todos los perfiles, con el nombre de cada uno, y los confirma aparte del dueño (`admin_acknowledged_at`). Confirmar los de su propio perfil los confirma también como dueño. Frase: `seguridad.intrusion_acedor`.

## El Acedor

### Activación y contraseña (RF-108, RF-109)

- Se activa en la configuración, en su propia tarjeta, poniéndole contraseña. Después solo se cambia dando la actual; un fallo cuenta como intento de acceso al Acedor.
- **Custodia** (`core/custody.py`): al activarse se genera un par de claves X25519. La pública está en claro; la privada se guarda cifrada con una clave derivada de su contraseña (scrypt + AES-GCM). Cualquier contraseña de perfil que se pone después se sella con la pública (X25519 efímera, HKDF-SHA256 y AES-GCM). Solo la privada abre el sello. Cambiar la contraseña del Acedor vuelve a cifrar la privada: lo custodiado sigue pudiéndose ver.
- Una contraseña puesta antes de activar al Acedor solo era un hash: se sella la próxima vez que su dueño entra con ella.
- **Olvido:** `python -m jarvis_assistant --reiniciar-acedor`, con el asistente cerrado. El Acedor deja de estar activo; sus claves y todos los sellos se marcan como borrados y las contraseñas dejan de poder verse. Los permisos y las contraseñas de los perfiles siguen valiendo.

### Sesión del Acedor (RN-61)

- Al acertar su contraseña se descifra su clave privada, que vive en memoria (`ActionContext.admin`) hasta cerrar su sesión. Si las claves están dañadas, se rechaza el acceso como una clave incorrecta.
- Solo usa los módulos de administración ([Permisos](permisos.md), [Credenciales](credenciales.md), [Perfiles](perfiles.md)), el módulo Sesión y el núcleo. Ningún otro perfil tiene esos tres módulos ni se le pueden conceder.

## Datos

| Tabla | Contenido |
|---|---|
| `profile_credentials` | Hash de la contraseña de cada perfil protegido, fallos seguidos, borrado lógico. |
| `intrusion_alerts` | Avisos: perfil, momento (UTC), intentos, origen, confirmación del dueño y del Acedor. |
| `admin_keys`, `credential_escrow` | Claves del Acedor (la privada, cifrada) y contraseñas selladas con su clave pública, con borrado lógico. |
| `reminders.profile_id` | Perfil al que pertenece cada recordatorio. |

El orquestador (hilo del núcleo) y la ventana de configuración (hilo de la interfaz) usan `ProfileVault`, cada uno con su propia conexión a la base de datos.

## Eventos

`ProtectedProfilesChanged` (perfiles con candado y si el Acedor está activado; al arrancar y al recargar la configuración), `AccessChallenged`, `AccessAttempted`, `AccessDenied`, `AccessCancelled`, `AccessClosed`, `IntrusionAlertsShown`, `IntrusionAcknowledged`.

## Criterios de aceptación

- Perfil sin contraseña: «Hey Jarvis» abre sesión sin caja.
- Perfil protegido: acierto a la primera; fallo y acierto; tres fallos seguidos (aviso registrado y caja cerrada); dos fallos, Esc y otro fallo (aviso registrado).
- Los fallos de la configuración y los de inicio suman en la misma cuenta.
- La respuesta al tercer fallo es idéntica a la de los anteriores.
- El dueño recibe el aviso al entrar; sin confirmar, vuelve a recibirlo en la sesión siguiente; confirmado, no.
- El Acedor recibe los avisos de todos y su confirmación no confirma los del dueño, salvo los de su propio perfil.
- Activar al Acedor, poner una contraseña de perfil y verla en su sesión; cambiar la contraseña del Acedor y seguir viéndola; contraseña anterior al Acedor, sellada tras la siguiente entrada de su dueño.
- `--reiniciar-acedor`: el Acedor desaparece del selector, las contraseñas de los perfiles siguen valiendo y los permisos se conservan.
- RNF-32: ninguna contraseña en la base de datos, en `profiles.toml` ni en el registro.

## Prohibiciones

- No se guarda ni se registra ninguna contraseña en claro, ni la clave privada del Acedor.
- No se dice cuántos intentos quedan ni que se ha registrado un aviso.
- Ningún perfil de `profiles.toml` usa el id ni el nombre del Acedor.
- La clave del Acedor no sobrevive a su sesión.
