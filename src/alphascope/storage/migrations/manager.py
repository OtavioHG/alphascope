from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from alphascope.core.logger import get_logger
from alphascope.storage.database import Base, storage_engine

logger = get_logger(__name__)


class MigrationManager:
    def __init__(self, migrations_dir: str | Path | None = None, alembic_ini: str | Path | None = None):
        self.project_root = Path(__file__).resolve().parents[4]
        self.migrations_dir = Path(migrations_dir or self.project_root / "alembic")
        self.alembic_ini = Path(alembic_ini or self.project_root / "alembic.ini")

    def _config(self) -> Config:
        config = Config(str(self.alembic_ini))
        config.set_main_option("script_location", str(self.migrations_dir))
        return config

    def upgrade(self, revision: str = "head") -> str:
        if self.alembic_ini.exists() and self.migrations_dir.exists():
            command.upgrade(self._config(), revision)
            logger.info("Alembic migrations applied", extra={"event": "alembic_upgrade", "revision": revision})
            return revision
        Base.metadata.create_all(bind=storage_engine)
        logger.warning("Alembic structure missing, falling back to create_all", extra={"event": "alembic_fallback"})
        return "fallback-create-all"

    def current(self) -> dict[str, str]:
        return {
            "status": "ready",
            "migrations_dir": str(self.migrations_dir),
            "alembic_ini": str(self.alembic_ini),
        }
