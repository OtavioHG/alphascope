from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from alphascope.config.settings import settings
from alphascope.execution.account_manager import AccountManager
from alphascope.execution.order_sizing import OrderSizing, calculate_order_sizing
from alphascope.execution.logging_utils import build_component_logger
from alphascope.storage.repositories import StorageRepository


class RiskManager:
    def __init__(self, account_manager: AccountManager, repository: StorageRepository | None = None) -> None:
        self.account_manager = account_manager
        self.repository = repository or StorageRepository()
        self.logger = build_component_logger("risk_manager", settings.risk_manager_log_path)

    def can_open_position(self, symbol: str, *, signal_score: float, price: float, quantity: float | None = None) -> tuple[bool, str]:
        checks = [
            (self.can_open_new_trade(), "max_open_trades_reached"),
            (not self.is_symbol_open(symbol), "symbol_already_open"),
            (self.check_daily_loss_limit(), "daily_loss_limit_reached"),
            (self.check_account_exposure(), "max_account_exposure_reached"),
            (self.validate_signal_score(signal_score), "signal_score_below_minimum"),
            (quantity is None or self.validate_min_notional(price=price, quantity=quantity), "min_notional_not_met"),
            (not self.is_paused_after_consecutive_losses(), "consecutive_losses_pause"),
            (not settings.live_emergency_stop, "emergency_stop_enabled"),
            (settings.live_kill_switch_enabled, "kill_switch_disabled"),
        ]
        for approved, reason in checks:
            if not approved:
                self._record_event(symbol, "open_position_blocked", "blocked", reason, {"signal_score": signal_score, "price": price, "quantity": quantity})
                return False, reason
        return True, "approved"

    def can_open_new_trade(self) -> bool:
        return len(self.repository.get_open_positions()) < settings.max_open_trades

    def is_symbol_open(self, symbol: str) -> bool:
        return self.repository.get_open_position(symbol) is not None

    def calculate_position_size(self, balance: float, risk_pct: float | None = None) -> float:
        del risk_pct
        return calculate_order_sizing(1.0, available_balance=balance).order_value_usd

    def calculate_order_size(
        self,
        *,
        balance: float,
        price: float,
        symbol: str | None = None,
        exchange_info: dict[str, Any] | None = None,
    ) -> OrderSizing:
        return calculate_order_sizing(
            price,
            available_balance=balance,
            symbol=symbol,
            exchange_info=exchange_info,
        )

    def calculate_stop_loss(self, entry_price: float) -> float:
        return entry_price * (1.0 - settings.stop_loss_pct)

    def calculate_take_profit(self, entry_price: float) -> float:
        return entry_price * (1.0 + settings.take_profit_pct)

    def calculate_trailing_stop(self, current_price: float) -> float:
        return current_price * (1.0 - settings.trailing_stop_pct)

    def check_daily_loss_limit(self) -> bool:
        daily = self.repository.get_daily_performance()
        if daily is None:
            return True
        return abs(float(daily.get("realized_pnl_pct", 0.0))) < settings.max_daily_loss_pct or float(daily.get("realized_pnl", 0.0)) >= 0

    def check_account_exposure(self) -> bool:
        exposure = self.account_manager.calculate_portfolio_exposure()
        return exposure < settings.max_account_exposure_pct

    def validate_min_notional(self, *, price: float, quantity: float) -> bool:
        return (price * quantity) >= settings.min_notional_usdt

    def validate_signal_score(self, score: float) -> bool:
        return score >= settings.min_confidence_score

    def calculate_drawdown(self, current_equity: float, peak_equity: float) -> float:
        if peak_equity <= 0:
            return 0.0
        return max((peak_equity - current_equity) / peak_equity, 0.0)

    def is_paused_after_consecutive_losses(self) -> bool:
        daily = self.repository.get_daily_performance()
        if daily is None:
            return False
        return int(daily.get("consecutive_losses", 0)) >= settings.max_consecutive_losses or bool(daily.get("paused", False))

    def record_trade_close(self, *, pnl: float, pnl_pct: float, open_positions: int) -> dict[str, Any]:
        today = datetime.now(UTC).date()
        current = self.repository.get_daily_performance(today) or {
            "date": today,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "realized_pnl": 0.0,
            "realized_pnl_pct": 0.0,
            "max_drawdown": 0.0,
            "open_positions": open_positions,
            "consecutive_losses": 0,
            "paused": False,
            "updated_at": datetime.now(UTC),
        }
        current["total_trades"] = int(current["total_trades"]) + 1
        current["realized_pnl"] = float(current["realized_pnl"]) + pnl
        current["realized_pnl_pct"] = float(current["realized_pnl_pct"]) + pnl_pct
        if pnl >= 0:
            current["wins"] = int(current["wins"]) + 1
            current["consecutive_losses"] = 0
        else:
            current["losses"] = int(current["losses"]) + 1
            current["consecutive_losses"] = int(current.get("consecutive_losses", 0)) + 1
        total_trades = max(int(current["total_trades"]), 1)
        current["win_rate"] = float(current["wins"]) / total_trades
        current["open_positions"] = open_positions
        current["paused"] = (
            abs(float(current["realized_pnl_pct"])) >= settings.max_daily_loss_pct and float(current["realized_pnl"]) < 0
        ) or int(current["consecutive_losses"]) >= settings.max_consecutive_losses
        current["updated_at"] = datetime.now(UTC)
        self.repository.upsert_daily_performance(current)
        if current["paused"]:
            self._record_event(None, "risk_pause", "blocked", "daily_loss_or_consecutive_losses", current)
        return current

    def _record_event(self, symbol: str | None, event_type: str, decision: str, reason: str, payload: dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now(UTC),
            "symbol": symbol.upper() if symbol else None,
            "event_type": event_type,
            "severity": "warning" if decision == "blocked" else "info",
            "decision": decision,
            "reason": reason,
            "payload_json": payload,
            "created_at": datetime.now(UTC),
        }
        self.repository.save_risk_event(event)
        self.logger.warning(
            "symbol={} score={} saldo={} quantidade={} preço={} pnl={} risco={} motivo={}",
            symbol or "ALL",
            payload.get("signal_score", "-"),
            payload.get("balance", "-"),
            payload.get("quantity", "-"),
            payload.get("price", "-"),
            payload.get("pnl", "-"),
            json.dumps(payload, default=str),
            reason,
        )
