"""Apartado Sonido: activa o desactiva el sonido del asistente (`sound.enabled`)."""
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from jarvis_assistant.config import Config, SoundSettings
from jarvis_assistant.config.settings import dump_sound
from jarvis_assistant.configurator.sections.base import Section


class SoundSection(Section):
    changed = Signal()

    files = ("settings.toml",)

    def __init__(self) -> None:
        super().__init__()
        self._enabled = True

    def load(self, config: Config) -> None:
        self._enabled = config.settings.sound.enabled
        self.changed.emit()

    def dump(self, documents: Mapping[str, Any]) -> None:
        dump_sound(documents["settings.toml"], SoundSettings(enabled=self._enabled))

    @Property(bool, notify=changed)
    def enabled(self) -> bool:
        return self._enabled

    @Slot(bool)
    def setEnabled(self, enabled: bool) -> None:
        if enabled != self._enabled:
            self._enabled = enabled
            self.changed.emit()
            self.touch()
