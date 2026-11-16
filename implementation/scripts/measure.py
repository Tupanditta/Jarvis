"""Mide los RNF de rendimiento del asistente en marcha (T-7.1; proceso.md, «Herramientas»).

Dos fuentes, sin tocar el asistente:

- **El proceso:** CPU y RAM muestreadas con `psutil` durante un periodo (RNF-04, RNF-05).
- **El registro de diagnóstico**, escrito con `--log-level DEBUG`: marcas de tiempo del envío
  de cada texto, del inicio de cada audio y de cada animación (RNF-03, RNF-22) y el tiempo de
  arranque (RNF-25). Todas las marcas usan el mismo reloj monótono, así que se comparan entre
  hilos.

Uso, desde ``implementation/``::

    python scripts/measure.py proceso --estado dormido [--segundos 60] [--pid N]
    python scripts/measure.py registro [ruta de jarvis.log]

Sale con 0 si todo lo medido cumple y con 1 si algo no cumple.
"""
import argparse
import os
import re
import statistics
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

MB = 1024 * 1024

# Límites de software/Requisitos/no-funcionales.md.
CPU_LIMIT_PERCENT = 2.0  # RNF-04: media en dormido y en reposo, sobre el total del equipo
RAM_LIMITS_MB = {"dormido": 400, "reposo": 400, "uso": 600}  # RNF-04 y RNF-05
LATENCY_MEDIAN_S = 0.5  # RNF-03
LATENCY_P95_S = 1.0  # RNF-03
WAKE_ANIMATION_S = 0.5  # RNF-03: de «Hey Jarvis» al inicio de la animación
SYNC_LIMIT_S = 0.150  # RNF-22
STARTUP_LIMIT_S = 10.0  # RNF-25
WAKE_ANIMATIONS = frozenset({"wake", "wake_from_rest"})

# Mensajes del registro (view_models.py, speaker.py, ui/app.py, main.py).
_SENT = re.compile(r"Texto enviado: (?P<t>\d+(?:\.\d+)?)")
_AUDIO = re.compile(r"Inicio del audio de (?P<id>\S+): (?P<t>\d+(?:\.\d+)?)")
_ANIMATION = re.compile(
    r"Inicio de la animación (?P<name>\S+) \((?P<surface>[^)]*)\): (?P<t>\d+(?:\.\d+)?)"
)
_READY = re.compile(r"Listo en (?P<s>\d+(?:\.\d+)?) s")


@dataclass(frozen=True)
class Mark:
    kind: str  # "texto", "audio" o "animacion"
    at: float  # segundos del reloj monótono del proceso
    name: str = ""


@dataclass(frozen=True)
class Check:
    """Una medida comparada con su límite."""

    requirement: str
    description: str
    value: float | None  # None: no hay datos para medirlo
    limit: float
    unit: str

    @property
    def passed(self) -> bool | None:
        return None if self.value is None else self.value <= self.limit

    def line(self) -> str:
        verdict = {True: "cumple", False: "NO CUMPLE", None: "sin datos"}[self.passed]
        value = "-" if self.value is None else f"{self.value:.3f} {self.unit}"
        limit = f"<= {self.limit:g} {self.unit}"
        return f"{self.requirement:7} {self.description:46} {value:>14}  {limit:10} {verdict}"


# --- Registro --------------------------------------------------------------------------------


def parse_log(lines: Iterable[str]) -> tuple[list[Mark], list[float]]:
    """Marcas de tiempo en orden y tiempos de arranque («Listo en ... s») del registro."""
    marks: list[Mark] = []
    startups: list[float] = []
    for line in lines:
        if match := _SENT.search(line):
            marks.append(Mark("texto", float(match["t"])))
        elif match := _AUDIO.search(line):
            marks.append(Mark("audio", float(match["t"]), match["id"]))
        elif match := _ANIMATION.search(line):
            marks.append(Mark("animacion", float(match["t"]), match["name"]))
        elif match := _READY.search(line):
            startups.append(float(match["s"]))
    marks.sort(key=lambda mark: mark.at)
    return marks, startups


def response_latencies(marks: Sequence[Mark]) -> list[float]:
    """De cada texto enviado al primer audio que empieza después, antes del siguiente texto.

    Un texto sin respuesta hablada antes del siguiente envío no cuenta.
    """
    latencies = []
    for index, mark in enumerate(marks):
        if mark.kind != "texto":
            continue
        for later in marks[index + 1:]:
            if later.kind == "texto":
                break
            if later.kind == "audio":
                latencies.append(later.at - mark.at)
                break
    return latencies


def wake_latencies(marks: Sequence[Mark]) -> list[float]:
    """De cada texto al inicio de la animación de despertar que provoca (la primera de una
    superficie, antes del siguiente texto)."""
    latencies = []
    for index, mark in enumerate(marks):
        if mark.kind != "texto":
            continue
        for later in marks[index + 1:]:
            if later.kind == "texto":
                break
            if later.kind == "animacion" and later.name in WAKE_ANIMATIONS:
                latencies.append(later.at - mark.at)
                break
    return latencies


def sync_offsets(marks: Sequence[Mark]) -> list[float]:
    """Para cada animación, la distancia al inicio de audio más cercano (RNF-22)."""
    audios = [mark.at for mark in marks if mark.kind == "audio"]
    if not audios:
        return []
    return [
        min(abs(mark.at - audio) for audio in audios)
        for mark in marks if mark.kind == "animacion"
    ]  # fmt: skip


def percentile(values: Sequence[float], fraction: float) -> float:
    """Percentil por el método del rango más cercano: un valor que existe en la muestra."""
    ordered = sorted(values)
    rank = max(1, round(fraction * len(ordered) + 0.4999))
    return ordered[min(rank, len(ordered)) - 1]


def log_checks(lines: Iterable[str]) -> list[Check]:
    marks, startups = parse_log(lines)
    responses = response_latencies(marks)
    wakes = wake_latencies(marks)
    offsets = sync_offsets(marks)
    return [
        Check("RNF-03", f"Respuesta, mediana ({len(responses)} órdenes)",
              statistics.median(responses) if responses else None, LATENCY_MEDIAN_S, "s"),
        Check("RNF-03", "Respuesta, percentil 95",
              percentile(responses, 0.95) if responses else None, LATENCY_P95_S, "s"),
        Check("RNF-03", f"Activación -> animación, máximo ({len(wakes)})",
              max(wakes) if wakes else None, WAKE_ANIMATION_S, "s"),
        Check("RNF-22", f"Animación <-> frase, máximo ({len(offsets)})",
              max(offsets) if offsets else None, SYNC_LIMIT_S, "s"),
        Check("RNF-25", "Arranque hasta listo, último",
              startups[-1] if startups else None, STARTUP_LIMIT_S, "s"),
    ]  # fmt: skip


# --- Proceso ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Sample:
    cpu_percent: float  # sobre el total del equipo: 100 % es todos los núcleos ocupados
    rss_bytes: int


def sample_process(
    process: object, seconds: float, interval: float = 1.0,
    sleep: Callable[[float], None] = time.sleep, cpu_count: int | None = None,
) -> list[Sample]:
    """Muestrea `process` (un `psutil.Process`) cada `interval` segundos durante `seconds`.

    `psutil` da la CPU de un proceso sobre un núcleo; se divide entre los núcleos lógicos
    para tenerla sobre el total, como pide RNF-04.
    """
    cores = cpu_count or os.cpu_count() or 1
    process.cpu_percent(None)  # type: ignore[attr-defined]  # la primera lectura es 0
    samples = []
    for _ in range(max(1, round(seconds / interval))):
        sleep(interval)
        cpu = process.cpu_percent(None) / cores  # type: ignore[attr-defined]
        rss = process.memory_info().rss  # type: ignore[attr-defined]
        samples.append(Sample(cpu, rss))
    return samples


def process_checks(samples: Sequence[Sample], state: str) -> list[Check]:
    cpu = statistics.fmean(sample.cpu_percent for sample in samples) if samples else None
    ram = max(sample.rss_bytes for sample in samples) / MB if samples else None
    checks = []
    if state in ("dormido", "reposo"):
        checks.append(Check("RNF-04", f"CPU media en {state}", cpu, CPU_LIMIT_PERCENT, "%"))
    requirement = "RNF-05" if state == "uso" else "RNF-04"
    checks.append(Check(requirement, f"RAM máxima en {state}", ram, RAM_LIMITS_MB[state], "MB"))
    return checks


def find_assistant(processes: Iterable[object]) -> object | None:
    """El proceso de Python que ejecuta `jarvis_assistant` (no este guion)."""
    own = os.getpid()
    for process in processes:
        try:
            cmdline = process.cmdline()  # type: ignore[attr-defined]
            if process.pid != own and "jarvis_assistant" in cmdline:  # type: ignore[attr-defined]
                return process
        except Exception:  # proceso que termina o sin permiso: se ignora
            continue
    return None


# --- Línea de órdenes ------------------------------------------------------------------------


def default_log_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Jarvis" / "logs" / "jarvis.log"


def rotated_logs(path: Path) -> list[Path]:
    """`jarvis.log.1`, `jarvis.log.2`...: los archivos anteriores que deja la rotación."""
    return [
        file for file in path.parent.glob(path.name + ".*") if file.suffix[1:].isdigit()
    ]  # fmt: skip


def report(checks: Sequence[Check], out: TextIO | None = None) -> int:
    for check in checks:
        print(check.line(), file=out or sys.stdout)
    return 1 if any(check.passed is False for check in checks) else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="measure", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    proc = commands.add_parser("proceso", help="CPU y RAM del asistente en marcha")
    proc.add_argument("--estado", choices=sorted(RAM_LIMITS_MB), required=True)
    proc.add_argument("--segundos", type=float, default=60.0)
    proc.add_argument("--pid", type=int)
    log = commands.add_parser("registro", help="latencias, sincronía y arranque del registro")
    log.add_argument("ruta", nargs="?", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "registro":
        path = args.ruta or default_log_path()
        # El registro rota: se leen también los archivos anteriores, del más antiguo al último.
        files = [*sorted(rotated_logs(path), key=lambda file: -int(file.suffix[1:])), path]
        lines = [
            line for file in files if file.is_file()
            for line in file.read_text(encoding="utf-8", errors="replace").splitlines()
        ]  # fmt: skip
        if not lines:
            print(f"No hay registro en {path}", file=sys.stderr)
            return 1
        return report(log_checks(lines))

    import psutil

    process = psutil.Process(args.pid) if args.pid else find_assistant(psutil.process_iter())
    if process is None:
        print("El asistente no está en marcha", file=sys.stderr)
        return 1
    print(f"Midiendo el proceso {process.pid} durante {args.segundos:g} s...")
    return report(process_checks(sample_process(process, args.segundos), args.estado))


if __name__ == "__main__":
    sys.exit(main())
