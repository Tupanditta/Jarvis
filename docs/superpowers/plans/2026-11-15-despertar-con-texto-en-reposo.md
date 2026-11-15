# Despertar con cualquier texto en reposo — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** En `IDLE`, cualquier texto no vacío despierta al asistente en silencio y se atiende como orden en el mismo envío.

**Architecture:** El router enruta en `IDLE` casi como en `LISTENING_COMMAND` (devuelve `IntentMatched` o `NoMatch`). La FSM, en `_resting`, despierta en silencio ante esas entradas y luego aplica los efectos de `_listening`. El orquestador no cambia.

**Tech Stack:** Python 3.11, pytest, rapidfuzz.

**Spec:** `docs/superpowers/specs/2026-11-15-despertar-con-texto-en-reposo-design.md`

## Global Constraints

- Pip solo en el venv: `.\implementation\.venv\Scripts\pip.exe` (no hace falta instalar nada).
- No crear commits: el propietario los hace. Los pasos «Commit» de este plan se sustituyen por «dejar los cambios listos».
- `DORMIDO` no cambia.
- El router sigue siendo puro; la FSM es la única dueña del estado.
- Comandos desde `implementation/`: `.venv/Scripts/python.exe -m pytest ...`

## Review Focus

- Texto solo de espacios en `IDLE`: no despierta (el orquestador ya lo descarta antes del router; el router debe devolver `None` si `normalized` queda vacío, p. ej. «¿?»).
- «gracias jarvis» o «cancelar» en `IDLE`: sin efecto y sin `CommandReceived` (el router devuelve `None`, no `Control`).
- Frase de cierre con erratas entre 80 y 84 de parecido en `IDLE`: despierta como no reconocida, no cierra.
- Orden en `IDLE`: no se oye «Le escucho» (`rig.spoken() == []`).
- Tras despertar con una orden, 30 s sin escribir vuelven a `IDLE`.

---

### Task 1: Router — enrutar en reposo

**Files:**
- Modify: `implementation/src/jarvis_assistant/intent_router/router.py:69-80` (`route`) y el docstring del módulo
- Test: `implementation/tests/unit/intent_router/test_router_control.py`

**Interfaces:**
- Produces: `IntentRouter.route(text, AssistantState.IDLE)` devuelve, en este orden de prioridad:
  1. `WakeWord()` si `_is_wake`.
  2. `ClosingPhraseInIdle()` si `fuzz.ratio(normalized, CLOSING_PHRASE) >= idle_closing_threshold`.
  3. `None` si `normalized` está vacío.
  4. `None` si `_attending(normalized)` es `Control(REPOSO)` o `Control(CANCELAR)`.
  5. `IntentMatched(...)` si `_core_intent(normalized)` coincide.
  6. `NoMatch(text)` en el resto (incluido `Control(CERRAR)` por debajo del umbral de reposo).
- `DORMIDO` y los estados de escucha no cambian.

- [ ] **Step 1: Ajustar las pruebas**

Sustituir `test_en_reposo_cualquier_otra_frase_se_descarta`, `test_en_reposo_el_umbral_es_mas_exigente_que_en_escucha` y `test_mostrar_la_pantalla_fuera_de_escucha_se_descarta` por:

```python
@pytest.mark.parametrize("text", ["gracias jarvis", "cancelar", "olvidalo", "", "   ", "¿?"])
def test_en_reposo_las_frases_sin_sentido_en_reposo_se_descartan(router, text):
    assert router.route(text, S.IDLE) is None


@pytest.mark.parametrize("text", ["abre el navegador", "qué tiempo hace hoy", "buenas noches"])
def test_en_reposo_un_texto_no_reconocido_despierta(router, text):
    assert router.route(text, S.IDLE) == NoMatch(text)


def test_en_reposo_el_umbral_de_cierre_es_mas_exigente_que_en_escucha():
    router = IntentRouter(RouterSettings(control_threshold=80, idle_closing_threshold=99))
    text = "buenas noches yarvis"
    assert router.route(text, S.LISTENING_COMMAND) == Control(ControlKind.CERRAR)
    assert router.route(text, S.IDLE) == NoMatch(text)


@pytest.mark.parametrize(
    ("text", "intent"), [("muestra la pantalla", SHOW_SCREEN), ("oculta la pantalla", HIDE_SCREEN)]
)
def test_en_reposo_mostrar_y_ocultar_la_pantalla_se_reconocen(router, text, intent):
    assert router.route(text, S.IDLE) == IntentMatched(intent)


def test_en_dormido_mostrar_la_pantalla_se_descarta(router):
    assert router.route("muestra la pantalla", S.DORMIDO) is None
```

- [ ] **Step 2: Ver que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/intent_router/test_router_control.py -v`
Expected: FAIL en `un_texto_no_reconocido_despierta`, `umbral_de_cierre`, `mostrar_y_ocultar_la_pantalla_se_reconocen`.

- [ ] **Step 3: Implementar la rama `IDLE` de `route` según el orden de Interfaces**

Extraer la rama a un método `_resting(self, text: str, normalized: str) -> Input | None`. Actualizar el docstring del módulo: en reposo cualquier texto se atiende.

- [ ] **Step 4: Ver que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/intent_router -v`
Expected: PASS.

### Task 2: FSM — despertar en silencio y atender

**Files:**
- Modify: `implementation/src/jarvis_assistant/core/state_machine.py:213-231` (`_resting`)
- Test: `implementation/tests/unit/core/test_state_machine.py`

**Interfaces:**
- Consumes: `IntentMatched`, `NoMatch` del router (Task 1).
- Produces: en `IDLE`, `handle(IntentMatched(i))` y `handle(NoMatch(t))` dejan el estado en `LISTENING_COMMAND` y devuelven `[PublishListeningResumed(silent=True), *efectos_de_listening]`, es decir:
  - `IntentMatched(i)` → `[PublishListeningResumed(silent=True), RunTurn(i)]`
  - `NoMatch(t)` → `[PublishListeningResumed(silent=True), PublishUnrecognized(t), RestartSilenceTimer()]`

- [ ] **Step 1: Pruebas nuevas**

```python
def test_reposo_con_una_intencion_despierta_en_silencio_y_ejecuta_el_turno():
    fsm = machine(S.IDLE)
    effects = fsm.handle(IntentMatched("nucleo.mostrar_pantalla"))
    assert fsm.state is S.LISTENING_COMMAND
    assert effects == [PublishListeningResumed(silent=True), RunTurn("nucleo.mostrar_pantalla")]


def test_reposo_con_frase_no_reconocida_despierta_en_silencio_y_la_publica():
    fsm = machine(S.IDLE)
    effects = fsm.handle(NoMatch("abre el navegador"))
    assert fsm.state is S.LISTENING_COMMAND
    assert effects == [
        PublishListeningResumed(silent=True),
        PublishUnrecognized("abre el navegador"),
        RestartSilenceTimer(),
    ]
```

`test_reposo_ignora_gracias_jarvis_y_el_silencio` se mantiene.

- [ ] **Step 2: Ver que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/core/test_state_machine.py -v`
Expected: FAIL en las dos pruebas nuevas.

- [ ] **Step 3: En `_resting`, para `IntentMatched | NoMatch`: pasar a `LISTENING_COMMAND` y devolver `[PublishListeningResumed(silent=True), *self._listening(entry)]`**

- [ ] **Step 4: Ver que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/unit/core -v`
Expected: PASS.

### Task 3: Integración, texto de ayuda y documentación

**Files:**
- Modify: `implementation/tests/integration/test_lifecycle.py` (`test_cu04_en_reposo_solo_se_atienden_la_activacion_y_el_cierre`, `test_cu05_a4_buenas_noches_sin_jarvis_se_ignora`)
- Modify: `implementation/src/jarvis_assistant/ui/view_models.py:37`
- Modify: `implementation/tests/manual/fase-1.md:44`
- Modify: `docs/superpowers/specs/2026-11-14-entrada-por-texto-design.md` (líneas 95, 131, 169-170 y 245: la regla «en reposo se descarta» y el texto de ayuda)

**Interfaces:**
- Consumes: Tasks 1 y 2.
- Produces: `PLACEHOLDER_RESTING = "En reposo. Escriba una orden"`.

- [ ] **Step 1: Pruebas de integración**

Sustituir `test_cu04_en_reposo_solo_se_atienden_la_activacion_y_el_cierre` por:

```python
async def test_cu04_en_reposo_gracias_jarvis_y_cancelar_no_tienen_efecto(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.write("gracias jarvis")
    await rig.write("cancelar")
    assert rig.state is S.IDLE
    assert rig.spoken() == [] and rig.of(events.CommandReceived) == []


async def test_cu04_en_reposo_una_orden_despierta_en_silencio_y_se_ejecuta(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.write("muestra la pantalla")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.ListeningResumed) == [events.ListeningResumed(silent=True)]
    assert rig.of(events.ShowScreenRequested) == [events.ShowScreenRequested(visible=True)]
    await rig.advance(30.5)
    assert rig.state is S.IDLE


async def test_cu04_en_reposo_un_texto_no_reconocido_despierta_y_se_muestra(rig):
    await rig.open_session()
    await rig.write("gracias jarvis")
    await rig.advance(1.0)
    rig.clear()
    await rig.write("abre el navegador")
    assert rig.state is S.LISTENING_COMMAND
    assert rig.spoken() == []
    assert rig.of(events.CommandReceived) == [
        events.CommandReceived("abre el navegador", recognized=False)
    ]
```

En `test_cu05_a4_buenas_noches_sin_jarvis_se_ignora`, tras el segundo `rig.write("buenas noches")`, esperar `S.LISTENING_COMMAND` en lugar de `S.IDLE` (sigue habiendo una sola sesión abierta).

- [ ] **Step 2: Ver que fallan antes de cambiar la ayuda y que pasan las de lógica**

Run: `.venv/Scripts/python.exe -m pytest tests/integration/test_lifecycle.py -v`
Expected: PASS (la lógica ya está en Tasks 1 y 2). Si falla, revisar las Tasks 1 y 2.

- [ ] **Step 3: Cambiar `PLACEHOLDER_RESTING` y la documentación**

`view_models.py:37` → `"En reposo. Escriba una orden"`. `fase-1.md:44` → la caja pasa a «En reposo. Escriba una orden». En la spec de entrada por texto: la regla de la línea 95 dice ahora que en reposo cualquier texto despierta en silencio y se atiende; línea 131 con el nuevo texto de ayuda; líneas 169-170 y 245 alineadas con el router de la Task 1. Añadir al principio de esa spec una referencia a `2026-11-15-despertar-con-texto-en-reposo-design.md`.

- [ ] **Step 4: Toda la batería**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo PASS.

- [ ] **Step 5: Dejar los cambios listos para que el propietario haga el commit**
