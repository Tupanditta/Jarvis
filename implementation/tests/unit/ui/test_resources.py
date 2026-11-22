"""Medidor de recursos: el modelo mide el consumo del asistente solo mientras alguien mira."""
import psutil

from jarvis_assistant.ui.resources import ProcessUsage, ResourcesModel, Usage, _size

MB = 2**20
GB = 2**30


class FakeSample:
    def __init__(self, *usages: Usage) -> None:
        self.usages = list(usages)
        self.calls = 0

    def __call__(self) -> Usage:
        self.calls += 1
        return self.usages[min(self.calls, len(self.usages)) - 1]


def test_sin_vistas_no_mide_nada(qtbot):
    sample = FakeSample(Usage(5.0, 2.0, 300 * MB, 16 * GB))
    model = ResourcesModel(sample)
    assert sample.calls == 0 and not model.watching
    assert model.cpu == 0.0 and model.ram == 0.0


def test_al_mirar_mide_ya_y_expone_los_porcentajes_y_los_tamanos(qtbot):
    model = ResourcesModel(FakeSample(Usage(12.5, 1.8, 300 * MB, 16 * GB)))
    model.watch()
    assert model.watching
    assert model.cpu == 12.5 and model.ram == 1.8
    assert model.ramText == "300 MB" and model.totalText == "16.0 GB"
    assert model.cores >= 1


def test_refresca_en_cada_intervalo_y_para_cuando_nadie_mira(qtbot):
    sample = FakeSample(Usage(1.0, 1.0, MB, GB), Usage(40.0, 2.0, 2 * MB, GB))
    model = ResourcesModel(sample, interval_ms=20)
    with qtbot.waitSignal(model.changed):
        model.watch()
    qtbot.waitUntil(lambda: model.cpu == 40.0, timeout=1000)
    model.watch()  # dos vistas: la pantalla y otra
    model.unwatch()
    assert model.watching
    model.unwatch()
    assert not model.watching
    model.unwatch()  # de más: no pasa nada
    assert not model.watching


def test_un_fallo_al_medir_conserva_la_ultima_medida(qtbot):
    def failing() -> Usage:
        raise psutil.AccessDenied()

    model = ResourcesModel(failing)
    model.watch()
    assert model.cpu == 0.0 and model.ramText == "0 MB"


def test_se_ve_abajo_a_la_derecha_y_su_boton_lo_oculta_y_lo_muestra(qtbot):
    model = ResourcesModel(FakeSample(Usage(1.0, 1.0, MB, GB)))
    assert model.shown and model.corner == "right"
    with qtbot.waitSignal(model.shownChanged):
        model.toggle()
    assert not model.shown
    model.toggle()
    assert model.shown


def test_el_triple_clic_alterna_entre_las_dos_esquinas_inferiores(qtbot):
    model = ResourcesModel(FakeSample(Usage(1.0, 1.0, MB, GB)))
    with qtbot.waitSignal(model.cornerChanged):
        model.switchCorner()
    assert model.corner == "left"
    model.switchCorner()
    assert model.corner == "right"


def test_los_tamanos_se_escriben_en_mb_o_gb():
    assert _size(250 * MB) == "250 MB"
    assert _size(1536 * MB) == "1.5 GB"


def test_mide_el_propio_proceso_en_porcentajes_validos():
    usage = ProcessUsage()()
    assert 0.0 <= usage.cpu <= 100.0
    assert 0.0 < usage.ram < 100.0
    assert 0 < usage.ram_bytes < usage.total_bytes
