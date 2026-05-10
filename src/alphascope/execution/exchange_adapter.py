from __future__ import annotations

from typing import Any

from alphascope.config.settings import settings
from alphascope.execution.compat import BinanceClient, call_authenticated_binance, sync_binance_time_or_raise
from alphascope.execution.logging_utils import build_component_logger
from alphascope.execution.quantity_normalizer import validate_order_quantity


class ExchangeAdapter:
    def __init__(self, client: Any | None = None) -> None:
        self.logger = build_component_logger("exchange_adapter", settings.order_manager_log_path)
        if client is not None:
            self.client = client
            self._sync_client_clock()
            return
        self.client = BinanceClient(settings.binance_api_key, settings.binance_api_secret, testnet=settings.live_trading_mode == "testnet")
        if settings.live_trading_mode == "testnet":
            self.client.API_URL = settings.live_binance_base_url.rstrip("/") + "/"
        self._sync_client_clock()

    @staticmethod
    def _max_allowed_clock_drift_ms() -> int | None:
        return 5000 if settings.live_trading_mode == "live" else None

    def _sync_client_clock(self) -> int:
        return sync_binance_time_or_raise(
            self.client,
            logger=self.logger,
            max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
        )

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float | None = None) -> dict[str, Any]:
        exchange_info = dict(self.client.get_exchange_info())
        reference_price = float(price) if price is not None else float(self.client.get_symbol_ticker(symbol=symbol.upper())["price"])
        valid, details = validate_order_quantity(symbol.upper(), amount, reference_price, exchange_info)
        if not valid:
            raise ValueError(f"Order blocked: {details['reason']}")
        payload: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": details["normalized_quantity_str"],
        }
        if order_type.upper() == "LIMIT":
            payload["timeInForce"] = "GTC"
            payload["price"] = price
        response = dict(
            call_authenticated_binance(
                self.client,
                self.client.create_order,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
                **payload,
            )
        )
        response["_normalized_quantity"] = details["normalized_quantity"]
        response["_validation"] = details
        return response

    def cancel_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        return dict(
            call_authenticated_binance(
                self.client,
                self.client.cancel_order,
                symbol=symbol.upper(),
                orderId=order_id,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
            )
        )

    def fetch_positions(self) -> list[dict[str, Any]]:
        return []

    def fetch_balance(self) -> dict[str, Any]:
        return dict(
            call_authenticated_binance(
                self.client,
                self.client.get_account,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
            )
        )
