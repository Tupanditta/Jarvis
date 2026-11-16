# Entrada por texto

- **Código:** `ui/` (la caja de texto), `core/events.py` (`TextSubmitted`, `UserTyping`), `core/orchestrator.py` (recepción y cuenta de inactividad).
- **Origen:** Refuerzo (módulo nuevo). Sustituye a la captura de audio y al transcriptor, retirados.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md).

## Propósito

Recibir las órdenes del usuario. El usuario no habla al asistente: escribe en una caja de texto y envía con Enter. El asistente responde hablando y en la interfaz. Todo lo que antes hacía la voz del usuario se hace escribiendo, con los mismos estados y las mismas frases (RF-60, RF-61).

## Comportamiento

### La caja de texto

- Hay una sola línea de texto. Está en la ventana del asistente, visible desde el arranque, también en modo dormido.
- **Enter** envía el texto y vacía la caja. Un envío vacío o solo con espacios no hace nada.
- La caja tiene el foco cuando la ventana se muestra o pasa al frente, y lo conserva tras cada envío.
- La interfaz no interpreta el texto. Lo publica tal cual en `TextSubmitted(text)`; reconocerlo es tarea del [enrutador](enrutador-intenciones.md).
- El texto de ayuda de la caja depende del estado:

| Estado | Texto de ayuda |
|---|---|
| `DORMIDO` | Escriba el código de activación para iniciar la sesión |
| `IDLE` | En reposo. Escriba «Hey Jarvis» |
| `LISTENING_COMMAND` y `AWAITING_*` | Escriba una orden |

- En `DORMIDO` lo escrito es el código de activación y la caja lo oculta como una contraseña: cada carácter se muestra como `*`. Solo cambia lo que se ve; el texto se publica igual y el enrutador lo reconoce con la misma tolerancia a erratas. En el resto de estados el texto se ve tal cual.

- No hay botones de órdenes. Los únicos controles de ratón de la interfaz son los de [hud.md](hud.md), sección 3.

### Qué se atiende en cada estado

| Estado | Texto que tiene efecto | El resto |
|---|---|---|
| `DORMIDO` | «Hey Jarvis»: abre la sesión. | Se descarta sin efecto ni aviso. |
| `IDLE` | «Hey Jarvis»: vuelve a escucha. «Buenas noches Jarvis»: cierra la sesión. | Se descarta sin efecto ni aviso. |
| `LISTENING_COMMAND` | Frases de control, «Hey Jarvis» y órdenes. | Se muestra como no reconocido (RN-51). |
| `AWAITING_*` | La respuesta al diálogo, las frases de control y «Hey Jarvis». | Respuesta no válida ([maquina-estados.md](maquina-estados.md)). |

La frase de activación se reconoce por similitud con la frase completa (`router.wake_threshold`, 80 ⚙): valen «hey jarvis», «Hey, Jarvis.», «hey jarbis» y «jarvis» a secas.

### Mientras el asistente habla

- **Frase del ciclo de vida** («Sesión iniciada. Le escucho.», «Le escucho.», «A su disposición.», «Buenas noches. Sesión cerrada.»): no se interrumpe. Lo que el usuario envía mientras suena se atiende, en orden, al terminar la frase.
- **Cualquier otra locución:** escribir «Hey Jarvis» la corta (RN-48).

### Cuenta de inactividad (RF-78)

En `LISTENING_COMMAND`, pasados 30 s ⚙ (`input.inactivity_to_idle_seconds`) sin actividad, el asistente pasa a reposo. Cuenta como actividad:

- enviar un texto, se reconozca o no;
- teclear en la caja sin enviar: la interfaz publica `UserTyping` como mucho una vez por segundo.

La cuenta empieza al terminar cada locución y no corre durante un turno en curso. Fuera de `LISTENING_COMMAND`, teclear no tiene efecto.

### Antes de que el núcleo esté listo

La ventana aparece antes de que termine la carga de la voz. Lo que el usuario envía en ese intervalo se atiende en cuanto el núcleo está listo.

## Interfaz

```python
@dataclass(frozen=True)
class TextSubmitted(Event):       # interfaz → núcleo, con publish_threadsafe
    text: str

@dataclass(frozen=True)
class UserTyping(Event): ...      # interfaz → núcleo, como mucho una vez por segundo

@dataclass(frozen=True)
class CommandReceived(Event):     # núcleo → interfaz: subtítulo de la orden (RF-89)
    text: str
    recognized: bool
```

## Criterios de aceptación

- Enter publica `TextSubmitted` con el texto y vacía la caja; un envío vacío no publica nada (`pytest-qt`).
- Teclear publica `UserTyping` como mucho una vez por segundo; cambiar el texto por código no lo publica.
- El texto de ayuda sigue al estado.
- Con dobles: CU-03, CU-04 y CU-05 completos escribiendo cada frase, incluidas las variantes con erratas de «Hey Jarvis».
- Teclear reinicia la cuenta de inactividad en escucha y no tiene efecto en reposo ni en dormido.

## Prohibiciones

- El proceso no abre el micrófono ni captura audio.
- La interfaz no decide qué significa el texto ni cambia el estado del asistente.
- El texto de las órdenes no se registra en nivel `INFO` (RES-48).
- No se añade una vía alternativa de entrada por voz mediante configuración.
