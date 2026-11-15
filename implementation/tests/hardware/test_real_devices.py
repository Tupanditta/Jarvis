r"""Altavoz real (marcador `hardware`; a demanda).

    .\.venv\Scripts\python.exe -m pytest -m hardware tests\hardware
"""
import asyncio

import numpy as np
import pytest

from jarvis_assistant.core.clock import SystemClock
from jarvis_assistant.speaker.player import Player

pytestmark = pytest.mark.hardware


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
