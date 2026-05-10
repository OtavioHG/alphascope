from __future__ import annotations

from datetime import UTC, datetime, timedelta

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.execution.compat import (
    EXECUTION_STATUS_CLOSED,
    EXECUTION_STATUS_CLOSED_ORPHAN,
    EXECUTION_STATUS_DUST_POSITION,
)
from alphascope.execution.logging_utils import build_component_logger
from alphascope.execution.order_manager import OrderManager
from alphascope.execution.position_manager import PositionManager
from alphascope.execution.risk_manager import RiskManager
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now


class StopManager:
    def __init__(
        self,
        order_manager: OrderManager,
        position_manager: PositionManager,
        risk_manager: RiskManager,
        repository: StorageRepository | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.repository = repository or StorageRepository()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.logger = build_component_logger("live_trading", settings.live_trading_log_path)

    def update_trailing_stop(self, symbol: str, current_price: float) -> dict[str, object]:
        position = self.position_manager.update_market_price(symbol, current_price)
        new_trailing = self.risk_manager.calculate_trailing_stop(current_price)
        current_trailing = float(position.get("trailing_stop_price") or 0.0)
        if new_trailing > current_trailing:
            position = self.position_manager.update_stops(symbol, trailing_stop_price=new_trailing)
        return position

    def check_stop_loss_hit(self, symbol: str, current_price: float) -> bool:
        position = self.repository.get_open_position(symbol)
        return position is not None and current_price <= float(position["stop_price"])

    def check_take_profit_hit(self, symbol: str, current_price: float) -> bool:
        position = self.repository.get_open_position(symbol)
        return position is not None and current_price >= float(position["take_profit_price"])

    def close_position(
        self,
        symbol: str,
        current_price: float,
        *,
        reason: str,
        requested_quantity: float | None = None,
    ) -> dict[str, object]:
        position = self.repository.get_open_position(symbol)
        if position is None:
            return {"symbol": symbol.upper(), "status": EXECUTION_STATUS_CLOSED_ORPHAN, "reason": "position_not_found"}
        local_quantity = float(position["quantity"])
        requested_sell_quantity = float(requested_quantity) if requested_quantity is not None else local_quantity
        safe_sell = self.order_manager.get_safe_sell_quantity(symbol, requested_sell_quantity, price=current_price)
        self.logger.info(
            "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional={} final_status={} motivo={} source={} order_id={} pnl=- risco=- saldo={}",
            symbol.upper(),
            local_quantity,
            safe_sell["real_balance"],
            requested_sell_quantity,
            safe_sell["safe_quantity"],
            safe_sell["normalized_quantity"],
            current_price,
            safe_sell["notional"],
            safe_sell["min_notional"],
            safe_sell["validation_status"],
            safe_sell["validation_reason"],
            reason,
            str(position.get("order_id") or "-"),
            self.order_manager.account_manager.get_free_balance("USDT"),
        )
        response = self.order_manager.place_order(symbol, "SELL", requested_sell_quantity, "MARKET", price=current_price)
        if response.get("blocked"):
            return self._handle_blocked_close(position, current_price=current_price, reason=reason, response=response)

        executed_price = float(response.get("executed_price") or current_price or 0.0)
        executed_quantity = float(response.get("executed_qty") or local_quantity or 0.0)
        entry_price = float(position["entry_price"])
        quantity = executed_quantity
        pnl = (executed_price - entry_price) * quantity
        pnl_pct = ((executed_price / entry_price) - 1.0) if entry_price > 0 else 0.0
        remaining_quantity = max(local_quantity - executed_quantity, 0.0)
        remaining_notional = remaining_quantity * executed_price
        self.repository.update_trade_execution(
            str(position.get("order_id") or response["orderId"]),
            {
                "exit_price": executed_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "status": EXECUTION_STATUS_CLOSED,
                "notes": reason,
            },
        )
        if remaining_quantity > 0 and remaining_notional >= settings.min_notional_usdt and reason == "partial_take_profit":
            position["quantity"] = remaining_quantity
            position["current_price"] = executed_price
            position["unrealized_pnl"] = (executed_price - entry_price) * remaining_quantity
            position["updated_at"] = utc_now()
            self.repository.upsert_open_position(position)
        else:
            self.repository.close_latest_open_trade(
                symbol=symbol,
                reason_closed=reason,
                exit_price=executed_price,
                fees_paid=0.0,
                stop_loss_hit=reason == "stop_loss",
                take_profit_hit=reason in {"take_profit", "partial_take_profit"},
                trailing_stop_hit=reason == "trailing_stop",
                notes_json={
                    "response": response,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "remaining_quantity": remaining_quantity,
                },
            )
            self.position_manager.close_position(symbol)
        daily = self.risk_manager.record_trade_close(
            pnl=pnl,
            pnl_pct=pnl_pct,
            open_positions=len(self.position_manager.list_open_positions()),
        )
        partial_close = quantity < local_quantity
        payload = {
            "symbol": symbol.upper(),
            "side": "SELL",
            "quantity": quantity,
            "price": executed_price,
            "realized_pnl": pnl,
            "mode": settings.live_trading_mode,
            "reason": "partial_close" if partial_close else reason,
        }
        self.alert_dispatcher.trade_closed(payload)
        if partial_close:
            self.alert_dispatcher.dispatch_raw(
                "partial_close",
                "Partial close executed",
                "\n".join(
                    [
                        f"symbol: {symbol.upper()}",
                        f"local_quantity: {local_quantity:.8f}",
                        f"executed_quantity: {quantity:.8f}",
                        f"real_balance: {float(response.get('_validation', {}).get('real_balance', 0.0)):.8f}",
                        "run_loop: continuing",
                    ]
                ),
                {
                    "symbol": symbol.upper(),
                    "local_quantity": local_quantity,
                    "executed_quantity": quantity,
                    "response": response,
                },
            )
        if reason == "stop_loss":
            self.alert_dispatcher.dispatch_raw(
                "stop_loss_hit",
                "Stop loss triggered",
                f"Stop loss acionado\nsymbol: {symbol}\nprice: {executed_price:.6f}",
                payload,
            )
        elif reason == "take_profit":
            self.alert_dispatcher.dispatch_raw(
                "take_profit_hit",
                "Take profit triggered",
                f"Take profit acionado\nsymbol: {symbol}\nprice: {executed_price:.6f}",
                payload,
            )
        elif reason == "trailing_stop":
            self.alert_dispatcher.dispatch_raw(
                "trailing_stop_hit",
                "Trailing stop triggered",
                f"Trailing stop acionado\nsymbol: {symbol}\nprice: {executed_price:.6f}",
                payload,
            )
        if bool(daily.get("paused")):
            self.alert_dispatcher.dispatch_raw(
                "daily_loss_limit",
                "Trading paused",
                "Perda diaria ou losses consecutivos atingidos",
                daily,
            )
        self.logger.info(
            "trade_executed symbol={} order_side=SELL order_value={} final_quantity={} trader=LiveTrader price={} reason={}",
            symbol.upper(),
            quantity * executed_price,
            quantity,
            executed_price,
            reason,
        )
        self.logger.warning(
            "symbol={} score=- saldo=- quantidade={} preco={} pnl={} risco=- motivo={}",
            symbol.upper(),
            quantity,
            executed_price,
            pnl,
            reason,
        )
        snapshot = self.order_manager.account_manager.generate_snapshot(reconcile=not partial_close)
        portfolio = dict(snapshot["snapshot_json"]["portfolio"])
        self.logger.info("order_response={}", response)
        self.logger.info("executed_price={} executed_qty={}", executed_price, executed_quantity)
        self.logger.info(
            "Post-trade portfolio\nequity: {:.4f}\ncash: {:.4f}\nopen positions: {}\nrealized pnl: {:.2f}\nunrealized pnl: {:.2f}",
            float(portfolio["equity"]),
            float(portfolio["cash"]),
            int(portfolio["open_positions"]),
            float(portfolio["realized_pnl"]),
            float(portfolio["unrealized_pnl"]),
        )
        return {"response": response, "pnl": pnl, "pnl_pct": pnl_pct, "reason": reason}

    def close_all_positions(self, current_prices: dict[str, float]) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for position in self.position_manager.list_open_positions():
            symbol = str(position["symbol"])
            if symbol in current_prices:
                results.append(self.close_position(symbol, float(current_prices[symbol]), reason="manual_close"))
        return results

    def emergency_close_all(self, current_prices: dict[str, float]) -> list[dict[str, object]]:
        results = self.close_all_positions(current_prices)
        self.order_manager.cancel_all_orders()
        return results

    def emergency_close_symbol(self, symbol: str, current_price: float | None = None) -> dict[str, object]:
        position = self.repository.get_open_position(symbol)
        resolved_price = float(current_price or 0.0)
        if resolved_price <= 0:
            resolved_price = float(self.order_manager.client.get_symbol_ticker(symbol=symbol.upper())["price"])
        if position is None:
            response = self.order_manager.place_order(symbol, "SELL", None, "MARKET", price=resolved_price)
            return {
                "symbol": symbol.upper(),
                "status": str(response.get("status", EXECUTION_STATUS_CLOSED_ORPHAN)),
                "reason": str(response.get("reason", "emergency_close")),
                "response": response,
            }
        return self.close_position(symbol, resolved_price, reason="emergency_close")

    def close_expired_positions(self, current_prices: dict[str, float]) -> list[dict[str, object]]:
        if not settings.enable_position_timeout:
            return []
        results: list[dict[str, object]] = []
        max_age = timedelta(hours=settings.max_position_duration_hours)
        now = datetime.now(UTC)
        for position in self.position_manager.list_open_positions():
            opened_at = position.get("opened_at")
            if not isinstance(opened_at, datetime):
                continue
            if now - opened_at < max_age:
                continue
            symbol = str(position["symbol"]).upper()
            current_price = float(current_prices.get(symbol, position.get("current_price", position.get("entry_price", 0.0))) or 0.0)
            if current_price <= 0:
                continue
            self.alert_dispatcher.dispatch_raw(
                "position_timeout",
                "Position timeout close",
                "\n".join(
                    [
                        f"symbol: {symbol}",
                        f"opened_at: {opened_at.isoformat()}",
                        f"max_hours: {settings.max_position_duration_hours}",
                        "action: auto_close",
                    ]
                ),
                {"symbol": symbol, "opened_at": opened_at.isoformat(), "max_hours": settings.max_position_duration_hours},
            )
            results.append(self.close_position(symbol, current_price, reason="position_timeout"))
        return results

    def _handle_blocked_close(
        self,
        position: dict[str, object],
        *,
        current_price: float,
        reason: str,
        response: dict[str, object],
    ) -> dict[str, object]:
        symbol = str(position["symbol"]).upper()
        validation = dict(response.get("_validation", {}))
        blocked_status = str(response.get("status", validation.get("validation_status", EXECUTION_STATUS_DUST_POSITION)))
        order_id = str(position.get("order_id") or "")
        if order_id:
            try:
                self.repository.update_trade_execution(
                    order_id,
                    {
                        "exit_price": current_price,
                        "status": blocked_status,
                        "notes": str(response.get("reason", reason)),
                    },
                )
            except Exception:
                pass
        self.position_manager.close_position(symbol)
        alert_payload = {
            "symbol": symbol,
            "local_quantity": float(position.get("quantity", 0.0) or 0.0),
            "real_balance": float(validation.get("real_balance", 0.0)),
            "requested_quantity": validation.get("requested_quantity"),
            "safe_quantity": float(validation.get("safe_quantity", 0.0)),
            "normalized_quantity": float(validation.get("normalized_quantity", 0.0)),
            "price": float(validation.get("price", current_price) or current_price),
            "notional": float(validation.get("notional", 0.0)),
            "min_notional": float(validation.get("min_notional", 0.0)),
            "final_status": blocked_status,
            "reason": str(response.get("reason", reason)),
            "source": reason,
            "order_id": order_id or "-",
        }
        self.alert_dispatcher.dispatch_raw(
            "position_blocked",
            f"Position removed [{blocked_status}]",
            "\n".join(
                [
                    f"symbol: {symbol}",
                    f"status: {blocked_status}",
                    f"reason: {alert_payload['reason']}",
                    f"real_balance: {alert_payload['real_balance']:.8f}",
                    f"normalized_quantity: {alert_payload['normalized_quantity']:.8f}",
                    f"notional: {alert_payload['notional']:.8f}",
                    f"min_notional: {alert_payload['min_notional']:.8f}",
                    "monitoring: removed",
                    "run_loop: continuing",
                ]
            ),
            alert_payload,
        )
        self.logger.warning(
            "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional={} final_status={} motivo={} source={} order_id={} pnl=- risco=- saldo={}",
            symbol,
            alert_payload["local_quantity"],
            alert_payload["real_balance"],
            alert_payload["requested_quantity"],
            alert_payload["safe_quantity"],
            alert_payload["normalized_quantity"],
            alert_payload["price"],
            alert_payload["notional"],
            alert_payload["min_notional"],
            blocked_status,
            alert_payload["reason"],
            reason,
            order_id or "-",
            self.order_manager.account_manager.get_free_balance("USDT"),
        )
        return {
            "symbol": symbol,
            "status": blocked_status,
            "reason": alert_payload["reason"],
            "response": response,
            "pnl": 0.0,
            "pnl_pct": 0.0,
        }
