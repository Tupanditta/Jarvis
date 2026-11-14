"""SQLite: conexión única del núcleo, migraciones y conversión de fechas (persistencia.md).

- Una sola conexión, creada y usada en el hilo del núcleo.
- Migraciones `NNNN_nombre.sql` aplicadas en orden según `PRAGMA user_version`.
- Fechas como texto ISO-8601 en UTC con desplazamiento explícito (RES-35).
- Borrado lógico: el código no contiene sentencias de borrado físico (RES-34).
"""
import logging
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
_PRAGMAS = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA busy_timeout = 2000",
)


def to_db(moment: datetime) -> str:
    """Fecha → texto de la base de datos, en UTC. Rechaza fechas sin zona horaria."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("La fecha no tiene zona horaria")
    return moment.astimezone(UTC).isoformat()


def from_db(text: str) -> datetime:
    """Texto de la base de datos → fecha en UTC."""
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError(f"Fecha sin zona horaria en la base de datos: {text!r}")
    return moment.astimezone(UTC)


class Database:
    """Conexión a `jarvis.db` (o a una base en memoria, para las pruebas)."""

    def __init__(
        self,
        path: Path | Literal[":memory:"],
        *,
        migrations_dir: Path = MIGRATIONS_DIR,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._path = None if str(path) == ":memory:" else Path(path)
        self._migrations_dir = migrations_dir
        self._now = now
        self._depth = 0
        self._conn: sqlite3.Connection | None = self._open()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("La base de datos está cerrada")
        return self._conn

    @property
    def schema_version(self) -> int:
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def close(self) -> None:
        """Cierra la conexión. Idempotente."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Transacción que admite anidarse: solo la más externa confirma o deshace.

        Los repositorios envuelven así cada operación; quien necesite varias operaciones en
        una sola transacción las agrupa con otro `with db.transaction():`.
        """
        conn = self.conn
        self._depth += 1
        try:
            yield conn
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                conn.rollback()
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                conn.commit()

    def migrate(self) -> None:
        """Aplica las migraciones pendientes, cada una en su transacción."""
        migrations = self._migrations()
        current = self.schema_version
        if current > len(migrations):
            raise RuntimeError(
                f"La base de datos (versión {current}) es más reciente que el código "
                f"(versión {len(migrations)})"
            )
        pending = migrations[current:]
        if not pending:
            return
        if current > 0:
            self._backup()
        for version, path in pending:
            script = path.read_text(encoding="utf-8")
            try:
                self.conn.executescript(
                    f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;"
                )
            except sqlite3.Error:
                if self.conn.in_transaction:
                    self.conn.rollback()
                logger.exception("La migración %s ha fallado", path.name)
                raise
            logger.info("Migración %s aplicada", path.name)

    # --- Internos ---

    def _open(self) -> sqlite3.Connection:
        if self._path is None:
            return self._connect(":memory:")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return self._connect(str(self._path))
        except sqlite3.OperationalError:
            raise  # bloqueada o inaccesible: no es una base dañada
        except sqlite3.DatabaseError as error:
            self._set_aside(error)
            return self._connect(str(self._path))

    @staticmethod
    def _connect(target: str) -> sqlite3.Connection:
        conn = sqlite3.connect(target)
        try:
            conn.row_factory = sqlite3.Row
            for pragma in _PRAGMAS:
                conn.execute(pragma)
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except BaseException:
            conn.close()
            raise
        return conn

    def _set_aside(self, error: Exception) -> None:
        """Renombra la base dañada a `jarvis.db.corrupt-<fecha>` para crear una nueva."""
        assert self._path is not None
        stamp = self._now().strftime("%Y%m%d-%H%M%S")
        target = self._path.with_name(f"{self._path.name}.corrupt-{stamp}")
        self._path.replace(target)
        for suffix in ("-wal", "-shm"):
            self._path.with_name(self._path.name + suffix).unlink(missing_ok=True)
        logger.error(
            "La base de datos está dañada (%s). Se conserva en %s y se crea una nueva.",
            error,
            target.name,
        )

    def _backup(self) -> None:
        """Copia la base a `jarvis.db.bak` antes de cambiar el esquema."""
        if self._path is None:
            return
        target = self._path.with_name(self._path.name + ".bak")
        target.unlink(missing_ok=True)
        with closing(sqlite3.connect(target)) as copy:
            self.conn.backup(copy)
        logger.info("Copia de seguridad en %s", target.name)

    def _migrations(self) -> list[tuple[int, Path]]:
        migrations = []
        for path in sorted(self._migrations_dir.glob("*.sql")):
            match = _MIGRATION_NAME.match(path.name)
            if match is None:
                raise ValueError(f"Nombre de migración no válido: {path.name}")
            migrations.append((int(match.group(1)), path))
        for expected, (version, path) in enumerate(migrations, start=1):
            if version != expected:
                raise ValueError(f"Migración fuera de secuencia: {path.name}")
        return migrations
