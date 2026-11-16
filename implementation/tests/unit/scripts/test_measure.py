"""`scripts/measure.py` (T-7.1): lectura del registro y muestreo del proceso, sin hardware."""
import io
import logging

import pytest

import measure
from jarvis_assistant.process.logging_setup import LOG_FORMAT

MB = 1024 * 1024


def log_lines(*messages: str) -> list[str]:
    """Líneas con el formato real del registro."""
    formatter = logging.Formatter(LOG_FORMAT)
    lines = []
    for message in messages:
        record = logging.LogRecord("jarvis", logging.DEBUG, __file__, 1, message, None, None)
        record.threadName = "nucleo"
        lines.append(formatter.format(record))
    return lines


SESSION = log_lines(
    "Listo en 3.2 s",
    "Texto enviado: 100.000",
    "Inicio de la animación wake (pantalla): 100.120",
    "Inicio del audio de ciclo.apertura: 100.200",
    "Texto enviado: 110.000",
    "Inicio del audio de comandos.cd: 110.300",
    "Texto enviado: 120.000",  # sin respuesta hablada antes del siguiente texto
    "Texto enviado: 130.000",
    "Inicio del audio de general.no_entendido: 130.900",
    "Inicio de la animación sleep_rest (hud): 140.050",
    "Inicio del audio de ciclo.reposo: 140.000",
)


def test_lee_las_marcas_del_registro_en_orden():
    marks, startups = measure.parse_log(SESSION)
    assert startups == [3.2]
    assert [mark.kind for mark in marks][:3] == ["texto", "animacion", "audio"]
    assert marks[1].name == "wake" and marks[2].name == "ciclo.apertura"
    assert [mark.at for mark in marks] == sorted(mark.at for mark in marks)


def test_ignora_las_lineas_ajenas():
    marks, startups = measure.parse_log(log_lines("Frase reconocida: WakeWord", "Jarvis termina"))
    assert marks == [] and startups == []


def test_latencia_de_respuesta_del_texto_al_primer_audio():
    marks, _ = measure.parse_log(SESSION)
    assert measure.response_latencies(marks) == pytest.approx([0.2, 0.3, 0.9])


def test_latencia_de_la_animacion_de_despertar():
    marks, _ = measure.parse_log(SESSION)
    assert measure.wake_latencies(marks) == pytest.approx([0.12])


def test_sincronia_de_cada_animacion_con_el_audio_mas_cercano():
    marks, _ = measure.parse_log(SESSION)
    assert measure.sync_offsets(marks) == pytest.approx([0.08, 0.05])


def test_percentil_por_rango_mas_cercano():
    values = [float(n) for n in range(1, 21)]
    assert measure.percentile(values, 0.95) == 19.0
    assert measure.percentile([0.4], 0.95) == 0.4


def test_comprobaciones_del_registro():
    checks = measure.log_checks(SESSION)
    assert [check.requirement for check in checks] == [
        "RNF-03", "RNF-03", "RNF-03", "RNF-22", "RNF-25",
    ]  # fmt: skip
    median, p95, wake, sync, startup = checks
    assert median.value == pytest.approx(0.3) and median.passed
    assert p95.value == pytest.approx(0.9) and p95.passed
    assert wake.passed and sync.passed and startup.value == 3.2


def test_sin_datos_no_cumple_ni_incumple():
    checks = measure.log_checks([])
    assert all(check.value is None and check.passed is None for check in checks)
    assert measure.report(checks, io.StringIO()) == 0


def test_una_medida_que_supera_el_limite_hace_fallar_el_informe():
    slow = log_lines("Texto enviado: 1.000", "Inicio del audio de x: 2.500")
    out = io.StringIO()
    assert measure.report(measure.log_checks(slow), out) == 1
    assert "NO CUMPLE" in out.getvalue()


class FakeProcess:
    def __init__(self, cpu: list[float], rss: list[int], pid: int = 42, cmdline=()):
        self._cpu = [0.0, *cpu]
        self._rss = list(rss)
        self.pid = pid
        self._cmdline = list(cmdline)

    def cpu_percent(self, _interval):
        return self._cpu.pop(0)

    def memory_info(self):
        return type("Memory", (), {"rss": self._rss.pop(0)})()

    def cmdline(self):
        return self._cmdline


def test_muestreo_del_proceso_con_la_cpu_sobre_el_total_del_equipo():
    slept = []
    process = FakeProcess(cpu=[8.0, 4.0, 0.0], rss=[100 * MB, 120 * MB, 110 * MB])
    samples = measure.sample_process(process, 3, sleep=slept.append, cpu_count=4)
    assert slept == [1.0, 1.0, 1.0]
    assert [sample.cpu_percent for sample in samples] == [2.0, 1.0, 0.0]
    checks = measure.process_checks(samples, "dormido")
    assert [check.requirement for check in checks] == ["RNF-04", "RNF-04"]
    assert checks[0].value == pytest.approx(1.0) and checks[0].passed
    assert checks[1].value == pytest.approx(120.0) and checks[1].passed


def test_en_uso_solo_cuenta_la_ram_con_su_limite():
    samples = [measure.Sample(50.0, 700 * MB)]
    (check,) = measure.process_checks(samples, "uso")
    assert check.requirement == "RNF-05" and check.limit == 600 and check.passed is False


def test_encuentra_el_proceso_del_asistente():
    other = FakeProcess([], [], pid=1, cmdline=["python", "otro.py"])
    jarvis = FakeProcess([], [], pid=2, cmdline=["pythonw", "-I", "-m", "jarvis_assistant"])
    assert measure.find_assistant([other, jarvis]) is jarvis
    assert measure.find_assistant([other]) is None


def test_el_registro_se_lee_con_sus_archivos_rotados(tmp_path, capsys):
    (tmp_path / "jarvis.log.1").write_text(
        "\n".join(log_lines("Texto enviado: 1.000")), encoding="utf-8"
    )
    (tmp_path / "jarvis.log").write_text(
        "\n".join(log_lines("Inicio del audio de x: 1.200", "Listo en 2.0 s")), encoding="utf-8"
    )
    assert measure.main(["registro", str(tmp_path / "jarvis.log")]) == 0
    out = capsys.readouterr().out
    assert "0.200 s" in out and "RNF-25" in out


def test_sin_registro_sale_con_error(tmp_path):
    assert measure.main(["registro", str(tmp_path / "jarvis.log")]) == 1
