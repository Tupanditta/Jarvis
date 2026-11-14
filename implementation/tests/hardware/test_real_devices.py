r"""Micrófono y altavoz reales (marcador `hardware`; a demanda).

    .\.venv\Scripts\python.exe -m pytest -m hardware tests\hardware
"""
import asyncio

import numpy as np
import pytest

from jarvis_assistant.audio_capture.microphone import Microphone
from jarvis_assistant.config import AudioSettings
from jarvis_assistant.core.clock import SystemClock
from jarvis_assistant.speaker.player import Player

pytestmark = pytest.mark.hardware


def test_el_microfono_real_entrega_bloques_de_80_ms():
    microphone = Microphone(AudioSettings())
    microphone.open()
    try:
        blocks = [microphone.read(1.0) for _ in range(10)]
    finally:
        microphone.close()
    assert all(block is not None and block.shape == (1280,) for block in blocks)
    assert all(block.dtype == np.int16 for block in blocks)


async def test_el_altavoz_real_reproduce_y_avisa_al_empezar():
    player = Player(SystemClock())
    player.open(22050)
    assert player.is_open
    started = []
    tone = (2000 * np.sin(2 * np.pi * 440 * np.arange(11025) / 22050)).astype(np.int16)
    try:
        completed = await asyncio.wait_for(player.play(tone, lambda: started.append(True)), 5)
    finally:
        player.close()
    assert completed and started == [True]
