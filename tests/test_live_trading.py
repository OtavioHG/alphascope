from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest

from alphascope.config.settings import settings
from alphascope.execution.account_manager import AccountManager
from alphascope.execution.compat import (
    BinanceAPIException,
    EXECUTION_STATUS_BLOCKED_INSUFFICIENT_BALANCE,
    EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL,
    EXECUTION_STATUS_CLOSED_ORPHAN,
    EXECUTION_STATUS_DUST_POSITION,
    get_safe_sell_quantity,
)
from alphascope.config.settings import settings
from alphascope.execution.live_trader import LiveTrader
from alphascope.execution.order_manager import OrderManager
from alphascope.execution.order_sizing import calculate_order_quantity, calculate_order_sizing
from alphascope.execution.paper_trader import PaperTrader
from alphascope.execution.position_manager import PositionManager
from alphascope.execution.quantity_normalizer import normalize_quantity, validate_order_quantity
from alphascope.execution.risk_manager import RiskManager
from alphascope.execution.stop_manager import StopManager


@pytest.fixture(autouse=True)
def _stable_live_settings() -> None:
    overrides = {
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "trailing_stop_pct": 0.01,
        "max_position_size_pct": 0.02,
        "max_open_trades": 5,
        "min_confidence_score": 0.6,
        "min_notional_usdt": 10.0,
        "live_kill_switch_enabled": True,
        "live_emergency_stop": False,
        "max_account_exposure_pct": 0.5,
        "max_daily_loss_pct": 0.2,
        "max_consecutive_losses": 3,
        "default_order_usd": 15.0,
        "order_size_usdt": 15.0,
        "min_trade_value": 15.0,
        "min_position_usd": 15.0,
        "max_position_usd": 25.0,
        "risk_per_trade": 0.10,
        "auto_sync_account": True,
        "enable_position_timeout": True,
        "max_position_duration_hours": 6,
        "enable_partial_take_profit": True,
        "partial_take_profit_pct": 0.02,
        "partial_take_profit_size": 0.5,
        "enable_break_even": True,
        "break_even_trigger_pct": 0.01,
        "break_even_offset_pct": 0.001,
        "telegram_enabled": False,
        "enable_telegram_alerts": False,
    }
    original = {name: getattr(settings, name) for name in overrides}
    for name, value in overrides.items():
        object.__setattr__(settings, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            object.__setattr__(settings, name, value)


class FakeRepository:
    INVALID_POSITION_STATUSES = {"closed", "sold", "cancelled", "canceled"}

    def __init__(self) -> None:
        self.open_positions: dict[str, dict[str, object]] = {}
        self.trade_executions: list[dict[str, object]] = []
        self.account_snapshots: list[dict[str, object]] = []
        self.risk_events: list[dict[str, object]] = []
        self.daily_performance: dict[object, dict[str, object]] = {}
        self.snapshots: list[dict[str, object]] = []
        self.saved_trades: list[dict[str, object]] = []
        self.trade_history: list[dict[str, object]] = []

    def get_open_positions(self) -> pd.DataFrame:
        self.cleanup_persisted_positions()
        return pd.DataFrame(self.open_positions.values())

    def get_open_position(self, symbol: str) -> dict[str, object] | None:
        self.cleanup_persisted_positions()
        position = self.open_positions.get(symbol.upper())
        if position and not self.is_valid_open_position(position):
            self.close_open_position(symbol.upper(), reason="invalid_position_removed")
            return None
        return position

    def upsert_open_position(self, position: dict[str, object]) -> int:
        if not self.is_valid_open_position(position):
            symbol = str(position.get("symbol", "")).upper()
            if symbol:
                self.close_open_position(symbol, reason="invalid_position_rejected")
            return 0
        self.open_positions[str(position["symbol"]).upper()] = dict(position)
        return 1

    def close_open_position(self, symbol: str, *, reason: str = "position_closed") -> int:
        self.open_positions.pop(symbol.upper(), None)
        self.reconcile_trade_execution(symbol=symbol, reason=reason)
        return 1

    def save_trade_execution(self, trade: dict[str, object]) -> int:
        self.trade_executions.append(dict(trade))
        return 1

    def update_trade_execution(self, order_id: str, updates: dict[str, object]) -> int:
        for trade in self.trade_executions:
            if str(trade["order_id"]) == str(order_id):
                trade.update(updates)
                return 1
        raise AssertionError("trade execution not found")

    def get_trade_executions(self, **_: Any) -> pd.DataFrame:
        return pd.DataFrame(self.trade_executions)

    def save_account_snapshot(self, snapshot: dict[str, object]) -> int:
        self.account_snapshots.append(dict(snapshot))
        return 1

    def get_latest_account_snapshot(self) -> dict[str, object] | None:
        return self.account_snapshots[-1] if self.account_snapshots else None

    def save_trades(self, trades: list[dict[str, object]]) -> int:
        self.saved_trades.extend(dict(trade) for trade in trades)
        return len(trades)

    def save_snapshot(self, snapshot: dict[str, object]) -> int:
        self.snapshots.append(dict(snapshot))
        return 1

    def get_latest_snapshot(self) -> dict[str, object] | None:
        return self.snapshots[-1] if self.snapshots else None

    def save_risk_event(self, event: dict[str, object]) -> int:
        self.risk_events.append(dict(event))
        return 1

    def get_daily_performance(self, target_date: object | None = None) -> dict[str, object] | None:
        if target_date is None:
            return next(reversed(self.daily_performance.values()), None)
        return self.daily_performance.get(target_date)

    def upsert_daily_performance(self, performance: dict[str, object]) -> int:
        self.daily_performance[performance["date"]] = dict(performance)
        return 1

    def get_live_account_view(self) -> dict[str, object]:
        self.cleanup_persisted_positions()
        return {
            "account_snapshot": self.get_latest_account_snapshot() or {},
            "daily_performance": self.get_daily_performance() or {},
            "open_positions": list(self.open_positions.values()),
            "exposure_pct": (self.get_latest_account_snapshot() or {}).get("exposure_pct", 0.0),
            "open_positions_count": len(self.open_positions),
        }

    def open_trade_history(self, payload: dict[str, object]) -> str:
        self.trade_history.append(dict(payload))
        return str(payload["trade_id"])

    def close_latest_open_trade(self, *, symbol: str, **updates: Any) -> dict[str, object]:
        for trade in reversed(self.trade_history):
            if str(trade.get("symbol", "")).upper() != symbol.upper():
                continue
            if str(trade.get("status", "")).upper() != "OPEN":
                continue
            trade.update(updates)
            trade["status"] = "CLOSED"
            return trade
        payload = {"symbol": symbol.upper(), "status": "CLOSED", **updates}
        self.trade_history.append(payload)
        return payload

    def update_open_trade_history_metrics(self, symbol: str, current_price: float) -> int:
        for trade in reversed(self.trade_history):
            if str(trade.get("symbol", "")).upper() == symbol.upper() and str(trade.get("status", "")).upper() == "OPEN":
                trade["current_price"] = current_price
                return 1
        return 0

    def cleanup_persisted_positions(self) -> dict[str, int]:
        invalid_symbols = [symbol for symbol, position in list(self.open_positions.items()) if not self.is_valid_open_position(position)]
        for symbol in invalid_symbols:
            self.close_open_position(symbol, reason="invalid_position_removed")
        removed_trade_rows = 0
        cleaned_trades: list[dict[str, object]] = []
        for trade in self.trade_executions:
            if float(trade.get("quantity", 0.0) or 0.0) <= 0:
                removed_trade_rows += 1
                continue
            cleaned_trades.append(trade)
        self.trade_executions = cleaned_trades
        return {
            "invalid_open_positions_removed": len(invalid_symbols),
            "invalid_trade_rows_removed": removed_trade_rows,
            "orphan_open_trades_closed": 0,
        }

    def reconcile_trade_execution(
        self,
        *,
        symbol: str | None = None,
        order_id: str | None = None,
        reason: str,
    ) -> int:
        updated = 0
        for trade in self.trade_executions:
            if str(trade.get("status", "")).upper() != "OPEN":
                continue
            if order_id and str(trade.get("order_id")) != str(order_id):
                continue
            if not order_id and symbol and str(trade.get("symbol", "")).upper() != str(symbol).upper():
                continue
            trade["status"] = "CLOSED"
            trade["notes"] = reason
            updated += 1
        return updated

    @classmethod
    def is_valid_open_position(cls, position: dict[str, object]) -> bool:
        symbol = str(position.get("symbol", "")).strip().upper()
        status = str(position.get("status", "open")).strip().lower()
        quantity = float(position.get("quantity", 0.0) or 0.0)
        entry_price = float(position.get("entry_price", 0.0) or 0.0)
        current_price = float(position.get("current_price", 0.0) or 0.0)
        executed_qty = position.get("executed_qty")
        if not symbol:
            return False
        if quantity <= 0 or entry_price <= 0 or current_price <= 0:
            return False
        if status in cls.INVALID_POSITION_STATUSES:
            return False
        if executed_qty is not None and float(executed_qty or 0.0) <= 0:
            return False
        return True


class FakeClient:
    def __init__(self) -> None:
        self.orders: list[dict[str, Any]] = []
        self.create_order_calls = 0
        self.raise_precision_once = False
        self.raise_insufficient_balance_once = False
        self.next_fill_price: float | None = None
        self.timestamp_offset = 0
        self.balances = {
            "USDT": {"free": "1000", "locked": "0"},
            "BTC": {"free": "0", "locked": "0"},
            "DOGE": {"free": "0", "locked": "0"},
            "ADA": {"free": "0", "locked": "0"},
            "XRP": {"free": "0", "locked": "0"},
            "BNB": {"free": "0", "locked": "0"},
            "SOL": {"free": "0", "locked": "0"},
            "ETH": {"free": "0", "locked": "0"},
        }
        self.exchange_info = {
            "symbols": [
                {
                    "symbol": "DOGEUSDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "1", "minQty": "1", "maxQty": "1000000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
                {
                    "symbol": "ADAUSDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.1", "minQty": "0.1", "maxQty": "1000000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
                {
                    "symbol": "XRPUSDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.1", "minQty": "0.1", "maxQty": "1000000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
                {
                    "symbol": "BTCUSDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.000001", "minQty": "0.000001", "maxQty": "1000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
                {
                    "symbol": "BNBUSDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "100000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
                {
                    "symbol": "SOLUSDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.01", "minQty": "0.01", "maxQty": "100000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
                {
                    "symbol": "ETHUSDT",
                    "baseAsset": "ETH",
                    "filters": [
                        {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "100000"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                    ],
                },
            ]
        }
        self.tickers = {
            "DOGEUSDT": "0.09047",
            "ADAUSDT": "0.2447",
            "XRPUSDT": "1.3127",
            "BTCUSDT": "68801.39",
            "BNBUSDT": "598.78",
            "SOLUSDT": "180.25",
            "ETHUSDT": "3100.00",
        }

    def get_account(self) -> dict[str, Any]:
        return {
            "balances": [
                {"asset": asset, "free": payload["free"], "locked": payload["locked"]}
                for asset, payload in self.balances.items()
            ]
        }

    def get_server_time(self) -> dict[str, int]:
        return {"serverTime": int(datetime.now(UTC).timestamp() * 1000)}

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        if symbol:
            return [order for order in self.orders if order["symbol"] == symbol and order["status"] == "NEW"]
        return [order for order in self.orders if order["status"] == "NEW"]

    def get_exchange_info(self) -> dict[str, Any]:
        return self.exchange_info

    def get_symbol_ticker(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "price": self.tickers[symbol]}

    def create_order(self, **params: Any) -> dict[str, Any]:
        self.create_order_calls += 1
        if self.raise_precision_once and self.create_order_calls == 1:
            exc = BinanceAPIException(None, 400, '{"code": -1111, "msg": "Parameter \\"quantity\\" has too much precision."}')
            raise exc
        execution_price = float(self.next_fill_price or params.get("price") or self.tickers[params["symbol"]])
        execution_quantity = float(params["quantity"])
        base_asset = params["symbol"].removesuffix("USDT")
        order_value = execution_price * execution_quantity
        if params["side"] == "SELL":
            available_balance = float(self.balances.setdefault(base_asset, {"free": "0", "locked": "0"})["free"])
            if self.raise_insufficient_balance_once and self.create_order_calls == 1:
                raise BinanceAPIException(None, 400, '{"code": -2010, "msg": "Account has insufficient balance for requested action."}')
            if execution_quantity > available_balance + 1e-12:
                raise BinanceAPIException(None, 400, '{"code": -2010, "msg": "Account has insufficient balance for requested action."}')
        if params["side"] == "BUY":
            self.balances["USDT"]["free"] = str(float(self.balances["USDT"]["free"]) - order_value)
            self.balances.setdefault(base_asset, {"free": "0", "locked": "0"})
            self.balances[base_asset]["free"] = str(float(self.balances[base_asset]["free"]) + execution_quantity)
        elif params["side"] == "SELL":
            self.balances["USDT"]["free"] = str(float(self.balances["USDT"]["free"]) + order_value)
            self.balances.setdefault(base_asset, {"free": "0", "locked": "0"})
            self.balances[base_asset]["free"] = str(float(self.balances[base_asset]["free"]) - execution_quantity)
        order = {
            "symbol": params["symbol"],
            "orderId": len(self.orders) + 1,
            "price": str(params.get("price", 0.0)),
            "origQty": str(params["quantity"]),
            "executedQty": str(params["quantity"]),
            "status": "FILLED",
            "side": params["side"],
            "fills": [{"price": str(execution_price), "qty": str(execution_quantity)}],
        }
        self.orders.append(order)
        return order

    def cancel_order(self, symbol: str, orderId: str) -> dict[str, Any]:
        return {"symbol": symbol, "orderId": orderId, "status": "CANCELED"}

    def get_order(self, symbol: str, orderId: str) -> dict[str, Any]:
        return {"symbol": symbol, "orderId": orderId, "status": "NEW"}


def _make_local_test_dir(name: str) -> Path:
    path = Path("data/runtime/test_live_trading") / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_stack() -> tuple[FakeRepository, FakeClient, AccountManager, RiskManager, OrderManager, PositionManager, StopManager]:
    repository = FakeRepository()
    client = FakeClient()
    account_manager = AccountManager(client=client, repository=repository)
    risk_manager = RiskManager(account_manager=account_manager, repository=repository)
    order_manager = OrderManager(client=client, repository=repository, account_manager=account_manager)
    position_manager = PositionManager(repository=repository)
    stop_manager = StopManager(
        order_manager=order_manager,
        position_manager=position_manager,
        risk_manager=risk_manager,
        repository=repository,
    )
    return repository, client, account_manager, risk_manager, order_manager, position_manager, stop_manager


def _seed_open_trade(repository: FakeRepository, *, symbol: str, quantity: float, entry_price: float, order_id: str) -> None:
    repository.save_trade_execution(
        {
            "timestamp": datetime.now(UTC),
            "symbol": symbol,
            "side": "BUY",
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": None,
            "stop_loss_price": entry_price * 0.98,
            "take_profit_price": entry_price * 1.04,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": "OPEN",
            "order_id": order_id,
            "source": "test",
            "mode": "testnet",
            "confidence_score": 0.8,
            "notes": "",
            "created_at": datetime.now(UTC),
        }
    )
    repository.open_trade_history(
        {
            "trade_id": order_id,
            "order_id": order_id,
            "symbol": symbol,
            "timeframe": "1h",
            "side": "BUY",
            "mode": "testnet",
            "status": "OPEN",
            "entry_time": datetime.now(UTC),
            "entry_price": entry_price,
            "quantity": quantity,
            "order_size_usdt": quantity * entry_price,
            "fees_paid": 0.0,
            "ranking_score": 0.8,
            "confidence_score": 0.8,
            "ml_score": 0.8,
            "heuristic_score": 0.8,
            "news_score": 0.0,
            "volatility": 0.0,
            "volume_ratio": 0.0,
            "trend_direction": "up",
            "reason_opened": "test",
            "notes_json": {},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )


def test_position_calculation_and_min_notional() -> None:
    _, _, account_manager, risk_manager, _, _, _ = _build_stack()
    position_notional = risk_manager.calculate_position_size(account_manager.get_free_balance("USDT"), 0.02)
    assert position_notional == 15.0
    assert risk_manager.validate_min_notional(price=100.0, quantity=0.2) is True


def test_calculate_order_quantity_uses_fixed_usdt_targets() -> None:
    assert round(calculate_order_quantity(0.095), 2) == 157.89
    assert round(calculate_order_quantity(0.26), 2) == 57.69
    assert round(calculate_order_quantity(1.37), 2) == 10.95


def test_calculate_order_sizing_blocks_when_balance_is_below_minimum_order() -> None:
    sizing = calculate_order_sizing(0.095, available_balance=9.0, symbol="DOGEUSDT")
    assert sizing.blocked_reason == "insufficient_balance"
    assert round(sizing.final_notional, 2) == 15.0


def test_stop_loss_take_profit_and_trailing_stop_calculation() -> None:
    _, _, _, risk_manager, _, _, _ = _build_stack()
    assert round(risk_manager.calculate_stop_loss(100.0), 2) == 98.0
    assert round(risk_manager.calculate_take_profit(100.0), 2) == 104.0
    assert round(risk_manager.calculate_trailing_stop(100.0), 2) == 99.0


def test_risk_manager_blocks_duplicate_open_symbol() -> None:
    repository, _, account_manager, risk_manager, _, position_manager, _ = _build_stack()
    position_manager.register_open_position(
        symbol="BTCUSDT",
        quantity=0.1,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        trailing_stop_price=99.0,
        order_id="1",
    )
    approved, reason = risk_manager.can_open_position("BTCUSDT", signal_score=0.8, price=100.0, quantity=0.2)
    assert approved is False
    assert reason == "symbol_already_open"
    assert repository.risk_events


def test_account_exposure_calculation() -> None:
    _, client, account_manager, _, _, position_manager, _ = _build_stack()
    client.balances["ETH"]["free"] = "2"
    position_manager.register_open_position(
        symbol="ETHUSDT",
        quantity=2.0,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        trailing_stop_price=99.0,
        order_id="2",
    )
    position_manager.update_market_price("ETHUSDT", 110.0)
    assert round(account_manager.calculate_portfolio_exposure(), 6) == round(220.0 / 1220.0, 6)


def test_drawdown_calculation() -> None:
    _, _, _, risk_manager, _, _, _ = _build_stack()
    assert risk_manager.calculate_drawdown(900.0, 1000.0) == 0.1


def test_order_creation_is_persisted() -> None:
    repository, client, account_manager, _, order_manager, _, _ = _build_stack()
    response = order_manager.place_market_buy("BTCUSDT", 0.2, score=0.7)
    assert response["orderId"] == 1
    assert len(client.orders) == 1
    assert len(repository.trade_executions) == 1
    assert repository.trade_executions[0]["symbol"] == "BTCUSDT"
    assert repository.trade_executions[0]["quantity"] == pytest.approx(0.014461)
    assert repository.trade_executions[0]["entry_price"] == 68801.39
    assert account_manager.get_open_orders("BTCUSDT") == []


def test_close_position_updates_trade_and_daily_performance() -> None:
    repository, client, _, _, order_manager, position_manager, stop_manager = _build_stack()
    client.next_fill_price = 104.0
    client.balances["BTC"]["free"] = "0.2"
    repository.save_trade_execution(
        {
            "timestamp": datetime.now(UTC),
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.2,
            "entry_price": 100.0,
            "exit_price": None,
            "stop_loss_price": 98.0,
            "take_profit_price": 104.0,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": "OPEN",
            "order_id": "1",
            "source": "test",
            "mode": "testnet",
            "confidence_score": 0.8,
            "notes": "",
            "created_at": datetime.now(UTC),
        }
    )
    position_manager.register_open_position(
        symbol="BTCUSDT",
        quantity=0.2,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        trailing_stop_price=99.0,
        order_id="1",
    )
    result = stop_manager.close_position("BTCUSDT", 104.0, reason="take_profit")
    assert result["pnl"] == 0.796
    assert repository.get_open_position("BTCUSDT") is None
    assert repository.trade_executions[0]["status"] == "CLOSED"
    assert repository.get_daily_performance() is not None


def test_live_trader_processes_rankings_and_opens_position() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.next_fill_price = 0.0954
    test_dir = _make_local_test_dir("process_signals")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    rankings = pd.DataFrame([{"symbol": "DOGEUSDT", "final_score": 0.8, "price": 0.09047}])
    result = trader.process_live_signals(rankings)
    assert result[0]["status"] == "opened"
    assert result[0]["quantity"] == 166.0
    assert result[0]["entry_price"] == 0.0954
    assert repository.get_open_position("DOGEUSDT") is not None
    assert float(repository.get_open_position("DOGEUSDT")["entry_price"]) == 0.0954
    assert (test_dir / "live_state.json").exists()


def test_live_trader_blocks_when_balance_is_below_minimum_order() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["USDT"]["free"] = "5"
    test_dir = _make_local_test_dir("insufficient_balance")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    rankings = pd.DataFrame([{"symbol": "DOGEUSDT", "final_score": 0.8, "price": 0.09047}])
    result = trader.process_live_signals(rankings)
    assert result[0]["status"] == "blocked"
    assert result[0]["reason"] == "insufficient_balance"


def test_live_trader_small_real_balance_is_not_blocked_by_static_minimum_balance_gate() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.next_fill_price = 0.09047
    client.balances["USDT"]["free"] = "9.7"
    original_min_notional = settings.min_notional_usdt
    original_default_order = settings.default_order_usd
    original_order_size = settings.order_size_usdt
    original_min_position = settings.min_position_usd
    original_min_trade = settings.min_trade_value
    original_max_position = settings.max_position_usd
    original_min_balance = settings.min_balance_required
    try:
        object.__setattr__(settings, "min_notional_usdt", 4.0)
        object.__setattr__(settings, "default_order_usd", 5.0)
        object.__setattr__(settings, "order_size_usdt", 5.0)
        object.__setattr__(settings, "min_position_usd", 4.0)
        object.__setattr__(settings, "min_trade_value", 4.0)
        object.__setattr__(settings, "max_position_usd", 5.0)
        object.__setattr__(settings, "min_balance_required", 10.0)
        test_dir = _make_local_test_dir("small_real_balance")
        trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
        trader.order_manager.get_exchange_info = lambda: {
            "symbols": [
                {
                    "symbol": "DOGEUSDT",
                    "filters": [{"filterType": "MIN_NOTIONAL", "minNotional": "4"}],
                }
            ]
        }
        rankings = pd.DataFrame([{"symbol": "DOGEUSDT", "final_score": 0.8, "price": 0.09047}])
        result = trader.process_live_signals(rankings)
        assert result[0]["reason"] != "insufficient_balance"
    finally:
        object.__setattr__(settings, "min_notional_usdt", original_min_notional)
        object.__setattr__(settings, "default_order_usd", original_default_order)
        object.__setattr__(settings, "order_size_usdt", original_order_size)
        object.__setattr__(settings, "min_position_usd", original_min_position)
        object.__setattr__(settings, "min_trade_value", original_min_trade)
        object.__setattr__(settings, "max_position_usd", original_max_position)
        object.__setattr__(settings, "min_balance_required", original_min_balance)


def test_sync_account_persists_snapshot() -> None:
    repository = FakeRepository()
    client = FakeClient()
    test_dir = _make_local_test_dir("sync_account")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    snapshot = trader.sync_account()
    assert snapshot["total_balance"] == 1000.0
    assert repository.get_latest_account_snapshot() is not None


def test_sync_account_removes_ghost_position_without_asset_balance() -> None:
    repository = FakeRepository()
    client = FakeClient()
    repository.upsert_open_position(
        {
            "symbol": "DOGEUSDT",
            "quantity": 53.0,
            "entry_price": 0.09466,
            "current_price": 0.09435,
            "unrealized_pnl": -0.01,
            "stop_price": 0.092,
            "take_profit_price": 0.098,
            "trailing_stop_price": 0.093,
            "order_id": "ghost-1",
            "mode": "live",
            "status": "OPEN",
            "opened_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )
    repository.save_trade_execution(
        {
            "timestamp": datetime.now(UTC),
            "symbol": "DOGEUSDT",
            "side": "BUY",
            "quantity": 53.0,
            "entry_price": 0.09466,
            "exit_price": None,
            "stop_loss_price": 0.092,
            "take_profit_price": 0.098,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": "OPEN",
            "order_id": "ghost-1",
            "source": "test",
            "mode": "live",
            "confidence_score": 0.8,
            "notes": "",
            "created_at": datetime.now(UTC),
        }
    )
    client.balances["DOGE"]["free"] = "0"
    test_dir = _make_local_test_dir("sync_account_cleanup")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")

    snapshot = trader.sync_account()

    assert repository.get_open_position("DOGEUSDT") is None
    assert snapshot["open_positions"] == 0
    assert snapshot["snapshot_json"]["portfolio"]["open_positions"] == 0
    assert snapshot["snapshot_json"]["portfolio"]["exposure"] == 0.0
    assert snapshot["exposure_pct"] == 0.0
    assert repository.trade_executions[0]["status"] == EXECUTION_STATUS_CLOSED_ORPHAN


def test_monitor_positions_closes_on_stop_hit() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["BTC"]["free"] = "0.2"
    test_dir = _make_local_test_dir("monitor_positions")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    repository.save_trade_execution(
        {
            "timestamp": datetime.now(UTC),
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.2,
            "entry_price": 100.0,
            "exit_price": None,
            "stop_loss_price": 98.0,
            "take_profit_price": 104.0,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": "OPEN",
            "order_id": "1",
            "source": "test",
            "mode": "testnet",
            "confidence_score": 0.8,
            "notes": "",
            "created_at": datetime.now(UTC),
        }
    )
    trader.position_manager.register_open_position(
        symbol="BTCUSDT",
        quantity=0.2,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        trailing_stop_price=99.0,
        order_id="1",
    )
    closed = trader.monitor_positions({"BTCUSDT": 97.0})
    assert len(closed) == 1
    assert repository.get_open_position("BTCUSDT") is None


@pytest.mark.parametrize(
    ("symbol", "quantity", "price", "expected_quantity", "expected_valid"),
    [
        ("DOGEUSDT", 100.93998390448816, 0.09047, 101.0, False),
        ("ADAUSDT", 41.987, 0.2447, 42.0, True),
        ("XRPUSDT", 20.987, 1.3127, 21.0, True),
        ("BTCUSDT", 0.00123456789, 68801.39, 0.001235, True),
        ("BNBUSDT", 0.123456, 598.78, 0.124, True),
        ("SOLUSDT", 0.98765, 180.25, 0.99, True),
    ],
)
def test_normalize_quantity_for_required_symbols(symbol: str, quantity: float, price: float, expected_quantity: float, expected_valid: bool) -> None:
    client = FakeClient()
    normalized = normalize_quantity(symbol, quantity, client.get_exchange_info(), side="BUY")
    assert normalized["normalized_quantity"] == expected_quantity
    valid, details = validate_order_quantity(symbol, quantity, price, client.get_exchange_info(), side="BUY")
    assert valid is expected_valid
    assert details["normalized_quantity"] == expected_quantity


def test_validate_order_quantity_blocks_min_notional() -> None:
    client = FakeClient()
    valid, details = validate_order_quantity("DOGEUSDT", 100.93998390448816, 0.09047, client.get_exchange_info(), side="BUY")
    assert valid is False
    assert details["reason"] == "min_notional_not_met"


def test_validate_order_quantity_blocks_min_qty() -> None:
    client = FakeClient()
    valid, details = validate_order_quantity("BTCUSDT", 0.0000009, 68801.39, client.get_exchange_info(), side="SELL")
    assert valid is False
    assert details["reason"] == "invalid_quantity"


def test_order_manager_normalizes_quantity_before_create_order() -> None:
    repository, client, account_manager, _, order_manager, _, _ = _build_stack()
    response = order_manager.place_market_buy("DOGEUSDT", 221.93998390448816, score=0.7)
    assert response["orderId"] == 1
    assert client.orders[0]["origQty"] == "222"
    assert repository.trade_executions[0]["quantity"] == 222.0
    assert account_manager.get_open_orders("DOGEUSDT") == []


def test_order_manager_retries_once_after_precision_error() -> None:
    _, client, _, _, order_manager, _, _ = _build_stack()
    client.raise_precision_once = True
    response = order_manager.place_market_buy("DOGEUSDT", 221.93998390448816, score=0.7)
    assert response["orderId"] == 1
    assert client.create_order_calls == 2
    assert client.orders[0]["origQty"] == "222"


def test_live_trader_persists_normalized_quantity() -> None:
    repository = FakeRepository()
    client = FakeClient()
    test_dir = _make_local_test_dir("normalized_live_trader")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    rankings = pd.DataFrame([{"symbol": "DOGEUSDT", "final_score": 0.8, "price": 0.09047}])
    result = trader.process_live_signals(rankings)
    assert result[0]["status"] == "opened"
    assert result[0]["quantity"] == 166.0
    assert float(repository.get_open_position("DOGEUSDT")["quantity"]) == 166.0


def test_snapshot_uses_real_executed_price_and_updates_wallet() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["USDT"]["free"] = "20"
    client.next_fill_price = 0.0954
    test_dir = _make_local_test_dir("snapshot_after_buy")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    rankings = pd.DataFrame([{"symbol": "DOGEUSDT", "final_score": 0.8, "price": 0.09047}])

    result = trader.process_live_signals(rankings)
    snapshot = repository.get_latest_account_snapshot()

    assert result[0]["entry_price"] == 0.0954
    assert result[0]["quantity"] == 166.0
    assert snapshot is not None
    assert round(float(snapshot["free_balance"]), 4) == round(20.0 - (166.0 * 0.0954), 4)
    assert round(float(snapshot["total_balance"]), 4) == round(20.0, 4)
    assert snapshot["open_positions"] == 1
    assert snapshot["snapshot_json"]["portfolio"]["open_positions"] == 1


def test_close_position_uses_real_sell_price_and_updates_snapshot() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["USDT"]["free"] = "4.8"
    client.balances["DOGE"]["free"] = "200"
    client.next_fill_price = 0.105
    account_manager = AccountManager(client=client, repository=repository)
    risk_manager = RiskManager(account_manager=account_manager, repository=repository)
    order_manager = OrderManager(client=client, repository=repository, account_manager=account_manager)
    position_manager = PositionManager(repository=repository)
    stop_manager = StopManager(
        order_manager=order_manager,
        position_manager=position_manager,
        risk_manager=risk_manager,
        repository=repository,
    )
    repository.save_trade_execution(
        {
            "timestamp": datetime.now(UTC),
            "symbol": "DOGEUSDT",
            "side": "BUY",
            "quantity": 200.0,
            "entry_price": 0.0954,
            "exit_price": None,
            "stop_loss_price": 0.093492,
            "take_profit_price": 0.099216,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "status": "OPEN",
            "order_id": "1",
            "source": "test",
            "mode": "testnet",
            "confidence_score": 0.8,
            "notes": "",
            "created_at": datetime.now(UTC),
        }
    )
    position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=200.0,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=0.099216,
        trailing_stop_price=0.094446,
        order_id="1",
    )

    result = stop_manager.close_position("DOGEUSDT", 0.101, reason="take_profit")
    snapshot = repository.get_latest_account_snapshot()

    assert round(float(result["pnl"]), 6) == round((0.105 - 0.0954) * 199.0, 6)
    assert repository.trade_executions[0]["exit_price"] == 0.105
    assert repository.get_open_position("DOGEUSDT") is None
    assert snapshot is not None
    assert snapshot["open_positions"] == 0
    assert round(float(snapshot["free_balance"]), 4) == round(4.8 + (199.0 * 0.105), 4)


def test_paper_trader_uses_fixed_order_value_and_full_sell_quantity() -> None:
    repository = FakeRepository()
    trader = PaperTrader(repository=repository, initial_cash=1000.0)
    buy_trade = trader.buy("ADAUSDT", 0.26)
    assert buy_trade is not None
    assert round(float(buy_trade["order_value"]), 2) == 15.0
    assert round(float(buy_trade["quantity"]), 2) == 57.69

    sell_trade = trader.sell("ADAUSDT", 0.30)
    assert sell_trade is not None
    assert round(float(sell_trade["quantity"]), 2) == round(float(buy_trade["quantity"]), 2)


def test_get_safe_sell_quantity_caps_to_real_balance_and_applies_fee_buffer() -> None:
    client = FakeClient()
    client.balances["DOGE"]["free"] = "58.392"
    client.tickers["DOGEUSDT"] = "0.08547"

    result = get_safe_sell_quantity(client, "DOGEUSDT", requested_quantity=100.0, exchange_info=client.get_exchange_info())

    assert result["real_balance"] == 58.392
    assert result["requested_quantity"] == 100.0
    assert result["safe_quantity"] < result["real_balance"]
    assert result["normalized_quantity"] == 58.0
    assert round(result["notional"], 2) == 4.96
    assert result["validation_status"] == EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL


def test_order_manager_sell_returns_blocked_when_balance_is_below_local_quantity() -> None:
    repository, client, _, _, order_manager, position_manager, _ = _build_stack()
    client.balances["DOGE"]["free"] = "150"
    _seed_open_trade(repository, symbol="DOGEUSDT", quantity=200.0, entry_price=0.0954, order_id="doge-1")
    position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=200.0,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=0.099216,
        trailing_stop_price=0.094446,
        order_id="doge-1",
    )

    response = order_manager.place_market_sell("DOGEUSDT", 200.0, source="stop_loss")

    assert response.get("blocked") is not True
    assert float(response["executed_qty"]) == 149.0


def test_stop_manager_marks_dust_position_without_fatal_error() -> None:
    repository, client, _, _, order_manager, position_manager, stop_manager = _build_stack()
    client.balances["DOGE"]["free"] = "58.392"
    client.tickers["DOGEUSDT"] = "0.08547"
    _seed_open_trade(repository, symbol="DOGEUSDT", quantity=58.392, entry_price=0.0954, order_id="dust-1")
    position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=58.392,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=0.099216,
        trailing_stop_price=0.094446,
        order_id="dust-1",
    )

    result = stop_manager.close_position("DOGEUSDT", 0.08547, reason="take_profit")

    assert result["status"] == EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL
    assert repository.get_open_position("DOGEUSDT") is None
    assert repository.trade_executions[0]["status"] == EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL


def test_stop_manager_handles_binance_minus_2010_without_crashing() -> None:
    repository, client, _, _, order_manager, position_manager, stop_manager = _build_stack()
    client.balances["DOGE"]["free"] = "200"
    client.raise_insufficient_balance_once = True
    _seed_open_trade(repository, symbol="DOGEUSDT", quantity=200.0, entry_price=0.0954, order_id="doge-2010")
    position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=200.0,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=0.099216,
        trailing_stop_price=0.094446,
        order_id="doge-2010",
    )

    result = stop_manager.close_position("DOGEUSDT", 0.101, reason="stop_loss")

    assert result["status"] == EXECUTION_STATUS_BLOCKED_INSUFFICIENT_BALANCE
    assert repository.get_open_position("DOGEUSDT") is None


def test_sync_account_creates_local_orphan_when_balance_exists_only_on_binance() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["DOGE"]["free"] = "150"

    account_manager = AccountManager(client=client, repository=repository)
    summary = account_manager.sync_positions_with_binance()

    assert "DOGEUSDT" in summary["created_orphans"]
    assert repository.get_open_position("DOGEUSDT") is not None
    assert repository.trade_executions[0]["source"] == "binance_orphan_sync"


def test_sync_account_updates_local_quantity_when_real_balance_is_lower() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["DOGE"]["free"] = "120"
    repository.upsert_open_position(
        {
            "symbol": "DOGEUSDT",
            "quantity": 200.0,
            "entry_price": 0.0954,
            "current_price": 0.0954,
            "unrealized_pnl": 0.0,
            "stop_price": 0.093,
            "take_profit_price": 0.099,
            "trailing_stop_price": 0.094,
            "order_id": "sync-1",
            "mode": "testnet",
            "status": "OPEN",
            "opened_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )

    account_manager = AccountManager(client=client, repository=repository)
    summary = account_manager.sync_positions_with_binance()

    assert "DOGEUSDT" in summary["updated_positions"]
    assert float(repository.get_open_position("DOGEUSDT")["quantity"]) == 120.0


def test_monitor_positions_continues_after_single_symbol_failure() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["BTC"]["free"] = "0.2"
    test_dir = _make_local_test_dir("monitor_continue_after_error")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    _seed_open_trade(repository, symbol="BTCUSDT", quantity=0.2, entry_price=100.0, order_id="btc-1")
    _seed_open_trade(repository, symbol="DOGEUSDT", quantity=200.0, entry_price=0.0954, order_id="doge-2")
    trader.position_manager.register_open_position(
        symbol="BTCUSDT",
        quantity=0.2,
        entry_price=100.0,
        stop_price=98.0,
        take_profit_price=104.0,
        trailing_stop_price=99.0,
        order_id="btc-1",
    )
    trader.position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=200.0,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=0.099216,
        trailing_stop_price=0.094446,
        order_id="doge-2",
    )

    original_update = trader.stop_manager.update_trailing_stop

    def failing_update(symbol: str, current_price: float) -> dict[str, object]:
        if symbol == "BTCUSDT":
            raise RuntimeError("forced monitor failure")
        return original_update(symbol, current_price)

    trader.stop_manager.update_trailing_stop = failing_update  # type: ignore[method-assign]
    client.balances["DOGE"]["free"] = "200"
    client.next_fill_price = 0.105

    results = trader.monitor_positions({"BTCUSDT": 97.0, "DOGEUSDT": 0.105})

    assert any(item["symbol"] == "BTCUSDT" and item["status"] == "MONITOR_ERROR" for item in results)
    assert repository.get_open_position("DOGEUSDT") is None


def test_emergency_close_symbol_works_without_manual_quantity() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["DOGE"]["free"] = "58.392"
    client.tickers["DOGEUSDT"] = "0.08547"
    account_manager = AccountManager(client=client, repository=repository)
    risk_manager = RiskManager(account_manager=account_manager, repository=repository)
    order_manager = OrderManager(client=client, repository=repository, account_manager=account_manager)
    position_manager = PositionManager(repository=repository)
    stop_manager = StopManager(
        order_manager=order_manager,
        position_manager=position_manager,
        risk_manager=risk_manager,
        repository=repository,
    )

    result = stop_manager.emergency_close_symbol("DOGEUSDT", current_price=0.08547)
    validation = result["response"]["_validation"]

    assert result["status"] == EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL
    assert validation["real_balance"] == 58.392
    assert validation["normalized_quantity"] == 58.0


def test_get_safe_quantity_returns_invalid_step_size_when_exchange_filter_is_broken() -> None:
    _, client, _, _, order_manager, _, _ = _build_stack()
    client.exchange_info["symbols"].append(
        {
            "symbol": "HBARUSDT",
            "filters": [
                {"filterType": "LOT_SIZE", "stepSize": "0", "minQty": "1", "maxQty": "1000000"},
                {"filterType": "MIN_NOTIONAL", "minNotional": "5"},
            ],
        }
    )
    client.tickers["HBARUSDT"] = "0.10"
    client.balances["HBAR"] = {"free": "500", "locked": "0"}

    result = order_manager.get_safe_sell_quantity("HBARUSDT", 100.0, price=0.10)

    assert result["validation_status"] == "BLOCKED_INVALID_STEP_SIZE"


def test_process_live_signals_runs_auto_sync_before_and_after_buy() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.next_fill_price = 0.0954
    test_dir = _make_local_test_dir("auto_sync_before_after_buy")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")

    trader.process_live_signals(pd.DataFrame([{"symbol": "DOGEUSDT", "final_score": 0.8, "price": 0.09047}]))

    assert len(repository.account_snapshots) >= 3


def test_monitor_positions_closes_position_after_timeout_window() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["DOGE"]["free"] = "200"
    test_dir = _make_local_test_dir("timeout_close")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    _seed_open_trade(repository, symbol="DOGEUSDT", quantity=200.0, entry_price=0.0954, order_id="timeout-1")
    trader.position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=200.0,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=999.0,
        trailing_stop_price=0.09,
        order_id="timeout-1",
    )
    repository.open_positions["DOGEUSDT"]["opened_at"] = datetime.now(UTC) - timedelta(hours=7)

    results = trader.monitor_positions({"DOGEUSDT": 0.0955})

    assert any(item.get("reason") == "position_timeout" for item in results)
    assert repository.get_open_position("DOGEUSDT") is None


def test_partial_take_profit_reduces_position_and_keeps_position_open() -> None:
    repository = FakeRepository()
    client = FakeClient()
    client.balances["DOGE"]["free"] = "200"
    client.next_fill_price = 0.102
    test_dir = _make_local_test_dir("partial_take_profit")
    trader = LiveTrader(client=client, repository=repository, state_path=test_dir / "live_state.json")
    _seed_open_trade(repository, symbol="DOGEUSDT", quantity=200.0, entry_price=0.0954, order_id="partial-1")
    trader.position_manager.register_open_position(
        symbol="DOGEUSDT",
        quantity=200.0,
        entry_price=0.0954,
        stop_price=0.093492,
        take_profit_price=999.0,
        trailing_stop_price=0.09,
        order_id="partial-1",
    )

    results = trader.monitor_positions({"DOGEUSDT": 0.102})

    assert any(item.get("reason") == "partial_take_profit" for item in results)
    remaining = repository.get_open_position("DOGEUSDT")
    assert remaining is not None
    assert float(remaining["quantity"]) == 101.0
