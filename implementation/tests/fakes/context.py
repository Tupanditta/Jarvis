"""Contexto de acción para probar un módulo sin orquestador: registra lo que el módulo hace."""
import asyncio
from pathlib import Path

from fakes.clock import FakeClock
from fakes.platform import FakePlatform
from jarvis_assistant.config import Config
from jarvis_assistant.core.action_api import ActionContext, ActionResult, Phrase
from jarvis_assistant.core.database import Database
from jarvis_assistant.core.events import Event
from jarvis_assistant.core.notices import Notice
from jarvis_assistant.core.workdir import Workdir


class ContextRig:
    """`ctx` es el contexto; lo ocurrido queda en `events`, `said`, `notices` y `jobs`."""

    def __init__(self, root: Path, *, config: Config | None = None, origin: str = "voz") -> None:
        self.platform = FakePlatform(root)
        self.places = dict(self.platform.default_places())
        self.home = root / "usuario"  # aparte de los lugares con nombre del doble
        self.home.mkdir(parents=True, exist_ok=True)
        self.clock = FakeClock()
        self.database = Database(":memory:")
        self.database.migrate()
        self.workdir = Workdir(self.home)
        self.events: list[Event] = []
        self.said: list[Phrase] = []
        self.notices: list[Notice] = []
        self.jobs: list[asyncio.Task] = []
        self.ctx = ActionContext(
            session=None,
            origin=origin,  # type: ignore[arg-type]
            workdir=self.workdir,
            clock=self.clock,
            config=config or Config(),
            db=self.database,
            platform=self.platform,
            places=self.places,
            say=self._say,
            publish=self.events.append,
            notify=self.notices.append,
            background=lambda work: self.jobs.append(asyncio.ensure_future(work)),
            task_id=7,
        )

    async def _say(self, phrase: Phrase) -> None:
        self.said.append(phrase)

    def of(self, kind: type) -> list:
        return [event for event in self.events if isinstance(event, kind)]

    def last(self, kind: type):
        return self.of(kind)[-1]

    async def job(self) -> ActionResult:
        """Resultado del trabajo en segundo plano que dejó la última acción."""
        return await self.jobs[-1]

    def close(self) -> None:
        for job in self.jobs:
            job.cancel()
        self.database.close()


async def settle() -> None:
    for _ in range(30):
        await asyncio.sleep(0)
