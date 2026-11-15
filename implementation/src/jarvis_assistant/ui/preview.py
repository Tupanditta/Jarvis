"""Vista previa de la interfaz (`--preview`, hud.md, sección 5).

Abre la interfaz con una secuencia de eventos simulados que recorre todos los estados, sin
voz, modelos, núcleo ni base de datos. Sirve para construir y revisar el aspecto (lista de
comprobación visual de Interfaz, sección 11). Lo que se escribe en la caja aparece como orden
no reconocida.
"""
import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, QTimer

from jarvis_assistant.core import events
from jarvis_assistant.core.events import Activity

LEVEL_INTERVAL_MS = 50  # 20 Hz, como el núcleo


@dataclass(frozen=True)
class Step:
    """Espera `delay` segundos y publica `event`. `speech`: segundos de voz simulada."""

    delay: float
    event: events.Event
    speech: float = 0.0


def _activity(state: str, activity: Activity) -> events.AssistantActivityChanged:
    return events.AssistantActivityChanged(state, activity)


def _task(task_id: int, status: str, description: str, *, module: str = "comandos",
          parent: int | None = None, detail: str | None = None) -> events.TaskUpdated:
    return events.TaskUpdated(task_id, parent, module, description, status, detail,
                              datetime.now())  # type: ignore[arg-type]


def _say(text: str, seconds: float, state: str, *, lifecycle: bool = False) -> list[Step]:
    return [
        Step(0.0, events.SpeechStarted(text, interruptible=not lifecycle), speech=seconds),
        Step(0.0, _activity(state, Activity.HABLANDO)),
    ]


def _done_speaking(state: str, activity: Activity, after: float) -> list[Step]:
    return [Step(after, events.SpeechFinished(False)), Step(0.0, _activity(state, activity))]


def script() -> list[Step]:
    """Recorrido completo: dormido, despertar, escucha, orden, procesando, hablando, tareas,
    pregunta (esperando), reposo, vuelta a escucha y cierre."""
    listening = "LISTENING_COMMAND"
    steps: list[Step] = [
        Step(1.5, _activity("DORMIDO", Activity.DORMIDO)),
        # Despertar con la frase de apertura (CU-03).
        *_say("Sesión iniciada. Le escucho.", 1.8, listening, lifecycle=True),
        Step(0.0, events.SessionOpened(1, datetime.now().date().isoformat())),
        Step(0.0, events.SessionChanged(1, datetime.now().date().isoformat(), False)),
        *_done_speaking(listening, Activity.ESCUCHANDO, 1.8),
        # Una orden que se procesa y responde.
        Step(2.0, events.CommandReceived("ejecuta git status", True)),
        Step(0.0, _activity(listening, Activity.PROCESANDO)),
        Step(0.0, _task(1, "pendiente", "git status")),
        Step(0.0, events.PanelActivated("comandos")),
        Step(1.6, _task(1, "completado", "git status")),
        *_say("Ejecutando git status.", 1.4, listening),
        *_done_speaking(listening, Activity.ESCUCHANDO, 1.4),
        # Una tarea que falla y otra que queda pendiente.
        Step(1.5, events.CommandReceived("abre el bloc de notas", True)),
        Step(0.0, _task(2, "error", "abrir bloc de notas", module="apertura",
                        detail="No se encuentra la aplicación")),
        Step(0.5, _task(3, "pendiente", "buscar informe", module="busqueda")),
        Step(1.5, events.CommandReceived("qué tiempo hace", False)),
        # Una pregunta: esperando.
        Step(1.5, events.SessionChanged(1, "prácticas de redes", True)),
        Step(0.0, events.DialogueOpened("¿Elimino la sesión 12?", "CONFIRMATION",
                                        ("Sí", "No", "Cancelar"), 15.0,
                                        {"id": 12, "name": "pruebas"})),
        Step(0.0, _activity("AWAITING_CONFIRMATION", Activity.ESPERANDO)),
        Step(3.0, events.DialogueClosed("cancelled")),
        Step(0.0, _task(3, "completado", "buscar informe", module="busqueda")),
        Step(0.0, _activity(listening, Activity.ESCUCHANDO)),
        # Reposo y vuelta a escucha.
        Step(2.0, events.CommandReceived("gracias jarvis", True)),
        *_say("A su disposición.", 1.4, "IDLE", lifecycle=True),
        Step(0.0, events.RestEntered()),
        *_done_speaking("IDLE", Activity.REPOSO, 1.4),
        Step(3.5, events.CommandReceived("hey jarvis", True)),
        *_say("Le escucho.", 1.0, listening, lifecycle=True),
        Step(0.0, events.ListeningResumed()),
        *_done_speaking(listening, Activity.ESCUCHANDO, 1.0),
        # Cierre de sesión (CU-05).
        Step(2.5, events.CommandReceived("buenas noches jarvis", True)),
        *_say("Buenas noches. Sesión cerrada.", 1.8, "DORMIDO", lifecycle=True),
        Step(0.0, events.SessionClosed()),
        *_done_speaking("DORMIDO", Activity.DORMIDO, 1.8),
    ]
    return steps


def voice_level(t: float) -> float:
    """Nivel simulado de la voz: sílabas de unos 180 ms con una envolvente suave."""
    syllable = abs(math.sin(t * math.pi / 0.18))
    return round(min(1.0, 0.25 + 0.6 * syllable * (0.7 + 0.3 * math.sin(t * 2.3))), 3)


class PreviewDriver(QObject):
    """Publica los pasos de `script()` en orden y, durante cada voz simulada, el nivel a 20 Hz.

    `speed` acelera el recorrido (las pruebas usan valores altos). Con `loop`, vuelve a
    empezar al terminar.
    """

    def __init__(
        self,
        deliver: Callable[[events.Event], None],
        *,
        steps: list[Step] | None = None,
        speed: float = 1.0,
        loop: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._deliver = deliver
        self._steps = steps if steps is not None else script()
        self._speed = speed
        self._loop = loop
        self._iterator: Iterator[Step] = iter(())
        self._step_timer = QTimer(self)
        self._step_timer.setSingleShot(True)
        self._step_timer.timeout.connect(self._next)
        self._level_timer = QTimer(self)
        self._level_timer.setInterval(max(1, round(LEVEL_INTERVAL_MS / speed)))
        self._level_timer.timeout.connect(self._level)
        self._speech_left = 0.0
        self._speech_t = 0.0
        self.finished_rounds = 0

    def start(self) -> None:
        self._iterator = iter(self._steps)
        self._schedule()

    def stop(self) -> None:
        self._step_timer.stop()
        self._level_timer.stop()

    def user_event(self, event: events.Event) -> None:
        """Acción del usuario en la vista previa: el texto se muestra como no reconocido."""
        if isinstance(event, events.TextSubmitted):
            self._deliver(events.CommandReceived(event.text, recognized=False))

    def _schedule(self) -> None:
        self._pending = next(self._iterator, None)
        if self._pending is None:
            self.finished_rounds += 1
            if self._loop:
                self.start()
            return
        self._step_timer.start(max(0, round(self._pending.delay * 1000 / self._speed)))

    def _next(self) -> None:
        step = self._pending
        if step is None:
            return
        if isinstance(step.event, events.SpeechFinished):
            self._level_timer.stop()
            self._deliver(events.AudioLevel(0.0, "none"))
        self._deliver(step.event)
        if step.speech > 0:
            self._speech_t = 0.0
            self._level_timer.start()
        self._schedule()

    def _level(self) -> None:
        self._speech_t += LEVEL_INTERVAL_MS / 1000
        self._deliver(events.AudioLevel(voice_level(self._speech_t), "assistant"))


def run_preview(settings: object, debug: bool) -> int:
    """Arranca la vista previa: solo Qt, sin núcleo, voz ni modelos."""
    from PySide6.QtGui import QGuiApplication

    from jarvis_assistant.ui.app import UiApp

    qt_app = QGuiApplication.instance() or QGuiApplication([])
    qt_app.setApplicationName("Jarvis (vista previa)")
    driver: PreviewDriver | None = None

    def publish(event: events.Event) -> None:
        if driver is not None:
            driver.user_event(event)

    ui = UiApp(publish=publish, settings=settings, debug=debug)  # type: ignore[arg-type]
    driver = PreviewDriver(ui.on_event)
    ui.shutdown()  # sin bandeja: cerrar la pantalla termina la vista previa
    ui.start()
    driver.start()
    return qt_app.exec()
