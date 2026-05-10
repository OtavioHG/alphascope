from __future__ import annotations

from alphascope.config.settings import settings
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now


class PositionManager:
    def __init__(self, repository: StorageRepository | None = None) -> None:
        self.repository = repository or StorageRepository()

    def register_open_position(
        self,
        *,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
        take_profit_price: float,
        trailing_stop_price: float | None,
        order_id: str | None,
    ) -> dict[str, object]:
        if quantity <= 0 or entry_price <= 0:
            self.repository.close_open_position(symbol.upper(), reason="invalid_position_rejected")
            raise ValueError(f"Invalid open position payload for {symbol}")
        payload = {
            "symbol": symbol.upper(),
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": entry_price,
            "unrealized_pnl": 0.0,
            "stop_price": stop_price,
            "take_profit_price": take_profit_price,
            "trailing_stop_price": trailing_stop_price,
            "order_id": order_id,
            "mode": settings.live_trading_mode,
            "status": "OPEN",
            "opened_at": utc_now(),
            "updated_at": utc_now(),
        }
        self.repository.upsert_open_position(payload)
        return payload

    def update_market_price(self, symbol: str, current_price: float) -> dict[str, object]:
        position = self.repository.get_open_position(symbol)
        if position is None:
            raise ValueError(f"Open position not found for {symbol}")
        entry_price = float(position["entry_price"])
        quantity = float(position["quantity"])
        if quantity <= 0 or current_price <= 0:
            self.repository.close_open_position(symbol.upper(), reason="invalid_position_removed")
            raise ValueError(f"Invalid open position state for {symbol}")
        position["current_price"] = current_price
        position["unrealized_pnl"] = (current_price - entry_price) * quantity
        position["updated_at"] = utc_now()
        self.repository.upsert_open_position(position)
        self.repository.update_open_trade_history_metrics(symbol, current_price)
        return position

    def update_stops(
        self,
        symbol: str,
        *,
        stop_price: float | None = None,
        take_profit_price: float | None = None,
        trailing_stop_price: float | None = None,
    ) -> dict[str, object]:
        position = self.repository.get_open_position(symbol)
        if position is None:
            raise ValueError(f"Open position not found for {symbol}")
        if stop_price is not None:
            position["stop_price"] = stop_price
        if take_profit_price is not None:
            position["take_profit_price"] = take_profit_price
        if trailing_stop_price is not None:
            position["trailing_stop_price"] = trailing_stop_price
        position["updated_at"] = utc_now()
        self.repository.upsert_open_position(position)
        return position

    def close_position(self, symbol: str) -> None:
        self.repository.close_open_position(symbol)

    def list_open_positions(self) -> list[dict[str, object]]:
        frame = self.repository.get_open_positions()
        if frame.empty:
            return []
        return frame.to_dict(orient="records")
