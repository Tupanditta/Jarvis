# Perfil Acedor: permisos por módulo y custodia de contraseñas

Fecha: 2026-11-17. Parte de los perfiles protegidos (mismo día).

## Intención

Un perfil es un entorno de trabajo (Trabajo, Casa, Estudio…). El **Acedor** es el nivel máximo
de autoridad en Jarvis: decide qué puede usar cada perfil, puede ver las contraseñas de los
perfiles protegidos y es el único que elimina perfiles. No trabaja con los módulos normales:
su sesión solo tiene módulos de administración.

## Objetivos

- Perfil Acedor fijo y único, que se activa una vez poniéndole contraseña.
- Permisos por módulo y por perfil. Un perfil nuevo empieza con todos los módulos.
- El Acedor ve las contraseñas de los perfiles, aunque las pongan otros sin estar él.
- El Acedor recibe los avisos de intrusión de todos los perfiles.
- Solo el Acedor elimina perfiles, desde su sesión.

## Fuera de alcance

- Permisos por acción (solo por módulo).
- Permisos sobre la configuración: sigue abierta a todos, salvo eliminar perfiles.
- Varios acedores.

## Anti-objetivos

- Que una contraseña se diga en voz alta, aparezca en el registro o pase por el enrutador.
- Que editar `profiles.toml` a mano dé o quite permisos o desactive al Acedor.
- Que un perfil restringido pueda usar el módulo por otra vía (ventana, protocolo).

## Decisiones del propietario

| Tema | Decisión |
|------|----------|
| Contraseñas | El Acedor puede **verlas** (cifrado recuperable solo por él) |
| Su sesión | Como las demás, pero solo con sus módulos: Permisos, Credenciales, Perfiles |
| Configuración | Abierta a todos; cualquiera añade perfiles; nadie elimina desde ella |
| Eliminar perfiles | Solo el Acedor, en su sesión |
| Granularidad | Por módulo |
| Creación | Fijo; se activa poniéndole contraseña en Configuración |
| Permisos por defecto | Todos los módulos |
| Ver contraseñas | En una ventana, ocultas hasta pulsar «mostrar»; nunca en voz |
| Módulo restringido | Oculto en la ayuda y en las ventanas; su orden se rechaza con una frase |
| Intrusiones | El Acedor recibe las de todos; confirmar él no confirma por el dueño |
| Olvido de su clave | Reinicio manual (`--reiniciar-acedor`); se pierden las contraseñas visibles |
| Cifrado | X25519 + AES-GCM con `cryptography` |
| Reparto | Tres módulos: Permisos, Credenciales, Perfiles |

## Enfoques considerados

- **Cifrado.** X25519 (elegido): par de claves del Acedor y cada contraseña sellada con la
  pública, así se cifra sin él. RSA-OAEP: lo mismo, más pesado. PyNaCl SealedBox: más simple,
  dependencia menos habitual. Uno simétrico con la clave del Acedor no sirve: quien pone su
  contraseña no tiene la clave del Acedor.
- **Módulos.** Tres módulos (elegido), uno por función y ventana, frente a uno con pestañas.
- **Dónde se aplica un permiso.** En dos sitios: el enrutador prefiere los módulos permitidos y
  oculta los demás en la ayuda; `run_task`, el único sitio que ejecuta acciones (AD-13),
  rechaza los no permitidos. Así ni una ventana ni un protocolo los esquivan.

## Diseño

### Datos (migración `0003_acedor.sql`)

- `profile_permissions(profile_id, module, allowed, updated_at)`, clave `(profile_id, module)`.
  Sin fila: permitido (permisos por defecto). Restringir es `allowed = 0`.
- `admin_keys` (una fila): clave pública X25519, clave privada cifrada (scrypt de la clave del
  Acedor + AES-GCM), sal y `is_deleted`.
- `credential_escrow(profile_id, sealed, updated_at, is_deleted)`: la contraseña de cada perfil
  sellada con la clave pública del Acedor (X25519 efímera + HKDF-SHA256 + AES-GCM).
- `intrusion_alerts.admin_acknowledged_at`: la confirmación del Acedor, aparte de la del dueño.
- La contraseña del Acedor va en `profile_credentials` como cualquier otra (id `acedor`):
  la regla de los tres intentos y los avisos le valen igual.

### Acedor

- Id reservado `acedor`, nombre «Acedor». No está en `profiles.toml`: el selector lo añade al
  final cuando está activo (`ProtectedProfilesChanged.admin_active`). Ningún perfil de
  `profiles.toml` puede usar ese id ni ese nombre.
- Activarlo (Configuración, tarjeta Acedor): contraseña nueva dos veces → par de claves.
  Cambiarla pide la actual (para volver a cifrar la clave privada).
- Al entrar con su contraseña se descifra la clave privada y se guarda en memoria hasta cerrar
  la sesión (`AdminSession`, en `ActionContext.admin`).

### Custodia de contraseñas

- Poner o cambiar la contraseña de un perfil en Configuración la sella con la clave pública, si
  el Acedor está activo.
- Las contraseñas anteriores al Acedor solo son hash: se sellan la próxima vez que su dueño
  entra con ella (al iniciar sesión o al desbloquear en Configuración).
- Quitar la contraseña o retirar el perfil marca su sello como borrado.
- Reiniciar el Acedor marca como borrados sus claves, su contraseña y todos los sellos.

### Permisos

- Módulos restringibles: los de acción normales. Siempre permitidos: el núcleo y Sesión. Los de
  administración (`admin = True`) solo existen para el Acedor y no se pueden conceder.
- Al abrir sesión el orquestador calcula los módulos permitidos del perfil, configura el
  enrutador (`set_scope`) y publica `PermissionsApplied(hidden_panels)`: la interfaz oculta las
  ventanas de los módulos no permitidos y la ayuda no los lista.
- `run_task` rechaza un módulo no permitido sin ejecutarlo: tarea en `error` con la frase
  «No tiene autorización para usar {modulo} en este entorno, señor.».

### Módulos del Acedor

- **Permisos** (`permisos`): «da permiso de {modulo} a {perfil}», «quita permiso de {modulo} a
  {perfil}», «muestra los permisos». Ventana con la tabla perfil × módulo e interruptores.
- **Credenciales** (`credenciales`): «muestra las contraseñas». Ventana con cada perfil
  protegido y su contraseña oculta hasta pulsar «mostrar». La voz nunca la dice. Una contraseña
  todavía sin sello aparece como «no disponible hasta que su dueño entre».
- **Perfiles** (`perfiles`): «elimina el perfil {perfil}», con confirmación. Ventana con la lista
  y un botón de eliminar. No elimina al Acedor ni el último perfil. Quita el perfil de
  `profiles.toml` y retira sus datos; el selector se actualiza al cerrar la sesión.

### Intrusiones

- Al entrar el Acedor se entregan los avisos sin confirmar por él de todos los perfiles; la
  tarjeta indica el perfil de cada uno. Confirmarlos fija `admin_acknowledged_at`; los suyos
  propios, también la confirmación de dueño.

### Configuración

- Ya no se eliminan perfiles desde ella.
- Tarjeta Acedor: activar / cambiar contraseña. No se duplica ni se edita su nombre.

### Reinicio

- `jarvis --reiniciar-acedor`: desactiva al Acedor (borrado lógico de claves, contraseña y
  sellos) y termina. Los permisos se conservan; las contraseñas de los perfiles siguen valiendo.

## Para quien lo construya

- Frases nuevas en `speaker/phrases.py`; iconos SVG nuevos en `ui/assets/icons/`.
- Ventanas nuevas en `ui/workspace.py` (`WINDOWS`) y `ui/qml/panels/`.
- Ampliar el mapa de dependencias de `tests/unit/test_architecture.py` con lo justo.
