from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.execution.account_manager import AccountManager
from alphascope.execution.compat import BinanceClient, sync_binance_time_or_raise
from alphascope.execution.logging_utils import build_component_logger
from alphascope.execution.order_manager import OrderManager
from alphascope.execution.order_sizing import OrderSizing
from alphascope.execution.position_manager import PositionManager
from alphascope.execution.risk_manager import RiskManager
from alphascope.execution.stop_manager import StopManager
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now


class LiveSignalRanking(BaseModel):
    symbol: str
    final_score: float = Field(ge=0, le=1)
    price: float = Field(gt=0)
    source: str = "ranking"


class LiveTrader:
    def __init__(
        self,
        *,
        client: Any | None = None,
        repository: StorageRepository | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.repository = repository or StorageRepository()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.logger = build_component_logger("live_trading", settings.live_trading_log_path)
        self.client = client or self._build_client()
        self._sync_client_clock()
        self.account_manager = AccountManager(client=self.client, repository=self.repository)
        self.risk_manager = RiskManager(account_manager=self.account_manager, repository=self.repository)
        self.position_manager = PositionManager(repository=self.repository)
        self.order_manager = OrderManager(
            client=self.client,
            repository=self.repository,
            alert_dispatcher=self.alert_dispatcher,
            account_manager=self.account_manager,
        )
        self.stop_manager = StopManager(
            order_manager=self.order_manager,
            position_manager=self.position_manager,
            risk_manager=self.risk_manager,
            repository=self.repository,
            alert_dispatcher=self.alert_dispatcher,
        )
        self.state_path = state_path or settings.live_trading_state_file
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_runtime_state()

    def execute_multi_agent_plan(
        self,
        *,
        symbol: str,
        side: str,
        price: float,
        final_score: float,
        execution_plan: dict[str, Any],
        supervisor: dict[str, Any],
        market_output: dict[str, Any] | None = None,
        news_output: dict[str, Any] | None = None,
        risk_output: dict[str, Any] | None = None,
        memory_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        symbol = symbol.upper()
        if price <= 0:
            return {"symbol": symbol, "status": "blocked", "reason": "invalid_price"}
        if final_score < settings.min_confidence_score:
            return {"symbol": symbol, "status": "blocked", "reason": "below_min_confidence"}
        if settings.live_trading_mode == "live" and settings.live_allowed_symbols_list and symbol not in settings.live_allowed_symbols_list:
            return {"symbol": symbol, "status": "blocked", "reason": "symbol_not_allowed"}
        self._sync_account_if_enabled(source=f"multi_agent_preflight_{symbol}")
        try:
            if side.upper() == "BUY":
                ranking_row = {
                    "symbol": symbol,
                    "final_score": final_score,
                    "price": price,
                    "close": price,
                    "confidence_score": float(supervisor.get("final_score", final_score) or final_score),
                    "ml_probability": float(market_output.get("score", 0.0) if market_output else 0.0),
                    "heuristic_score": float(market_output.get("score", final_score) if market_output else final_score),
                    "news_score": float(news_output.get("score", 0.0) if news_output else 0.0),
                    "relative_volume": float((market_output or {}).get("metadata", {}).get("relative_volume", 0.0)),
                    "volatility": float((market_output or {}).get("metadata", {}).get("volatility", 0.0)),
                    "market_regime": str((market_output or {}).get("metadata", {}).get("market_regime", "unknown")),
                    "source": "multi_agent",
                }
                results = self.process_live_signals(pd.DataFrame([ranking_row]))
                result = results[0] if results else {"symbol": symbol, "status": "blocked", "reason": "no_result"}
            else:
                position = self.repository.get_open_position(symbol)
                if position is None:
                    result = {"symbol": symbol, "status": "ignored", "reason": "position_not_found"}
                else:
                    result = self.stop_manager.close_position(symbol, price, reason="multi_agent_sell")
            self._sync_account_if_enabled(source=f"multi_agent_postflight_{symbol}")
            return result
        except Exception as exc:
            self.logger.exception("multi_agent_live_execution_failed symbol=%s", symbol)
            self.alert_dispatcher.critical_error(component="multi_agent_live_trader", error=str(exc), context={"symbol": symbol, "side": side, "mode": settings.live_trading_mode})
            self._sync_account_if_enabled(source=f"multi_agent_error_{symbol}")
            return {"symbol": symbol, "status": "blocked", "reason": str(exc)}

    def _initialize_runtime_state(self) -> None:
        open_positions = 0
        exposure_pct = 0.0
        try:
            self.account_manager.reconcile_persisted_positions()
            portfolio = self.account_manager.get_portfolio_summary()
            open_positions = int(portfolio["open_positions"])
            exposure_pct = float(self.account_manager.calculate_portfolio_exposure())
        except Exception as exc:
            self.logger.warning("startup_cleanup_failed error={}", str(exc))
        self._write_state(
            {
                "updated_at": utc_now().isoformat(),
                "mode": settings.live_trading_mode,
                "live_trading_enabled": settings.live_trading_enabled,
                "safe_mode": settings.live_mode_safe,
                "open_positions": open_positions,
                "exposure_pct": exposure_pct,
            }
        )

    def process_live_signals(self, rankings: pd.DataFrame) -> list[dict[str, Any]]:
        self._sync_account_if_enabled(source="process_live_signals_start")
        if rankings.empty:
            return []
        results: list[dict[str, Any]] = []
        if settings.live_trading_mode == "testnet":
            self.logger.warning("symbol=ALL score=- saldo=- quantidade=- preco=- pnl=- risco=- motivo=testnet_safe_mode_active")

        balance = self.account_manager.get_free_balance("USDT")
        order_floor = max(settings.default_order_usd, settings.order_size_usdt, settings.min_position_usd, settings.min_trade_value, settings.min_notional_usdt)
        minimum_required_balance = min(settings.min_balance_required, min(order_floor, settings.max_position_usd) + 1.0)
        if balance < minimum_required_balance:
            self.logger.warning("trade_blocked symbol=ALL reason=insufficient_balance balance={} minimum_required_balance={}", balance, minimum_required_balance)
            return [{"symbol": "ALL", "status": "blocked", "reason": "insufficient_balance", "balance": balance, "minimum_required_balance": minimum_required_balance}]
        for row in rankings.itertuples(index=False):
            try:
                final_score = float(getattr(row, "final_score", getattr(row, "score", 0.0)))
                symbol = str(getattr(row, "symbol")).upper()
                price = float(getattr(row, "price", getattr(row, "close", 0.0)) or 0.0)
                if settings.live_trading_mode == "live" and settings.live_allowed_symbols_list and symbol not in settings.live_allowed_symbols_list:
                    self.logger.warning("trade_blocked symbol={} reason=symbol_not_allowed", symbol)
                    results.append({"symbol": symbol, "status": "blocked", "reason": "symbol_not_allowed"})
                    continue
                if final_score < settings.min_confidence_score or price <= 0:
                    continue
                if float(getattr(row, "confidence_score", final_score)) < settings.min_model_confidence:
                    self.logger.warning("trade_blocked symbol={} reason=min_model_confidence", symbol)
                    results.append({"symbol": symbol, "status": "blocked", "reason": "min_model_confidence"})
                    continue

                self._sync_account_if_enabled(source=f"before_symbol_{symbol}")
                signal = LiveSignalRanking(symbol=symbol, final_score=final_score, price=price)
                if self.risk_manager.is_symbol_open(signal.symbol):
                    continue
                balance = self.account_manager.get_free_balance("USDT")
                sizing = self.risk_manager.calculate_order_size(
                    balance=balance,
                    price=signal.price,
                    symbol=signal.symbol,
                    exchange_info=self.order_manager.get_exchange_info(),
                )
                self.logger.info(
                    "trade_attempt symbol={} score={} mode={} trader={} price={} calculated_order_value={} calculated_quantity={} min_notional_required={} final_quantity={}",
                    signal.symbol,
                    signal.final_score,
                    settings.live_trading_mode,
                    self.__class__.__name__,
                    signal.price,
                    sizing.order_value_usd,
                    sizing.calculated_quantity,
                    sizing.min_notional_required,
                    sizing.final_quantity,
                )
                if self._append_sizing_block(signal.symbol, sizing, results):
                    continue

                approved, reason = self.risk_manager.can_open_position(
                    signal.symbol,
                    signal_score=signal.final_score,
                    price=signal.price,
                    quantity=sizing.final_quantity,
                )
                if not approved:
                    normalized_reason = self._normalize_block_reason(reason)
                    self.logger.warning("trade_blocked symbol={} reason={}", signal.symbol, normalized_reason)
                    results.append({"symbol": signal.symbol, "status": "blocked", "reason": normalized_reason})
                    continue

                order = self.order_manager.place_market_buy(
                    signal.symbol,
                    sizing.final_quantity,
                    score=signal.final_score,
                    source=signal.source,
                )
            except Exception as exc:
                normalized_reason = self._normalize_block_reason(str(exc))
                symbol = str(getattr(row, "symbol", "UNKNOWN")).upper()
                self.logger.warning("trade_blocked symbol={} reason={}", symbol, normalized_reason)
                self.alert_dispatcher.dispatch_raw(
                    "run_loop_continue",
                    "Run loop continuing after error",
                    "\n".join([f"symbol: {symbol}", f"error: {str(exc)}", "run_loop: continuing"]),
                    {"symbol": symbol, "error": str(exc)},
                )
                self._sync_account_if_enabled(source=f"after_error_{symbol}")
                results.append({"symbol": symbol, "status": "blocked", "reason": normalized_reason})
                continue

            executed_price = float(order.get("executed_price") or signal.price or 0.0)
            executed_quantity = float(order.get("executed_qty") or order.get("_normalized_quantity") or sizing.final_quantity)
            order_value = float(order.get("executed_value") or (executed_quantity * executed_price))
            stop_loss = self.risk_manager.calculate_stop_loss(executed_price)
            take_profit = self.risk_manager.calculate_take_profit(executed_price)
            trailing_stop = self.risk_manager.calculate_trailing_stop(executed_price)
            position = self.position_manager.register_open_position(
                symbol=signal.symbol,
                quantity=executed_quantity,
                entry_price=executed_price,
                stop_price=stop_loss,
                take_profit_price=take_profit,
                trailing_stop_price=trailing_stop,
                order_id=str(order["orderId"]),
            )
            self.repository.open_trade_history(
                {
                    "trade_id": str(order["orderId"]),
                    "order_id": str(order["orderId"]),
                    "symbol": signal.symbol,
                    "timeframe": settings.default_interval,
                    "side": "BUY",
                    "mode": settings.live_trading_mode,
                    "status": "OPEN",
                    "entry_time": utc_now(),
                    "entry_price": executed_price,
                    "quantity": executed_quantity,
                    "order_size_usdt": order_value,
                    "fees_paid": 0.0,
                    "ranking_score": signal.final_score,
                    "confidence_score": float(getattr(row, "confidence_score", final_score)),
                    "ml_score": float(getattr(row, "ml_probability", getattr(row, "ml_score", 0.0))),
                    "heuristic_score": float(getattr(row, "heuristic_score", final_score)),
                    "news_score": float(getattr(row, "news_score", 0.0)),
                    "volatility": float(getattr(row, "volatility", 0.0)),
                    "volume_ratio": float(getattr(row, "relative_volume", 0.0)),
                    "trend_direction": "up" if final_score >= settings.rank_buy_threshold else "sideways",
                    "reason_opened": signal.source,
                    "notes_json": {
                        "ranking_source": signal.source,
                        "market_regime": getattr(row, "market_regime", "unknown"),
                    },
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                }
            )
            self.logger.info("order_response={}", order)
            self.logger.info("executed_price={} executed_qty={}", executed_price, executed_quantity)
            self.logger.info("position_saved={}", position)
            self.repository.update_trade_execution(
                str(order["orderId"]),
                {"stop_loss_price": stop_loss, "take_profit_price": take_profit, "notes": "position_opened"},
            )
            snapshot = self.account_manager.generate_snapshot()
            portfolio = dict(snapshot["snapshot_json"]["portfolio"])
            result = {
                "symbol": signal.symbol,
                "status": "opened",
                "score": signal.final_score,
                "quantity": executed_quantity,
                "entry_price": executed_price,
                "stop_loss_price": stop_loss,
                "take_profit_price": take_profit,
                "trailing_stop_price": trailing_stop,
                "order_id": order["orderId"],
                "mode": settings.live_trading_mode,
            }
            self.logger.info(
                "trade_executed symbol={} order_side=BUY order_value={} final_quantity={} trader={} price={} score={}",
                signal.symbol,
                order_value,
                executed_quantity,
                self.__class__.__name__,
                executed_price,
                signal.final_score,
            )
            self.logger.info(
                "Trade opened LIVE\nsymbol: {}\nside: BUY\nqty: {:.6f}\nprice: {:.6f}\nscore: {:.4f}",
                signal.symbol,
                executed_quantity,
                executed_price,
                signal.final_score,
            )
            self.logger.info(
                "Post-trade portfolio\nequity: {:.4f}\ncash: {:.4f}\nopen positions: {}\nrealized pnl: {:.2f}\nunrealized pnl: {:.2f}",
                float(portfolio["equity"]),
                float(portfolio["cash"]),
                int(portfolio["open_positions"]),
                float(portfolio["realized_pnl"]),
                float(portfolio["unrealized_pnl"]),
            )
            results.append(result)
            balance = self.account_manager.get_free_balance("USDT")
            self._sync_account_if_enabled(source=f"after_buy_{signal.symbol}")

        self._write_state(
            {
                "updated_at": utc_now().isoformat(),
                "last_processed": len(results),
                "open_positions": len(self.position_manager.list_open_positions()),
            }
        )
        return results

    def monitor_positions(self, current_prices: dict[str, float]) -> list[dict[str, object]]:
        self._sync_account_if_enabled(source="monitor_positions_start")
        results: list[dict[str, object]] = []
        for position in self.position_manager.list_open_positions():
            symbol = str(position["symbol"])
            try:
                current_price = float(current_prices.get(symbol, position["current_price"]))
                updated = self.stop_manager.update_trailing_stop(symbol, current_price)
                trailing_stop_price = float(updated.get("trailing_stop_price") or 0.0)
                if settings.enable_break_even and current_price >= float(position["entry_price"]) * (1.0 + settings.break_even_trigger_pct):
                    break_even_stop = float(position["entry_price"]) * (1.0 + settings.break_even_offset_pct)
                    if break_even_stop > float(updated.get("stop_price", 0.0) or 0.0):
                        self.position_manager.update_stops(symbol, stop_price=break_even_stop)
                if self.stop_manager.check_stop_loss_hit(symbol, current_price):
                    results.append(self.stop_manager.close_position(symbol, current_price, reason="stop_loss"))
                elif self.stop_manager.check_take_profit_hit(symbol, current_price):
                    results.append(self.stop_manager.close_position(symbol, current_price, reason="take_profit"))
                elif trailing_stop_price > 0 and current_price <= trailing_stop_price:
                    results.append(self.stop_manager.close_position(symbol, current_price, reason="trailing_stop"))
                elif settings.enable_partial_take_profit and current_price >= float(position["entry_price"]) * (1.0 + settings.partial_take_profit_pct):
                    partial_qty = float(position["quantity"]) * settings.partial_take_profit_size
                    if partial_qty > 0:
                        results.append(self.stop_manager.close_position(symbol, current_price, reason="partial_take_profit", requested_quantity=partial_qty))
            except Exception as exc:
                self.logger.error(
                    "symbol={} local_quantity={} real_balance=- requested_quantity=- safe_quantity=- normalized_quantity=- price={} notional=- min_notional=- final_status=MONITOR_ERROR motivo={} source=monitor_positions order_id={} pnl=- risco=- saldo={}",
                    symbol,
                    float(position.get("quantity", 0.0) or 0.0),
                    float(current_prices.get(symbol, position.get("current_price", 0.0)) or 0.0),
                    str(exc),
                    str(position.get("order_id") or "-"),
                    self.account_manager.get_free_balance("USDT"),
                )
                self.alert_dispatcher.dispatch_raw(
                    "position_monitor_error",
                    "Position monitoring error",
                    "\n".join(
                        [
                            f"symbol: {symbol}",
                            f"error: {str(exc)}",
                            "action: skipping_symbol",
                            "run_loop: continuing",
                        ]
                    ),
                    {
                        "symbol": symbol,
                        "error": str(exc),
                        "position": position,
                    },
                )
                results.append({"symbol": symbol, "status": "MONITOR_ERROR", "reason": str(exc)})
        results.extend(self.stop_manager.close_expired_positions(current_prices))
        return results

    def sync_account(self) -> dict[str, Any]:
        snapshot = self.account_manager.generate_snapshot()
        self._write_state(
            {
                "updated_at": utc_now().isoformat(),
                "last_account_sync": snapshot["timestamp"].isoformat(),
            }
        )
        return snapshot

    def emergency_close_all(self, current_prices: dict[str, float]) -> list[dict[str, object]]:
        self._write_state({"updated_at": utc_now().isoformat(), "emergency_close_requested": True})
        return self.stop_manager.emergency_close_all(current_prices)

    def _write_state(self, payload: dict[str, Any]) -> None:
        state: dict[str, Any] = {}
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state.update(payload)
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    @staticmethod
    def _build_client() -> BinanceClient:
        client = BinanceClient(
            settings.binance_api_key,
            settings.binance_api_secret,
            testnet=settings.live_trading_mode == "testnet",
        )
        if settings.live_trading_mode == "testnet":
            client.API_URL = settings.live_binance_base_url.rstrip("/") + "/"
        return client

    def _sync_client_clock(self) -> int:
        return sync_binance_time_or_raise(
            self.client,
            logger=self.logger,
            max_allowed_drift_ms=5000 if settings.live_trading_mode == "live" else None,
        )

    @staticmethod
    def _normalize_block_reason(reason: str) -> str:
        normalized = str(reason).strip().lower()
        aliases = {
            "symbol_already_open": "already_has_open_position",
            "signal_score_below_minimum": "confidence_below_threshold",
            "order_blocked:_insufficient_balance": "insufficient_balance",
            "order blocked: insufficient_balance": "insufficient_balance",
        }
        return aliases.get(normalized, normalized.replace(" ", "_"))

    def _append_sizing_block(self, symbol: str, sizing: OrderSizing, results: list[dict[str, Any]]) -> bool:
        if not sizing.blocked_reason:
            return False
        self.logger.warning("trade_blocked symbol={} reason={}", symbol, sizing.blocked_reason)
        results.append({"symbol": symbol, "status": "blocked", "reason": sizing.blocked_reason})
        return True

    def _sync_account_if_enabled(self, *, source: str) -> None:
        if not settings.auto_sync_account:
            return
        snapshot = self.account_manager.generate_snapshot()
        self.logger.info(
            "symbol=ALL local_quantity=- real_balance={} requested_quantity=- safe_quantity=- normalized_quantity=- price=- notional=- min_notional=- final_status=SYNC_COMPLETED motivo={} source={} order_id=- pnl=- risco={} saldo={}",
            snapshot["free_balance"],
            source,
            source,
            snapshot["exposure_pct"],
            snapshot["free_balance"],
        )
