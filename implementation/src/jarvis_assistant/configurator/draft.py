"""Borrador de la configuración: carga, cambios pendientes, validación y guardado.

Los apartados editan en memoria. `save` valida todos; si alguno tiene problemas no escribe
nada. Si no, vuelca los apartados con cambios en sus documentos TOML, comprueba cada
documento con las mismas reglas que usa el asistente al cargar y los escribe. Sin QML: se
prueba solo.
"""
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from jarvis_assistant import config as config_module
from jarvis_assistant.config.writer import WriteError, read_document, write_documents
from jarvis_assistant.configurator.sections.base import Section

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SaveResult:
    saved: bool
    problems: list[str] = field(default_factory=list)


class Draft:
    def __init__(self, config_dir: Path, sections: Mapping[str, Section]) -> None:
        self._config_dir = config_dir
        self._sections = dict(sections)

    @property
    def dirty(self) -> bool:
        return any(section.dirty for section in self._sections.values())

    def open(self) -> None:
        """Carga la configuración guardada en todos los apartados, sin cambios pendientes.

        Un apartado cuyo archivo tiene errores queda bloqueado: guardar sobre él borraría lo
        que el asistente no ha podido leer."""
        config, errors = config_module.load(self._config_dir)
        broken = {error.file: error for error in errors if not error.warning}
        for section in self._sections.values():
            problem = next((broken[name] for name in section.files if name in broken), None)
            locked = ""
            if problem is not None:
                where = f", clave {problem.key}" if problem.key else ""
                locked = (
                    f"El archivo {problem.file} tiene un error{where}: {problem.reason}. "
                    "Corríjalo a mano para poder editar este apartado."
                )
            section.reset(config, locked)

    def save(self) -> SaveResult:
        problems = [problem for s in self._sections.values() for problem in s.validate()]
        if problems:
            return SaveResult(False, problems)
        changed = [section for section in self._sections.values() if section.dirty]
        if not changed:
            return SaveResult(True)
        names = sorted({name for section in changed for name in section.files})
        try:
            documents = {name: read_document(self._config_dir, name) for name in names}
        except WriteError as error:
            return SaveResult(False, [f"No se puede leer {error.file}: {error.reason}"])
        for section in changed:
            section.dump(documents)
        for name, document in documents.items():
            for error in config_module.check(name, document.unwrap()):
                if not error.warning:
                    problems.append(f"{name}, {error.key}: {error.reason}")
        if problems:
            return SaveResult(False, problems)
        try:
            write_documents(self._config_dir, documents)
        except WriteError as error:
            logger.error("No se ha podido guardar %s: %s", error.file, error.reason)
            return SaveResult(False, [f"No se ha podido guardar {error.file}: {error.reason}"])
        logger.info("Configuración guardada: %s", ", ".join(names))
        self.open()
        return SaveResult(True)
