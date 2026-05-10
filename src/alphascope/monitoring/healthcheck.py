from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import inspect, text

from alphascope.config.settings import settings
from alphascope.infrastructure.redis_client import InMemoryRedisClient
from alphascope.storage.database import StorageSessionLocal, storage_engine


class HealthcheckService:
    def __init__(self, redis_client: InMemoryRedisClient | None = None):
        self.redis_client = redis_client or InMemoryRedisClient()

    def status(self) -> dict[str, object]:
        from alphascope.config.settings import settings as live_settings

        database_ok = True
        multi_agent_tables_ok = True
        session = StorageSessionLocal()
        try:
            session.execute(text("SELECT 1"))
            inspector = inspect(storage_engine)
            tables = set(inspector.get_table_names())
            expected_multi_agent = {"agent_decisions", "agent_debates", "trade_consensus", "trade_audit", "runtime_events", "model_outputs"}
            multi_agent_tables_ok = expected_multi_agent.issubset(tables)
        except Exception:
            database_ok = False
            multi_agent_tables_ok = False
        finally:
            session.close()

        redis_ok = True
        try:
            if hasattr(self.redis_client, "ping"):
                self.redis_client.ping()
            self.redis_client.set("healthcheck", "ok")
            redis_ok = self.redis_client.get("healthcheck") == "ok"
        except Exception:
            redis_ok = False

        runtime_dir = live_settings.data_dir / "runtime"
        multi_agent_runtime = self._read_json(runtime_dir / "multi_agent_runtime_status.json")
        multi_agent_heartbeat = self._read_json(runtime_dir / "multi_agent_heartbeat.json")
        scheduler = self._read_json(runtime_dir / "multi_agent_scheduler_status.json")
        models_ready = all(bool(config.get("active")) for config in live_settings.multi_agent_model_registry.values())
        multi_agent_ok = bool(multi_agent_runtime) and bool(multi_agent_heartbeat) and models_ready
        overall_ok = database_ok and redis_ok and multi_agent_tables_ok and multi_agent_ok
        return {
            "status": "ok" if overall_ok else "degraded",
            "database": database_ok,
            "redis": redis_ok,
            "multi_agent_tables": multi_agent_tables_ok,
            "multi_agent": {
                "runtime": multi_agent_runtime,
                "heartbeat": multi_agent_heartbeat,
                "scheduler": scheduler,
                "models_ready": models_ready,
                "healthy": multi_agent_ok,
            },
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
