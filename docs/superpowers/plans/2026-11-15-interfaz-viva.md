# Interfaz viva — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Orbe central con capas «pensantes», fondo vivo en toda la pantalla y contraste fuerte entre reposo y despierto, todo movido por un director común.

**Architecture:** `Orb.qml` es el director: añade las propiedades de control `energy`, `chaos` y `beatRate`, los relojes `flow` y `mind`, y la función `wave(r)`. Cada elemento nuevo es un archivo QML pequeño que solo lee esas señales. El fondo (`LifeField.qml`) vive en `SessionScreen.qml`, por debajo del orbe y de los paneles, y recibe el orbe como `conductor`.

**Tech Stack:** QML (Qt Quick, Qt Quick Shapes) con PySide6 ≥ 6.7; pytest-qt.

**Spec:** `docs/superpowers/specs/2026-11-15-interfaz-viva-design.md`

## Global Constraints

- Pip solo en el venv (no hace falta instalar nada).
- No crear commits: el propietario los hace.
- El aspecto de dormido no cambia. No se tocan `MiniOrb.qml`, `HudOverlay.qml`, paneles, `view_models.py` ni `preview.py`.
- Ningún componente define colores propios: salen de `Theme.qml`.
- Sin `Canvas` a pantalla completa ni sombreadores compilados.
- Objetivo 60 fps; nunca menos de 30 (RNF-21).
- Comandos desde `implementation/`: `.venv/Scripts/python.exe -m pytest ...`

## Review Focus

- Dormido: con `brightness` 0 no se dibuja ni se anima ningún elemento nuevo.
- `reduceMotion`: todo quieto, sin latido (`pulse` 0), sin avisos de QML.
- `quality: low`: sin fondo, sin red, núcleo liso; `medium`: la mitad, sin retícula ni estelas.
- Cambio de tamaño de la ventana (640 × 480 a 1920 × 1080): el fondo se recoloca sin avisos.
- Transición interrumpida por otra: `energy`, `chaos` y `beatRate` continúan desde su valor actual.

---

### Task 1: Director y contraste (`Orb.qml`, `Theme.qml`)

**Files:**
- Modify: `src/jarvis_assistant/ui/qml/orb/Orb.qml`, `src/jarvis_assistant/ui/qml/Theme.qml`
- Create: `src/jarvis_assistant/ui/qml/orb/field.js`
- Modify: `pyproject.toml` (`package-data`: `ui/qml/*/*.js`)
- Test: `tests/integration/test_qml.py`

**Interfaces — Produces (propiedades de `Orb`):**
- Control (animables, en `aspect()`, `tween` y las cuatro transiciones): `energy`, `chaos`, `beatRate` (latidos/s).
- Derivadas: `flow` (segundos × `energy`), `mind` (segundos × (0,25 + 1,75 × `chaos`)), `beatPhase` (0–1), `pulse` (0–1; 0 con `reduceMotion`), `reach` = 2,5 (en unidades de `d`), `live` (visibilidad de las capas vivas; sustituye el uso de `particles`).
- `function wave(r)`: brillo 0–1 del latido a la distancia `r` (en unidades de `d`).
- `field.js` (`.pragma library`): `hash(i, salt)` → 0–1 determinista; `nearest(points, k)` → lista de parejas `[a, b]` sin repetir.
- `Theme.primaryHot`: blanco cian del centro del núcleo.

Valores de `aspect()`:

| | reposo | escuchando | procesando | esperando |
|---|---|---|---|---|
| `brightness` | 0,22 | 1 | 1 | 1 |
| `tint` | 0,7 | 0 | 0 | 0 |
| `energy` | 0,08 | 0,6 | 1 | 0,45 |
| `chaos` | 0 | 0,35 | 1 | 0,2 |
| `beatRate` | 0 | 1/2,4 | 1/0,9 | 1/1,8 |
| `particles` | 0 | 1 | 1 | 1 |

- [ ] Prueba `test_el_orbe_distingue_reposo_de_despierto`: tras `AssistantActivityChanged` a REPOSO y esperar el fundido, `brightness` ≤ 0,25, `energy` < 0,1 y `chaos` == 0; a PROCESANDO, `brightness` == 1, `energy` == 1, `chaos` == 1. El orbe se busca con `objectName: "orb"`.
- [ ] Verla fallar, implementar, verla pasar.

### Task 2: Elementos del centro

**Files:**
- Modify: `orb/OrbCore.qml` (plasma), `orb/DataRing.qml` (segmentos que parpadean), `orb/Orb.qml` (montaje, halo, onda)
- Create: `orb/NeuralNet.qml`, `orb/GyroArcs.qml`, `orb/Satellites.qml`, `orb/Glyphs.qml`

**Interfaces — Consumes:** las señales de la tarea 1. Cada elemento recibe por propiedades lo que usa (`d`, `color`, `flow`, `mind`, `chaos`, `strength`, `level`) y, si reacciona al latido, `conductor` (el `Orb`).

- [ ] Ampliar `test_hay_qml_de_todas_las_partes_de_la_interfaz` con los archivos nuevos; verla fallar.
- [ ] Implementar. Cantidades: red 28 nodos (`high`), 14 (`medium`), 0 (`low`); glifos 10 / 5 / 0; satélites 5 con estela solo en `high`; arcos 3 siempre.
- [ ] `pytest tests/integration/test_qml.py`: compila cada archivo y recorre la vista previa en las seis combinaciones de calidad y movimiento sin avisos.

### Task 3: Fondo vivo

**Files:**
- Create: `orb/LifeField.qml` (contenedor), `orb/Constellation.qml` (mini orbes, enlaces y señales), `orb/SatelliteOrbs.qml`, `orb/Dust.qml`, `orb/Lattice.qml`
- Modify: `SessionScreen.qml` (un `LifeField` antes del `Orb`)

**Interfaces — Consumes:** `conductor: Orb`, `quality`, y el centro del orbe en coordenadas de la pantalla.

- [ ] Ampliar la prueba de archivos; verla fallar.
- [ ] Implementar. Cantidades: mini orbes 45 / 22 / 0; polvo 70 / 35 / 0; orbes satélite 5 / 5 / 0; retícula solo en `high`. En reposo solo queda a la vista uno de cada cuatro mini orbes, sin enlaces.
- [ ] `pytest tests/integration/test_qml.py` completo.

### Task 4: Revisión visual, rendimiento y documentación

- [ ] Capturar la pantalla en reposo, escuchando, hablando, procesando y esperando (script temporal fuera del repositorio) y ajustar valores.
- [ ] Medir fotogramas con `--preview` y el contador de diagnóstico; reducir cantidades si baja de 60.
- [ ] Actualizar `software/Interfaz/README.md`: color (`primary.hot`), secciones 3, 5, 10 y 11.
- [ ] `pytest` completo y `ruff check`.
