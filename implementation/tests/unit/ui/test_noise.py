"""Medidor de ruido: el modelo solo abre el micrófono mientras alguien mira."""
import numpy as np
import pytest

from jarvis_assistant.ui.noise import CALIBRATION_DB, MAX_DB, NoiseModel, to_db


class FakeStream:
    def __init__(self) -> None:
        self.closed = False

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class FakeMicrophone:
    """Abre flujos falsos; `feed` hace de hilo de audio."""

    def __init__(self) -> None:
        self.opened = 0
        self.stream: FakeStream | None = None
        self.on_block = None

    def __call__(self, on_block) -> FakeStream:
        self.opened += 1
        self.on_block = on_block
        self.stream = FakeStream()
        return self.stream

    def feed(self, amplitude: float, frames: int = 480) -> None:
        self.on_block(np.full(frames, amplitude, dtype=np.float32))


def test_sin_vistas_no_abre_el_microfono_y_empieza_oculto(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    assert mic.opened == 0 and not model.watching
    assert not model.shown and model.corner == "right"
    assert model.level == 0.0


def test_al_mirar_abre_el_microfono_y_al_dejar_de_mirar_lo_suelta(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    model.watch()
    model.watch()  # dos vistas: un solo micrófono
    assert mic.opened == 1 and model.watching
    model.unwatch()
    assert model.watching and not mic.stream.closed
    model.unwatch()
    assert not model.watching and mic.stream.closed
    model.unwatch()  # de más: no pasa nada
    assert not model.watching


def test_cada_intervalo_pasa_la_energia_media_a_decibelios(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic, interval_ms=20)
    model.watch()
    mic.feed(0.01)  # -40 dBFS
    mic.feed(0.01)
    with qtbot.waitSignal(model.changed, timeout=1000):
        pass
    assert model.level == pytest.approx(CALIBRATION_DB - 40, abs=0.1)
    assert model.focusText == "CONCENTRACIÓN MEDIA"


def test_sin_audio_nuevo_conserva_la_ultima_medida(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    model.watch()
    mic.feed(0.001)  # -60 dBFS
    model.refresh()
    level = model.level
    model.refresh()
    assert model.level == level
    assert model.focusText == "CONCENTRACIÓN ALTA"


def test_ruido_alto_baja_la_concentracion(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    model.watch()
    mic.feed(0.1)  # -20 dBFS
    model.refresh()
    assert model.focusText == "CONCENTRACIÓN BAJA"


def test_los_picos_breves_no_suben_el_ruido_de_fondo(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)  # 300 ms por medida: 100 medidas en la ventana de 30 s
    model.watch()
    for _ in range(93):  # 28 s de silencio
        mic.feed(0.001)  # -60 dBFS
        model.refresh()
    quiet = model.level
    for _ in range(7):  # 2 s de golpes fuertes
        mic.feed(1.0)  # 0 dBFS
        model.refresh()
    assert model.level == quiet == pytest.approx(CALIBRATION_DB - 60, abs=0.1)


def test_un_ruido_que_dura_mas_de_media_ventana_si_cuenta(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    model.watch()
    for _ in range(40):
        mic.feed(0.001)
        model.refresh()
    for _ in range(60):
        mic.feed(0.1)  # -20 dBFS
        model.refresh()
    assert model.level == pytest.approx(CALIBRATION_DB - 20, abs=0.1)


def test_las_medidas_de_mas_de_30_segundos_salen_de_la_ventana(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    model.watch()
    for _ in range(100):
        mic.feed(0.1)
        model.refresh()
    for _ in range(100):  # 30 s de silencio: el ruido anterior ya no cuenta
        mic.feed(0.001)
        model.refresh()
    assert model.level == pytest.approx(CALIBRATION_DB - 60, abs=0.1)


def test_al_volver_a_mirar_empieza_una_ventana_nueva(qtbot):
    mic = FakeMicrophone()
    model = NoiseModel(mic)
    model.watch()
    for _ in range(10):
        mic.feed(0.1)
        model.refresh()
    model.unwatch()
    model.watch()
    mic.feed(0.001)
    model.refresh()
    assert model.level == pytest.approx(CALIBRATION_DB - 60, abs=0.1)


def test_sin_microfono_lo_dice_y_no_falla(qtbot):
    def missing(on_block):
        raise OSError("No Default Input Device Available")

    model = NoiseModel(missing)
    model.watch()
    assert not model.available and model.level == 0.0
    assert model.focusText == "SIN MICRÓFONO"
    model.unwatch()


def test_su_boton_lo_muestra_y_el_triple_clic_alterna_las_esquinas(qtbot):
    model = NoiseModel(FakeMicrophone())
    with qtbot.waitSignal(model.shownChanged):
        model.toggle()
    assert model.shown
    with qtbot.waitSignal(model.cornerChanged):
        model.switchCorner()
    assert model.corner == "left"
    model.switchCorner()
    assert model.corner == "right"


def test_los_decibelios_van_de_cero_al_maximo():
    assert to_db(0.0) == 0.0
    assert to_db(1.0) == pytest.approx(CALIBRATION_DB)
    assert to_db(1e-9) == 0.0
    assert to_db(1e6) == MAX_DB
