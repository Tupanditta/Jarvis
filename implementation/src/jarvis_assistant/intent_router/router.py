"""Despacho del texto escrito según el estado (enrutador-intenciones.md).

Código puro: no ejecuta acciones, no habla y no publica eventos. Reconoce la frase de
activación, las frases de control y el cierre en reposo, y clasifica las órdenes contra los
patrones que registran los módulos de acción, resolviendo sus entidades. En reposo, cualquier
otro texto se atiende como orden: la FSM despierta en silencio. En espera de una respuesta,
el texto se valida contra el tipo que espera la pregunta (`answers.py`).

Reconocer una orden tiene dos pasos: `prepare` compara el texto con los patrones y `resolve`
resuelve sus entidades. Van separados porque una orden que espera en la cola se resuelve
cuando le llega el turno: «ve a proyectos -- ve a jarvis» resuelve «jarvis» ya dentro de
«proyectos».
"""
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo
from pathlib import Path

from rapidfuzz import fuzz

from jarvis_assistant.config import DEFAULT_BINARIES, Binary, RouterSettings
from jarvis_assistant.core.action_api import (
    ExpectedType,
    HelpEntry,
    HelpGroup,
    Intent,
    IntentSpec,
    Phrase,
    Slot,
    SlotType,
)
from jarvis_assistant.core.state_machine import (
    AssistantState,
    ClosingPhraseInIdle,
    Control,
    ControlKind,
    Input,
    IntentMatched,
    NoMatch,
    WakeWord,
)
from jarvis_assistant.core.workdir import Workdir
from jarvis_assistant.intent_router import answers, patterns
from jarvis_assistant.intent_router.normalizer import Tokens, normalize, tokenize
from jarvis_assistant.intent_router.slots import (
    catalogs,
    command_line,
    datetimes,
    durations,
    names,
    numbers,
    paths,
)

CLOSING_PHRASE = "buenas noches jarvis"

# Frases de activación ya normalizadas.
WAKE_PHRASES: tuple[str, ...] = ("hey jarvis", "jarvis")

# Frases de control ya normalizadas (catalogo-intenciones.md, sección 1).
CONTROL_PHRASES: tuple[tuple[str, ControlKind], ...] = (
    ("gracias jarvis", ControlKind.REPOSO),
    (CLOSING_PHRASE, ControlKind.CERRAR),
    ("cancelar", ControlKind.CANCELAR),
    ("cancela", ControlKind.CANCELAR),
    ("olvidalo", ControlKind.CANCELAR),
    ("dejalo", ControlKind.CANCELAR),
)

CORE_MODULE = "nucleo"
SHOW_SCREEN = Intent(CORE_MODULE, "mostrar_pantalla")
HIDE_SCREEN = Intent(CORE_MODULE, "ocultar_pantalla")
HELP = Intent(CORE_MODULE, "ayuda")
REPEAT = Intent(CORE_MODULE, "repetir")
# «aparta {ventana}»: su entidad `ventana` es el título de una ventana flotante.
ASIDE_WINDOW = "apartar_ventana"
ASIDE_WINDOWS = Intent(CORE_MODULE, "apartar_ventanas")
RESTORE_WINDOW = "desapartar_ventana"  # también con la entidad `ventana`
RESTORE_WINDOWS = Intent(CORE_MODULE, "desapartar_ventanas")
WINDOWS_CATALOG = "ventanas"

SAME_SCORE_MARGIN = 3  # puntos por debajo de los cuales dos candidatos empatan
_TEXT_EDGES = " .,;:!?¿¡\"'«»"

_ATTENDING = (
    AssistantState.LISTENING_COMMAND,
    AssistantState.AWAITING_CONFIRMATION,
    AssistantState.AWAITING_PARAMETER,
)

Provider = Callable[[], Sequence[str]]


class _CoreIntents:
    """Intenciones del núcleo (catalogo-intenciones.md, sección 2). Las ejecuta el
    orquestador: no pertenecen a ningún módulo de acción."""

    name = CORE_MODULE
    title = "Asistente"

    def __init__(self, windows: Provider) -> None:
        self._windows = windows

    def catalogs(self) -> Mapping[str, tuple[Provider, ...]]:
        return {WINDOWS_CATALOG: (self._windows,)}

    def intents(self) -> Sequence[IntentSpec]:
        return (
            IntentSpec(
                "ayuda", ("ayuda", "qué puedes hacer", "qué sabes hacer"),
                description="Mostrar las órdenes disponibles", example="Ayuda",
                panel="ayuda", in_protocols=False,
            ),
            IntentSpec(
                "repetir", ("repite", "repítelo", "puedes repetir"),
                description="Repetir la última respuesta", example="Repite",
                in_protocols=False,
            ),
            IntentSpec(
                "mostrar_pantalla", ("muestra la pantalla", "pantalla completa"),
                description="Traer la pantalla de sesión al frente",
                example="Muestra la pantalla", in_protocols=False,
            ),
            IntentSpec(
                "ocultar_pantalla", ("oculta la pantalla", "minimiza la pantalla"),
                description="Minimizar la pantalla de sesión", example="Oculta la pantalla",
                in_protocols=False,
            ),
            IntentSpec(
                ASIDE_WINDOW, ("aparta {ventana}", "aparta la ventana de {ventana}"),
                slots=(Slot("ventana", SlotType.CATALOG, catalog=WINDOWS_CATALOG),),
                description="Apartar la ventana de un módulo a un borde",
                example="Aparta comandos", in_protocols=False,
            ),
            IntentSpec(
                ASIDE_WINDOWS.action,
                ("aparta módulos", "aparta los módulos", "aparta todas las ventanas"),
                description="Apartar todas las ventanas abiertas",
                example="Aparta módulos", in_protocols=False,
            ),
            IntentSpec(
                RESTORE_WINDOW,
                ("desaparta {ventana}", "desaparta la ventana de {ventana}"),
                slots=(Slot("ventana", SlotType.CATALOG, catalog=WINDOWS_CATALOG),),
                description="Devolver a su sitio la ventana apartada de un módulo",
                example="Desaparta comandos", in_protocols=False,
            ),
            IntentSpec(
                RESTORE_WINDOWS.action,
                ("desaparta módulos", "desaparta los módulos", "desaparta todas las ventanas"),
                description="Devolver a su sitio todas las ventanas apartadas",
                example="Desaparta módulos", in_protocols=False,
            ),
        )  # fmt: skip


class RegistrationError(ValueError):
    """Un módulo declara una intención que no se puede registrar."""


class ParamError(ValueError):
    """Una entidad no se puede resolver. `phrase`: el motivo, para decirlo."""

    def __init__(self, phrase: Phrase) -> None:
        super().__init__(phrase.id)
        self.phrase = phrase


@dataclass(frozen=True)
class _Registered:
    module: str
    spec: IntentSpec
    pattern: patterns.Pattern
    order: int


@dataclass(frozen=True)
class Order:
    """Orden reconocida por sus patrones, con las entidades todavía sin resolver.

    `candidates`: los patrones que coinciden, en orden de elección. Cuál gana se sabe al
    resolver las entidades (`IntentRouter.resolve`).
    """

    text: str
    tokens: Tokens
    candidates: tuple[tuple[patterns.Match, _Registered], ...]

    @property
    def specs(self) -> tuple[tuple[str, IntentSpec], ...]:
        """Las intenciones que la orden puede acabar siendo, con su módulo."""
        return tuple((item.module, item.spec) for _found, item in self.candidates)


def _best(normalized: str, phrases: Iterable[str]) -> float:
    return max(fuzz.ratio(normalized, phrase) for phrase in phrases)


class IntentRouter:
    def __init__(
        self,
        settings: RouterSettings,
        aliases: Mapping[str, str] | None = None,
        *,
        binaries: Sequence[Binary] = DEFAULT_BINARIES,
        places: Mapping[str, Path] | None = None,
        workdir: Workdir | None = None,
        now: Callable[[], datetime] | None = None,
        local_tz: tzinfo | None = None,
        windows: Sequence[str] = (),
    ) -> None:
        """`now`: el reloj del núcleo, para las fechas (`DATETIME`). `local_tz`: la zona
        horaria en la que se interpretan; None, la del sistema. `windows`: títulos de las
        ventanas flotantes, para «aparta {ventana}»; los da la interfaz (sin ella, ninguno)."""
        self._windows = tuple(windows)
        self._workdir = workdir or Workdir(Path.home())
        self._now = now or (lambda: datetime.now(UTC))
        self._tz = local_tz
        self._patterns: list[_Registered] = []
        self._keys: dict[str, str] = {}
        self._specs: dict[tuple[str, str], list[IntentSpec]] = {}
        self._titles: dict[str, str] = {}
        self._catalogs: dict[str, tuple[Provider, ...]] = {}
        self.configure(settings, aliases, binaries=binaries, places=places)
        self.register(_CoreIntents(lambda: self._windows))

    def configure(
        self,
        settings: RouterSettings,
        aliases: Mapping[str, str] | None = None,
        *,
        binaries: Sequence[Binary] = DEFAULT_BINARIES,
        places: Mapping[str, Path] | None = None,
    ) -> None:
        """Aplica la configuración vigente (se recarga al abrir cada sesión, RF-96)."""
        self._settings = settings
        self._aliases = dict(aliases or {})
        self._binaries = tuple(binaries)
        self._places = dict(places or {})

    # --- Registro ----------------------------------------------------------------------------

    def register(self, module: object) -> None:
        """Valida y compila los patrones de las intenciones de `module`."""
        name: str = module.name  # type: ignore[attr-defined]
        if name in self._titles:
            raise RegistrationError(f"El módulo «{name}» ya está registrado")
        for catalog, providers in getattr(module, "catalogs", dict)().items():
            self.register_catalog(catalog, *providers)
        compiled: list[_Registered] = []
        keys: dict[str, str] = {}
        for spec in module.intents():  # type: ignore[attr-defined]
            intent = f"{name}.{spec.action}"
            slots = {slot.name: slot for slot in spec.slots}
            for slot in spec.slots:
                if slot.type is SlotType.CATALOG and slot.catalog not in self._catalogs:
                    raise RegistrationError(f"{intent}: catálogo desconocido «{slot.catalog}»")
            if not spec.patterns:
                raise RegistrationError(f"{intent}: no tiene patrones")
            for source in spec.patterns:
                try:
                    pattern = patterns.compile_pattern(source)
                except patterns.PatternError as error:
                    raise RegistrationError(f"{intent}: {error}") from error
                if any(hole not in slots for hole in pattern.holes):
                    raise RegistrationError(f"{intent}: «{source}» usa huecos sin declarar")
                owner = self._keys.get(pattern.key) or keys.get(pattern.key)
                if owner is not None:
                    raise RegistrationError(
                        f"El patrón «{source}» de {intent} ya pertenece a {owner}"
                    )
                keys[pattern.key] = intent
                compiled.append(
                    _Registered(name, spec, pattern, len(self._patterns) + len(compiled))
                )
        self._patterns.extend(compiled)
        self._keys.update(keys)
        self._titles[name] = getattr(module, "title", name)
        for item in compiled:
            specs = self._specs.setdefault((name, item.spec.action), [])
            if item.spec not in specs:
                specs.append(item.spec)

    def register_catalog(self, name: str, *providers: Provider) -> None:
        """Lista para las entidades `CATALOG`. Con varias fuentes, gana la primera que tenga
        una coincidencia que supere el umbral. Se consultan al resolver."""
        if name in self._catalogs:
            raise RegistrationError(f"El catálogo «{name}» ya está registrado")
        self._catalogs[name] = tuple(providers)

    def specs(self) -> list[tuple[str, IntentSpec]]:
        """Todas las intenciones registradas, con su módulo, en orden de registro."""
        return [(module, spec) for (module, _), specs in self._specs.items() for spec in specs]

    def specs_of(self, module: str, action: str) -> tuple[IntentSpec, ...]:
        """Las intenciones registradas de una acción; vacío si no existe."""
        return tuple(self._specs.get((module, action), ()))

    def help(self) -> tuple[HelpGroup, ...]:
        """Órdenes disponibles con un ejemplo, agrupadas por módulo (RF-92)."""
        groups: dict[str, list[HelpEntry]] = {}
        for (module, _action), specs in self._specs.items():
            spec = next((spec for spec in specs if spec.description), None)
            if spec is not None:
                groups.setdefault(module, []).append(HelpEntry(spec.description, spec.example))
        ordered = [name for name in groups if name != CORE_MODULE]
        if CORE_MODULE in groups:
            ordered.append(CORE_MODULE)  # las órdenes del propio asistente, al final
        return tuple(HelpGroup(name, self._titles[name], tuple(groups[name])) for name in ordered)

    # --- Despacho ----------------------------------------------------------------------------

    def route(
        self, text: str, state: AssistantState, dialogue: object = None, *, resolve: bool = True
    ) -> Input | None:
        """Entrada para la FSM, o None si el texto se descarta sin efecto.

        Con `resolve=False`, una orden reconocida llega como `IntentMatched(Order)`: sus
        entidades se resuelven después, con `resolve`.
        """
        normalized = normalize(text, self._aliases)
        if state in _ATTENDING:
            entry = self._attending(normalized)
            if entry is not None:
                return entry
            if state is not AssistantState.LISTENING_COMMAND:
                # En espera, el texto es la respuesta: nunca una intención nueva.
                expected = getattr(dialogue, "expected_type", None)
                if not isinstance(expected, ExpectedType):
                    return answers.INVALID
                return answers.validate(
                    text, normalized, expected, self._settings.control_threshold,
                    now=self._now(), default_hour=self._settings.default_hour, tz=self._tz,
                )  # fmt: skip
            return self._classify(text, resolve) or NoMatch(text)
        if self._is_wake(normalized):
            return WakeWord()
        if state is AssistantState.IDLE:
            return self._resting(text, normalized, resolve)
        return None

    def _resting(self, text: str, normalized: str, resolve: bool = True) -> Input | None:
        """En reposo, cualquier texto despierta y se atiende como orden. El cierre exige su
        umbral de reposo; las frases de control sin sentido en reposo se descartan."""
        if fuzz.ratio(normalized, CLOSING_PHRASE) >= self._settings.idle_closing_threshold:
            return ClosingPhraseInIdle()
        if not normalized:
            return None
        control = self._attending(normalized)
        if isinstance(control, Control) and control.kind is not ControlKind.CERRAR:
            return None
        return self._classify(text, resolve) or NoMatch(text)

    def _is_wake(self, normalized: str) -> bool:
        return bool(normalized) and _best(normalized, WAKE_PHRASES) >= self._settings.wake_threshold

    def _attending(self, normalized: str) -> Input | None:
        """La frase de control o de activación más parecida a la frase completa, si alcanza
        su umbral. A igual parecido gana la frase de control."""
        if not normalized:
            return None
        score, kind = max(
            ((fuzz.ratio(normalized, phrase), kind) for phrase, kind in CONTROL_PHRASES),
            key=lambda scored: scored[0],
        )
        is_control = score >= self._settings.control_threshold
        wake = _best(normalized, WAKE_PHRASES)
        if wake >= self._settings.wake_threshold and not (is_control and score >= wake):
            return WakeWord()
        return Control(kind) if is_control else None

    # --- Clasificación -----------------------------------------------------------------------

    def _classify(self, text: str, resolve: bool = True) -> IntentMatched | None:
        """La intención del texto, con sus entidades, o None si ningún patrón coincide."""
        order = self.prepare(text)
        if order is None:
            return None
        return IntentMatched(self.resolve(order) if resolve else order)

    def prepare(self, text: str) -> Order | None:
        """Compara el texto con los patrones, sin resolver entidades. None si ninguno
        coincide."""
        tokens = tokenize(text, self._aliases)
        if not tokens.words:
            return None
        candidates = []
        for item in self._patterns:
            found = patterns.match(item.pattern, tokens.words, self._settings.intent_threshold)
            if found is not None:
                candidates.append((found, item))
        if not candidates:
            return None
        return Order(text.strip(), tokens, tuple(_ranked(candidates)))

    def resolve(self, order: Order) -> Intent:
        """La intención de la orden, con sus entidades resueltas en este momento. Si ninguna
        candidata se resuelve, la intención lleva el error de la primera."""
        tokens, description = order.tokens, order.text
        failed: Intent | None = None
        tried: set[tuple[str, str]] = set()  # acciones cuyas entidades no se han resuelto
        best = order.candidates[0][0].score
        for found, item in order.candidates:
            spec = item.spec
            if (
                failed is not None
                and item.module != failed.module
                and best - found.score >= SAME_SCORE_MARGIN
            ):
                # Otro módulo solo es alternativa si su texto fijo empata con lo escrito: uno
                # que solo se le parece haría otra cosa. «abre la carpeta fotos» no acaba en
                # «crea la carpeta fotos».
                continue
            if (item.module, spec.action) in tried:
                # Otro patrón de la misma acción leería la entidad que falta como parte de
                # otra: «crea el archivo notas en fotos» no crea «notas en fotos».
                continue
            try:
                params = {
                    hole: self._resolve(_slot(spec, hole), tokens, *found.spans[hole])
                    for hole in item.pattern.holes
                }
            except ParamError as unresolved:
                tried.add((item.module, spec.action))
                # Se prueba el siguiente candidato; si ninguno se resuelve, vale este error.
                failed = failed or Intent(
                    item.module, spec.action, error=unresolved.phrase,
                    description=description, panel=spec.panel,
                )  # fmt: skip
                continue
            return Intent(
                item.module, spec.action, {**params, **spec.fixed},
                description=description, panel=spec.panel,
            )  # fmt: skip
        assert failed is not None  # una orden tiene al menos una candidata
        return failed

    def resolve_params(
        self, module: str, action: str, raw: Mapping[str, object]
    ) -> Mapping[str, object]:
        """Resuelve los parámetros de una tarea de protocolo, que llegan como texto.

        Lanza `ParamError` si alguno no se puede resolver.
        """
        specs = self._specs.get((module, action))
        if not specs:
            raise KeyError(f"{module}.{action}")
        slots = {slot.name: slot for spec in specs for slot in spec.slots}
        params: dict[str, object] = dict(specs[0].fixed)
        for name, value in raw.items():
            slot = slots.get(name)
            if slot is None or not isinstance(value, str):
                params[name] = value
                continue
            tokens = tokenize(value, self._aliases)
            params[name] = self._resolve(slot, tokens, 0, len(tokens.words))
        return params

    def _resolve(self, slot: Slot, tokens: Tokens, start: int, end: int) -> object:
        original = tokens.original(start, end)
        spoken = " ".join(tokens.words[start:end])
        match slot.type:
            case SlotType.TEXT:
                return original.strip(_TEXT_EDGES)
            case SlotType.INTEGER:
                number = numbers.parse(spoken)
                if number is None:
                    raise ParamError(Phrase("entidad.numero"))
                return number
            case SlotType.DURATION:
                duration = durations.parse(spoken)
                if duration is None:
                    raise ParamError(Phrase("entidad.duracion"))
                return duration
            case SlotType.DATETIME:
                now = self._now()
                moment = datetimes.parse(
                    spoken.split(), now, self._settings.default_hour, self._tz
                )
                if moment is None:
                    raise ParamError(Phrase("entidad.fecha"))
                if moment <= now:
                    raise ParamError(Phrase("entidad.fecha_pasada"))
                return moment
            case SlotType.DIR_PATH:
                try:
                    return paths.resolve(
                        original, self._workdir.path, self._places,
                        home=self._workdir.home, threshold=self._settings.path_threshold,
                    )  # fmt: skip
                except paths.PathError as error:
                    phrase = f"ruta.{error.kind}"
                    raise ParamError(Phrase(phrase, {"nombre": error.name})) from None
            case SlotType.NEW_NAME | SlotType.NEW_PATH:
                build = names.build if slot.type is SlotType.NEW_NAME else names.build_path
                try:
                    return build(original.strip(_TEXT_EDGES))
                except names.InvalidNameError:
                    raise ParamError(Phrase("entidad.nombre")) from None
            case SlotType.CATALOG:
                for provider in self._catalogs[slot.catalog or ""]:
                    found = catalogs.best_match(
                        spoken, provider(), self._settings.catalog_threshold
                    )
                    if found is not None:
                        return found
                name = original.strip(_TEXT_EDGES)
                raise ParamError(Phrase("entidad.no_encontrado", {"nombre": name}))
            case SlotType.COMMAND_LINE:
                try:
                    return command_line.parse(tokens, start, end, self._binaries)
                except command_line.NotAllowedError:
                    raise ParamError(Phrase("comandos.no_permitido")) from None
        raise ParamError(Phrase("general.error"))


def _slot(spec: IntentSpec, name: str) -> Slot:
    return next(slot for slot in spec.slots if slot.name == name)


def _ranked(candidates: list) -> list:
    """Orden de elección: mayor puntuación; a igualdad (menos de 3 puntos), el patrón con
    más texto fijo; a igualdad, el orden de registro."""
    remaining = list(candidates)
    ordered = []
    while remaining:
        top = max(found.score for found, _ in remaining)
        tied = [c for c in remaining if top - c[0].score < SAME_SCORE_MARGIN]
        chosen = min(tied, key=lambda c: (-c[1].pattern.fixed_words, c[1].order))
        ordered.append(chosen)
        remaining.remove(chosen)
    return ordered
