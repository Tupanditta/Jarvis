"""Nivel de la voz del asistente para la interfaz (RF-83)."""
import numpy as np

from jarvis_assistant.speaker.level import dbfs, level_of


def test_dbfs_va_del_silencio_digital_al_fondo_de_escala():
    assert dbfs(0) == -120.0
    assert dbfs(32767) == 0.0


def test_el_nivel_esta_entre_0_y_1():
    assert level_of(np.zeros(1280, dtype=np.int16)) == 0.0
    assert level_of(np.full(1280, 32767, dtype=np.int16)) == 1.0
    assert 0 < level_of(np.full(1280, 1000, dtype=np.int16)) < 1
    assert level_of(np.zeros(0, dtype=np.int16)) == 0.0
