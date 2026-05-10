from __future__ import annotations

import pandas as pd
from datetime import datetime
from typing import Any

from alphascope.alerts import AlertDispatcher
from alphascope.config.settings import settings
from alphascope.execution.compat import (
    EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL,
    EXECUTION_STATUS_DUST_POSITION,
    EXECUTION_STATUS_CLOSED_ORPHAN,
    EXECUTION_STATUS_OPEN,
    call_authenticated_binance,
    get_asset_balance_from_account,
    get_safe_sell_quantity,
    infer_base_asset,
)
from alphascope.execution.logging_utils import build_component_logger
from alphascope.storage.repositories import StorageRepository
from alphascope.utils.time import utc_now


class AccountManager:
    def __init__(
        self,
        client: Any,
        repository: StorageRepository | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self.client = client
        self.repository = repository or StorageRepository()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.logger = build_component_logger("account_manager", settings.account_manager_log_path)

    @staticmethod
    def _max_allowed_clock_drift_ms() -> int | None:
        return 5000 if settings.live_trading_mode == "live" else None

    def get_account_info(self) -> dict[str, Any]:
        return dict(
            call_authenticated_binance(
                self.client,
                self.client.get_account,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
            )
        )

    def get_asset_balance(self, asset: str) -> dict[str, float]:
        balances = self.get_account_info().get("balances", [])
        for balance in balances:
            if str(balance.get("asset", "")).upper() == asset.upper():
                return {
                    "free": float(balance.get("free", 0.0)),
                    "locked": float(balance.get("locked", 0.0)),
                    "total": float(balance.get("free", 0.0)) + float(balance.get("locked", 0.0)),
                }
        return {"free": 0.0, "locked": 0.0, "total": 0.0}

    def get_free_balance(self, asset: str = "USDT") -> float:
        return self.get_asset_balance(asset)["free"]

    def get_total_balance(self, asset: str = "USDT") -> float:
        return self.get_asset_balance(asset)["total"]

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        if symbol:
            return list(
                call_authenticated_binance(
                    self.client,
                    self.client.get_open_orders,
                    symbol=symbol.upper(),
                    logger=self.logger,
                    sync_before=True,
                    max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
                )
            )
        return list(
            call_authenticated_binance(
                self.client,
                self.client.get_open_orders,
                logger=self.logger,
                sync_before=True,
                max_allowed_drift_ms=self._max_allowed_clock_drift_ms(),
            )
        )

    def get_open_positions(self, *, reconcile: bool = True) -> list[dict[str, Any]]:
        frame = self._load_valid_positions_frame(reconcile=reconcile)
        if frame.empty:
            return []
        return frame.to_dict(orient="records")

    def calculate_portfolio_exposure(self, *, reconcile: bool = True) -> float:
        open_positions = self._load_valid_positions_frame(reconcile=reconcile)
        position_notional = self._calculate_open_positions_notional(open_positions)
        equity = self.get_free_balance("USDT") + position_notional
        if open_positions.empty or equity <= 0:
            self.logger.info("portfolio_exposure=0.0")
            self.logger.info("open_positions=0")
            return 0.0
        exposure = float(position_notional / equity)
        self.logger.info("portfolio_exposure={}", position_notional)
        self.logger.info("open_positions={}", len(open_positions))
        self.logger.info("symbol=ALL saldo={:.6f} risco=exposure exposicao={:.6f}", equity, exposure)
        return exposure

    def generate_snapshot(self, *, reconcile: bool = True) -> dict[str, Any]:
        open_positions = self.get_open_positions(reconcile=reconcile)
        open_orders = self.get_open_orders()
        portfolio = self.get_portfolio_summary(reconcile=reconcile)
        exposure_pct = self.calculate_portfolio_exposure(reconcile=reconcile)
        snapshot = {
            "timestamp": utc_now(),
            "mode": settings.live_trading_mode,
            "total_balance": portfolio["equity"],
            "free_balance": portfolio["cash"],
            "locked_balance": 0.0,
            "exposure_pct": exposure_pct,
            "open_positions": portfolio["open_positions"],
            "open_orders": len(open_orders),
            "snapshot_json": {
                "account": self.get_account_info(),
                "open_positions": open_positions,
                "open_orders": open_orders,
                "portfolio": portfolio,
            },
        }
        self.repository.save_account_snapshot(snapshot)
        self.logger.info(
            "symbol=ALL saldo={:.6f} quantidade={} preco=- pnl=- risco={:.6f} motivo=snapshot",
            portfolio["equity"],
            portfolio["open_positions"],
            exposure_pct,
        )
        return snapshot

    def get_portfolio_summary(self, *, reconcile: bool = True) -> dict[str, float | int]:
        open_positions = self._load_valid_positions_frame(reconcile=reconcile)
        cash = self.get_free_balance("USDT")
        exposure = self._calculate_open_positions_notional(open_positions)
        unrealized_pnl = self._calculate_unrealized_pnl(open_positions)
        realized_pnl = float((self.repository.get_daily_performance() or {}).get("realized_pnl", 0.0))
        return {
            "cash": cash,
            "equity": cash + exposure,
            "position_notional": exposure,
            "exposure": exposure,
            "open_positions": len(open_positions),
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
        }

    def reconcile_persisted_positions(self) -> list[str]:
        summary = self.sync_positions_with_binance()
        return summary["closed_orphans"]

    def sync_positions_with_binance(self) -> dict[str, list[str]]:
        frame = self.repository.get_open_positions()
        account_info = self.get_account_info()
        exchange_symbols = self._build_exchange_symbol_map()
        closed_orphans: list[str] = []
        created_orphans: list[str] = []
        updated_positions: list[str] = []
        dust_positions: list[str] = []
        open_trade_symbols = {
            str(trade.get("symbol", "")).upper()
            for trade in (self.repository.get_trade_executions(status=EXECUTION_STATUS_OPEN).to_dict(orient="records"))
            if str(trade.get("symbol", "")).strip()
        }
        local_symbols = {
            str(position.get("symbol", "")).upper()
            for position in (frame.to_dict(orient="records") if not frame.empty else [])
            if str(position.get("symbol", "")).strip()
        }
        local_symbols.update(open_trade_symbols)

        for position in frame.to_dict(orient="records") if not frame.empty else []:
            symbol = str(position.get("symbol", "")).upper()
            if not symbol:
                continue
            base_asset = infer_base_asset(symbol)
            real_balance = get_asset_balance_from_account(account_info, base_asset)["free"]
            local_quantity = float(position.get("quantity", 0.0) or 0.0)
            current_price = float(position.get("current_price", 0.0) or 0.0)
            safe_sell = get_safe_sell_quantity(
                self.client,
                symbol,
                local_quantity,
                exchange_info=dict(self.client.get_exchange_info()),
                price=current_price,
                account_info=account_info,
            )
            if real_balance <= 0:
                order_id = str(position.get("order_id") or "")
                if order_id:
                    try:
                        self.repository.update_trade_execution(order_id, {"status": EXECUTION_STATUS_CLOSED_ORPHAN, "notes": "binance_balance_zero"})
                    except Exception:
                        pass
                self.repository.close_open_position(symbol, reason=EXECUTION_STATUS_CLOSED_ORPHAN)
                closed_orphans.append(symbol)
                self.logger.warning(
                    "symbol={} local_quantity={} real_balance={} requested_quantity=- safe_quantity=- normalized_quantity=- price=- notional=- min_notional=- final_status={} motivo=local_position_without_binance_balance source=account_sync order_id={} pnl=- risco=- saldo={}",
                    symbol,
                    local_quantity,
                    real_balance,
                    EXECUTION_STATUS_CLOSED_ORPHAN,
                    order_id or "-",
                    self.get_free_balance("USDT"),
                )
                self.alert_dispatcher.dispatch_raw(
                    "orphan_position",
                    "Orphan position removed",
                    "\n".join(
                        [
                            f"symbol: {symbol}",
                            f"local_quantity: {local_quantity:.8f}",
                            f"real_balance: {real_balance:.8f}",
                            f"status: {EXECUTION_STATUS_CLOSED_ORPHAN}",
                            "run_loop: continuing",
                        ]
                    ),
                    {"symbol": symbol, "local_quantity": local_quantity, "real_balance": real_balance, "status": EXECUTION_STATUS_CLOSED_ORPHAN},
                )
                continue
            if real_balance < local_quantity:
                position["quantity"] = real_balance
                position["updated_at"] = utc_now()
                self.repository.upsert_open_position(position)
                updated_positions.append(symbol)
                self.logger.warning(
                    "symbol={} local_quantity={} real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional=- final_status={} motivo=local_quantity_synced_to_binance source=account_sync order_id={} pnl={} risco=- saldo={}",
                    symbol,
                    local_quantity,
                    real_balance,
                    local_quantity,
                    real_balance,
                    real_balance,
                    float(position.get("current_price", 0.0) or 0.0),
                    real_balance * float(position.get("current_price", 0.0) or 0.0),
                    EXECUTION_STATUS_OPEN,
                    str(position.get("order_id") or "-"),
                    float(position.get("unrealized_pnl", 0.0) or 0.0),
                    self.get_free_balance("USDT"),
                )
            if safe_sell["validation_status"] in {EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL, EXECUTION_STATUS_DUST_POSITION}:
                order_id = str(position.get("order_id") or "")
                if order_id:
                    try:
                        self.repository.update_trade_execution(
                            order_id,
                            {"status": EXECUTION_STATUS_DUST_POSITION, "notes": safe_sell["validation_reason"]},
                        )
                    except Exception:
                        pass
                self.repository.close_open_position(symbol, reason=EXECUTION_STATUS_DUST_POSITION)
                dust_positions.append(symbol)
                self.alert_dispatcher.dispatch_raw(
                    "dust_position",
                    "Dust position detected",
                    "\n".join(
                        [
                            f"symbol: {symbol}",
                            f"real_balance: {real_balance:.8f}",
                            f"price: {float(safe_sell.get('price', current_price) or 0.0):.8f}",
                            f"notional: {float(safe_sell.get('notional', 0.0)):.8f}",
                            f"min_notional: {float(safe_sell.get('min_notional', 0.0)):.8f}",
                            "action: removed_from_active_loop",
                        ]
                    ),
                    {"symbol": symbol, "status": EXECUTION_STATUS_DUST_POSITION, **safe_sell},
                )
                continue

        for asset_balance in account_info.get("balances", []):
            asset = str(asset_balance.get("asset", "")).upper()
            free_balance = float(asset_balance.get("free", 0.0) or 0.0)
            if asset in {"", "USDT", "FDUSD", "USDC", "BUSD", "BRL"} or free_balance <= 0:
                continue
            symbol = exchange_symbols.get(asset)
            if not symbol or symbol in local_symbols:
                continue
            current_price = self._get_symbol_price(symbol)
            safe_sell = get_safe_sell_quantity(
                self.client,
                symbol,
                free_balance,
                exchange_info=dict(self.client.get_exchange_info()),
                price=current_price,
                account_info=account_info,
            )
            if safe_sell["validation_status"] in {EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL, EXECUTION_STATUS_DUST_POSITION}:
                dust_positions.append(symbol)
                self.alert_dispatcher.dispatch_raw(
                    "dust_position",
                    "Dust balance ignored",
                    "\n".join(
                        [
                            f"symbol: {symbol}",
                            f"real_balance: {free_balance:.8f}",
                            f"notional: {float(safe_sell.get('notional', 0.0)):.8f}",
                            f"min_notional: {float(safe_sell.get('min_notional', 0.0)):.8f}",
                            "action: skip_orphan_creation",
                        ]
                    ),
                    {"symbol": symbol, "status": safe_sell["validation_status"], **safe_sell},
                )
                continue
            order_id = f"ORPHAN-{symbol}-{int(utc_now().timestamp())}"
            self.repository.upsert_open_position(
                {
                    "symbol": symbol,
                    "quantity": free_balance,
                    "entry_price": current_price,
                    "current_price": current_price,
                    "unrealized_pnl": 0.0,
                    "stop_price": current_price * (1.0 - settings.stop_loss_pct),
                    "take_profit_price": current_price * (1.0 + settings.take_profit_pct),
                    "trailing_stop_price": current_price * (1.0 - settings.trailing_stop_pct),
                    "order_id": order_id,
                    "mode": settings.live_trading_mode,
                    "status": EXECUTION_STATUS_OPEN,
                    "opened_at": utc_now(),
                    "updated_at": utc_now(),
                }
            )
            self.repository.save_trade_execution(
                {
                    "timestamp": utc_now(),
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": free_balance,
                    "entry_price": current_price,
                    "exit_price": None,
                    "stop_loss_price": current_price * (1.0 - settings.stop_loss_pct),
                    "take_profit_price": current_price * (1.0 + settings.take_profit_pct),
                    "pnl": 0.0,
                    "pnl_pct": 0.0,
                    "status": EXECUTION_STATUS_OPEN,
                    "order_id": order_id,
                    "source": "binance_orphan_sync",
                    "mode": settings.live_trading_mode,
                    "confidence_score": 0.0,
                    "notes": "created_from_binance_balance",
                    "created_at": utc_now(),
                }
            )
            created_orphans.append(symbol)
            self.logger.warning(
                "symbol={} local_quantity=0 real_balance={} requested_quantity={} safe_quantity={} normalized_quantity={} price={} notional={} min_notional=- final_status={} motivo=created_local_orphan_from_binance source=account_sync order_id={} pnl=0 risco=- saldo={}",
                symbol,
                free_balance,
                free_balance,
                free_balance,
                free_balance,
                current_price,
                free_balance * current_price,
                EXECUTION_STATUS_OPEN,
                order_id,
                self.get_free_balance("USDT"),
            )
            self.alert_dispatcher.dispatch_raw(
                "orphan_position",
                "Orphan position detected",
                "\n".join(
                    [
                        f"symbol: {symbol}",
                        f"real_balance: {free_balance:.8f}",
                        f"price: {current_price:.8f}",
                        f"status: {EXECUTION_STATUS_OPEN}",
                        "action: created_local_position",
                    ]
                ),
                {"symbol": symbol, "status": EXECUTION_STATUS_OPEN, "real_balance": free_balance, "price": current_price, "order_id": order_id},
            )

        summary = {
            "closed_orphans": closed_orphans,
            "created_orphans": created_orphans,
            "updated_positions": updated_positions,
            "dust_positions": dust_positions,
        }
        self.alert_dispatcher.dispatch_raw(
            "sync_completed",
            "Account sync completed",
            "\n".join(
                [
                    f"closed_orphans: {len(closed_orphans)}",
                    f"created_orphans: {len(created_orphans)}",
                    f"updated_positions: {len(updated_positions)}",
                    f"dust_positions: {len(dust_positions)}",
                ]
            ),
            summary,
        )
        return summary

    def _load_valid_positions_frame(self, *, reconcile: bool) -> pd.DataFrame:
        if reconcile:
            self.reconcile_persisted_positions()
        frame = self.repository.get_open_positions()
        loaded_positions = frame.to_dict(orient="records") if not frame.empty else []
        self.logger.info("loaded_positions={}", loaded_positions)
        valid_positions = [position for position in loaded_positions if self.repository.is_valid_open_position(position)]
        self.logger.info("valid_positions={}", valid_positions)
        if not valid_positions:
            return pd.DataFrame(columns=list(frame.columns) if not frame.empty else [])
        return pd.DataFrame(valid_positions)

    def _account_has_asset(self, asset: str) -> bool:
        balances = self.get_account_info().get("balances", [])
        return any(str(balance.get("asset", "")).upper() == asset.upper() for balance in balances)

    def _build_exchange_symbol_map(self) -> dict[str, str]:
        exchange_info = dict(self.client.get_exchange_info())
        symbol_map: dict[str, str] = {}
        for symbol_info in exchange_info.get("symbols", []):
            symbol = str(symbol_info.get("symbol", "")).upper()
            if not symbol.endswith("USDT"):
                continue
            base_asset = str(symbol_info.get("baseAsset", infer_base_asset(symbol))).upper()
            if base_asset and base_asset not in symbol_map:
                symbol_map[base_asset] = symbol
        return symbol_map

    def _get_symbol_price(self, symbol: str) -> float:
        try:
            return float(self.client.get_symbol_ticker(symbol=symbol)["price"])
        except Exception:
            position = self.repository.get_open_position(symbol)
            if position is not None:
                return float(position.get("current_price", position.get("entry_price", 0.0)) or 0.0)
            return 0.0

    @staticmethod
    def _calculate_open_positions_notional(open_positions: Any) -> float:
        if getattr(open_positions, "empty", True):
            return 0.0
        return float((open_positions["quantity"].astype(float) * open_positions["current_price"].astype(float)).sum())

    @staticmethod
    def _calculate_unrealized_pnl(open_positions: Any) -> float:
        if getattr(open_positions, "empty", True):
            return 0.0
        return float(open_positions["unrealized_pnl"].astype(float).sum())
