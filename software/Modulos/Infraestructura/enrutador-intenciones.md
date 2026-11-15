# Enrutador de intenciones

- **Código:** `intent_router/`.
- **Volver a:** [contexto](../../contexto.md) · [arquitectura](../../arquitectura.md) · frases en [catalogo-intenciones.md](../../catalogo-intenciones.md).

## Propósito

Identificar en el texto escrito por el usuario su intención y sus entidades, de forma determinista (RNF-10), y decir al orquestador qué hacer con él según el estado. Es código puro: no ejecuta acciones ni habla.

## 1. Decisión según el estado

`route(text, state, dialogue) -> RouteResult`, en este orden:

1. **Texto vacío** → se descarta (la interfaz no lo envía; el orquestador lo ignora).
2. **Frase de activación**, en todos los estados: se compara la frase completa normalizada con «hey jarvis» y «jarvis» usando `fuzz.ratio`; se acepta con ≥ 80 ⚙ (`router.wake_threshold`). → `WakeWord`. En `DORMIDO` es lo único que se reconoce: cualquier otra cosa se descarta sin efecto.
3. **Frases de control** (RN-52), en `LISTENING_COMMAND` y `AWAITING_*`: se compara la frase completa normalizada con cada frase de control usando `fuzz.ratio`; se acepta con ≥ 80 ⚙. → `Control(reposo | cerrar | cancelar)`. Si una frase alcanza a la vez el umbral de activación y el de control, gana la de mayor similitud y, a igualdad, la de control.
4. **`IDLE`**: además de la frase de activación, solo la frase de cierre, con `fuzz.ratio` ≥ 85 ⚙ → `ClosingPhraseInIdle`; cualquier otra cosa → se descarta sin efecto.
5. **`AWAITING_*`**: el texto se valida contra el `expected_type` del diálogo → `Answer(value)` o `Answer(invalid)`. Nunca se clasifica como intención nueva.
6. **`LISTENING_COMMAND`**: clasificación contra los patrones → `IntentMatched` o `NoMatch`.

Comparar la frase completa con `fuzz.ratio` (no con coincidencia parcial) evita falsos positivos: «muchas gracias Jarvis por todo» no pasa a reposo, y «jarvis abre el navegador» no cuenta como frase de activación.

## 2. Normalización

`normalizer.py`, aplicada al texto y a los patrones:

1. Minúsculas.
2. Quitar tildes y diéresis; la `ñ` se conserva.
3. Quitar signos de puntuación, salvo `.`, `/`, `\`, `:`, `_` y `-` dentro de una palabra (nombres de archivo y rutas).
4. Colapsar espacios.
5. Aplicar los **alias** de la configuración, palabra a palabra o por secuencias de palabras: aceptan formas alternativas de escribir una palabra («guit» → `git`, «ce de» → `cd`, «ele ese» → `ls`).

El texto original, sin normalizar, se conserva para las entidades de texto libre.

## 3. Patrones

Un patrón es una frase con texto fijo y huecos: `"crea el archivo {nombre} en {ruta}"`. Cada módulo declara los suyos en `intents()` ([arquitectura.md](../../arquitectura.md), sección 5). No hay un catálogo central en el código: [catalogo-intenciones.md](../../catalogo-intenciones.md) documenta el resultado.

Reglas de escritura:

- Un patrón empieza siempre por texto fijo.
- Dos huecos nunca son contiguos: los separa texto fijo.
- No hay sintaxis de partes opcionales: cada variante es un patrón distinto.
- Un mismo patrón no puede pertenecer a dos intenciones (se comprueba al registrar).

### Coincidencia

Con el texto dividido en palabras:

1. **Patrón sin huecos:** `fuzz.ratio` entre la frase completa y el patrón.
2. **Patrón con huecos:** el patrón se divide en segmentos fijos y huecos.
   - El primer segmento fijo, de *k* palabras, se compara con las *k* primeras palabras del texto.
   - Cada segmento fijo intermedio o final se busca en el resto del texto, eligiendo la **última** posición cuya similitud supere el umbral y que deje los huecos vecinos no vacíos (si el nombre contiene la palabra separadora, gana la última aparición).
   - Cada hueco recibe las palabras que quedan entre los segmentos fijos.
   - Puntuación del patrón = la menor similitud de sus segmentos fijos.
3. **Similitud de un segmento fijo:** `fuzz.ratio` entre el segmento y la ventana de palabras. Un segmento de 3 caracteres o menos («cd», «ls», «en», «a») exige coincidencia exacta.
4. **Solo el texto fijo cuenta.** El contenido de los huecos no influye en la puntuación, así que una entidad en otro idioma no la reduce (RNF-15).
5. Un patrón es candidato si su puntuación ≥ 80 ⚙ y todos sus huecos obligatorios tienen contenido.

### Elección entre candidatos

1. Mayor puntuación.
2. A igualdad (diferencia < 3 puntos): más palabras de texto fijo, es decir, el patrón más específico. Así «abre la carpeta proyectos» elige *abrir carpeta* frente a *abrir aplicación*.
3. A igualdad: orden de registro de los módulos y, dentro de cada módulo, de sus intenciones.

4. **Entidades que no se resuelven:** si las entidades del candidato elegido no se pueden resolver (sección 4), se prueba el siguiente candidato, en el mismo orden. Si ninguno se resuelve, el resultado es el error del primero. Así «abre el navegador» no se pierde por un patrón más específico que esperaba un número.

El resultado es siempre el mismo para el mismo texto y el mismo estado del sistema (directorio de trabajo, catálogos).

**Regla para quien añade patrones:** un patrón nuevo no debe poder leerse como caso particular de otro con una entidad de tipo distinto. El juego de frases de prueba incluye un caso de desambiguación por cada par de patrones que comparten sus primeras palabras.

## 4. Entidades

Tras elegir el patrón, cada hueco se resuelve según su `SlotType`. Si un hueco obligatorio no se puede resolver con ningún candidato (sección 3), el resultado es `IntentMatched` con `error`, y el orquestador crea la tarea en `error` con la frase de error del tipo. No se pregunta, salvo donde un módulo lo define.

| Tipo | Resolución | Error |
|---|---|---|
| `TEXT` | El texto original del hueco, recortado. | — |
| `INTEGER` | `numbers.py`: cifras («12»), números en letras de 0 a 999 («doce»), ordinales del 1 al 10 («primero», «la segunda»). | «No he entendido el número.» |
| `DURATION` | `durations.py`: `{número} {unidad}` con unidad segundos, minutos, horas, días; «media hora», «un cuarto de hora», «una hora y media». | «No he entendido la duración.» |
| `DATETIME` | `datetimes.py`: gramática cerrada de la sección 5. Debe ser futura. | «No he entendido la fecha.» / «Esa fecha ya ha pasado.» |
| `DIR_PATH` | `paths.py`: sección 6. Debe existir y ser carpeta; si no, RN-41. | «La carpeta X no existe.» / «X no es una carpeta.» |
| `NEW_NAME` | `names.py`: sección 7. | «Ese nombre no es válido.» |
| `NEW_PATH` | Como `NEW_NAME`, con «barra» como separador de niveles. | «Ese nombre no es válido.» |
| `CATALOG` | `catalogs.py`: `process.extractOne` con `fuzz.WRatio` sobre los nombres normalizados de la lista indicada; se acepta con ≥ 75 ⚙. A igualdad, orden alfabético. | «No encuentro X.» |
| `COMMAND_LINE` | La primera palabra, tras los alias, debe ser un binario permitido; el resto son argumentos, separados por espacios, con «guion» → `-`, «guion guion» → `--`, «punto» → `.`. | «Ese comando no está permitido.» |

Los proveedores de listas para `CATALOG` (aplicaciones, páginas, protocolos, estructuras) los registra cada módulo y se consultan en el momento de resolver, de modo que reflejan la configuración vigente.

## 5. Gramática de fechas y horas

Analizador por palabras, sin expresiones regulares de lenguaje natural (RES-25). Acepta, sobre el texto normalizado:

| Forma | Ejemplos |
|---|---|
| Relativa | «en 10 minutos», «dentro de dos horas», «en media hora», «en 3 días» |
| Día + hora | «hoy a las 18», «mañana a las 9 y media», «pasado mañana a las 10 y cuarto», «esta tarde a las 5», «esta noche a las 10» |
| Día de la semana | «el lunes a las 10», «el viernes» (próxima aparición; si es hoy, la semana siguiente) |
| Fecha | «el 5 de diciembre a las 12», «el 5 de diciembre de 2027», «el día 20 a las 8» (mes actual o siguiente) |
| Solo hora | «a las 7», «a las 19 30», «a las 7 de la tarde» (hoy si aún no ha pasado; si no, mañana) |

Reglas: hora de 0 a 23; «de la mañana», «de la tarde», «de la noche» fijan mañana o tarde; sin indicación, una hora de 1 a 7 se interpreta como de la tarde si en horario de mañana ya ha pasado hoy; «y media», «y cuarto», «menos cuarto» y «{h} {mm}» fijan los minutos; sin hora, las 9:00 ⚙. El resultado es una fecha con la zona horaria local.

`datetimes.find_suffix(words)` localiza la expresión de fecha más larga al final de un texto; lo usa Recordatorio para separar el texto del recordatorio de su fecha («recuérdame llamar a Ana mañana a las 9»).

## 6. Resolución de rutas escritas

`paths.resolve(spoken, workdir, places) -> Path`, en este orden:

1. **Palabras especiales:** «aquí», «esta carpeta» → directorio de trabajo; «atrás», «arriba», «carpeta anterior» → carpeta padre; «inicio», «carpeta personal» → carpeta del usuario.
2. **Ruta literal:** si el texto contiene `/`, `\` o `:`, se usa tal cual (relativa al directorio de trabajo si no es absoluta).
3. **Niveles:** el texto se divide por la palabra «barra». Para cada nivel:
   - Primer nivel: un **lugar con nombre** de la configuración (escritorio, documentos, descargas, y los que defina el usuario), con similitud ≥ 85; o una unidad («disco ce» → `C:\`); o, si no, un hijo del directorio de trabajo.
   - Niveles siguientes: un hijo de la carpeta resuelta hasta ese punto.
   - Un hijo se busca entre las subcarpetas reales con `fuzz.WRatio` ≥ 80 ⚙ sobre nombres normalizados; gana la mayor similitud y, a igualdad, el orden alfabético.
4. Si un nivel no se resuelve → error «no existe» con el nombre escrito.

La respuesta de voz siempre dice el nombre real de la carpeta resuelta, para que el usuario detecte una resolución equivocada.

## 7. Nombres de archivo y carpeta nuevos

`names.build(spoken) -> str`: «punto» entre palabras se convierte en `.` («notas punto txt» → `notas.txt`); «guion bajo» en `_`; «guion» en `-`; el resto de las palabras se conservan separadas por espacios. Se rechaza un nombre vacío, con caracteres no permitidos por el sistema de archivos o reservado.

## 8. Registro

```python
class IntentRouter:
    def register(self, module: ActionModule) -> None: ...            # valida y compila sus patrones
    def register_catalog(self, name: str, provider: Callable[[], Sequence[str]]) -> None: ...
    def route(self, text: str, state: AssistantState, dialogue: DialogueContext | None) -> RouteResult: ...
    def resolve_params(self, module: str, action: str, raw: Mapping[str, object]) -> Mapping[str, object]: ...
    def help(self) -> Sequence[HelpGroup]: ...                        # para RF-92
```

`resolve_params` aplica la misma resolución de entidades a los parámetros de una tarea de protocolo, que llegan como texto desde la configuración.

Las intenciones del núcleo (control, ayuda, repetir, mostrar u ocultar la pantalla) no pertenecen a ningún módulo de acción: las registra el orquestador como módulo interno `nucleo`.

## Criterios de aceptación

- El juego de frases de [catalogo-intenciones.md](../../catalogo-intenciones.md) se ejecuta como prueba parametrizada y cumple RNF-11.
- Las frases de control negativo no producen ninguna intención ni cuentan como frase de activación.
- La frase de activación se reconoce en todos los estados, con erratas, y su umbral es configurable.
- Cada analizador de entidades tiene pruebas con reloj falso.
- Registrar dos intenciones con el mismo patrón falla al arrancar.
- Misma entrada, misma salida, en 1000 repeticiones (RNF-10).

## Prohibiciones

- No se usan expresiones regulares complejas para lenguaje natural (RES-25).
- No se usan modelos generativos ni clasificadores estadísticos.
- El enrutador no ejecuta acciones, no habla y no publica eventos.
