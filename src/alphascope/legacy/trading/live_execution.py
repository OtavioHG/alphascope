from __future__ import annotations

from alphascope.config.settings import settings


class LiveExecutionClient:
    def __init__(self) -> None:
        self.enabled = settings.ENABLE_LIVE_TRADING

    def place_order(self, *args, **kwargs):
        if not self.enabled:
            raise RuntimeError("Live trading is disabled. Keep ENABLE_LIVE_TRADING=False for Phase 4.")
        raise NotImplementedError("Live execution via CCXT is prepared but not implemented in Phase 4.")
