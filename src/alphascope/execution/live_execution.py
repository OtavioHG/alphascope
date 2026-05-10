from __future__ import annotations

from typing import Any

from alphascope.execution.exchange_adapter import ExchangeAdapter
from alphascope.execution.order_manager import OrderManager


class LiveExecutionService:
    def __init__(self, adapter: ExchangeAdapter | None = None, order_manager: OrderManager | None = None):
        self.adapter = adapter or ExchangeAdapter()
        self.order_manager = order_manager or OrderManager(self.adapter.client)

    def execute_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        action = signal.get("action", "").lower()
        if action not in {"buy", "sell"}:
            return {"status": "ignored", "reason": "unsupported_action"}
        return self.order_manager.place_order(
            symbol=signal["symbol"],
            side=action,
            quantity=float(signal["quantity"]),
            order_type=signal.get("order_type", "market"),
            price=signal.get("price"),
        )
