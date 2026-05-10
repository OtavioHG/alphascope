from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

from alphascope.monitoring.metrics import compute_trading_metrics
from alphascope.storage.repositories import StorageRepository


def configure_phase4_logging(log_dir: str | Path = "logs") -> None:
    base_dir = Path(log_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("alphascope.system")
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        handler = logging.FileHandler(base_dir / "system.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)


class SystemStatusService:
    def __init__(self, repository: StorageRepository | None = None):
        self.repository = repository or StorageRepository()

    def get_status(self) -> dict[str, Any]:
        ranking = self.repository.get_latest_ranking(interval="1h")
        snapshot = self.repository.get_latest_snapshot() or {}
        trades = self.repository.get_trade_history(limit=200)
        return {
            "portfolio": snapshot,
            "open_positions": self.repository.get_open_positions().to_dict(orient="records"),
            "trading_metrics": compute_trading_metrics(trades),
            "latest_ranking": ranking.head(5).to_dict(orient="records") if not ranking.empty else [],
            "scheduler": {},
            "pipeline": {},
            "system_metrics": self._system_metrics(),
        }

    def _system_metrics(self) -> dict[str, Any]:
        if psutil is None:
            return {"cpu_percent": None, "memory_percent": None, "memory_used_gb": None, "process_id": os.getpid()}
        memory = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "process_id": os.getpid(),
        }
