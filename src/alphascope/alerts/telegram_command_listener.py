from __future__ import annotations

import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import requests

from alphascope.alerts.telegram_command_templates import (
    api_status_message,
    multi_agent_decision_message,
    multi_agent_status_message,
    portfolio_message,
    positions_message,
    profit_message,
    ranking_message,
    risk_message,
    status_message,
)
from alphascope.alerts.telegram_notifier import TelegramNotifier
from alphascope.alerts.telegram_router import dispatch_command as dispatch_telegram_command
from alphascope.agents.runtime import MultiAgentRuntime
from alphascope.config.runtime_updates import RuntimeSettingsManager
from alphascope.config.settings import settings
from alphascope.core.logger import get_logger
from alphascope.execution.live_trader import LiveTrader
from alphascope.execution.paper_trader import PaperTrader
from alphascope.monitoring.runtime_status import RuntimeStatusService
from alphascope.storage.repositories import StorageRepository

logger = get_logger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


@dataclass(slots=True)
class TelegramCommandContext:
    chat_id: str
    text: str
    update_id: int


class TelegramCommandListener:
    def __init__(
        self,
        *,
        repository: StorageRepository | None = None,
        notifier: TelegramNotifier | None = None,
        runtime_status: RuntimeStatusService | None = None,
        settings_manager: RuntimeSettingsManager | None = None,
        continuous_pipeline: Any | None = None,
        get_func: Callable[..., Any] | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.repository = repository or StorageRepository()
        self.notifier = notifier or TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            enabled=settings.telegram_enabled or settings.enable_telegram_alerts,
            parse_mode=settings.telegram_parse_mode,
            timeout=settings.request_timeout,
            retries=settings.request_retries,
        )
        self.runtime_status = runtime_status or RuntimeStatusService(repository=self.repository)
        self.settings_manager = settings_manager or RuntimeSettingsManager()
        self.continuous_pipeline = continuous_pipeline
        self._get_func = get_func or requests.get
        self._sleep_func = sleep_func or time.sleep
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset = 0
        self._bootstrapped = False
        self._processed_ids: deque[int] = deque(maxlen=2048)
        self._processed_lookup: set[int] = set()
        self._confirmation_state: dict[str, str] = {}

    def start(self) -> None:
        if not (settings.telegram_enabled or settings.enable_telegram_alerts):
            logger.info("Telegram command listener skipped because telegram is disabled")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="alphascope-telegram-command-listener", daemon=True)
        self._thread.start()
        logger.info("Telegram command listener started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        close = getattr(self.notifier, "close", None)
        if callable(close):
            close()
        logger.info("Telegram command listener stopped")

    def poll_updates(self) -> int:
        if not settings.telegram_bot_token:
            return 0
        updates = self._fetch_updates()
        if not updates:
            return 0
        if not self._bootstrapped:
            self._offset = max(int(item["update_id"]) for item in updates) + 1
            self._bootstrapped = True
            logger.info("Telegram command listener bootstrapped offset=%s skipped_updates=%s", self._offset, len(updates))
            return 0

        processed = 0
        for update in updates:
            update_id = int(update.get("update_id", 0))
            self._offset = max(self._offset, update_id + 1)
            if update_id in self._processed_lookup:
                continue
            self._remember_processed(update_id)
            processed += self.handle_message(update)
        return processed

    def handle_message(self, update: dict[str, Any]) -> int:
        message = update.get("message") or update.get("edited_message") or {}
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = str(message.get("text", "")).strip()
        if not text or not chat_id:
            return 0
        if settings.telegram_chat_id and chat_id != str(settings.telegram_chat_id):
            return 0
        context = TelegramCommandContext(chat_id=chat_id, text=text, update_id=int(update["update_id"]))
        logger.info("Telegram command received update_id=%s chat_id=%s text=%s", context.update_id, chat_id, text)
        try:
            reply = self.handle_command(context)
            if reply:
                self.send_reply(chat_id, reply)
            logger.info("Telegram command executed update_id=%s chat_id=%s", context.update_id, chat_id)
        except Exception as exc:
            logger.exception("Telegram command failed update_id=%s chat_id=%s", context.update_id, chat_id)
            self.send_reply(chat_id, f"Falha ao executar comando: {exc}")
        return 1

    def handle_command(self, context: TelegramCommandContext) -> str:
        return dispatch_telegram_command(self, context)

    def send_reply(self, chat_id: str, message: str) -> None:
        result = self.notifier.send_message(message, chat_id=chat_id)
        if result.delivered:
            logger.info("Telegram reply sent chat_id=%s chunks=%s", chat_id, result.chunks_sent)
            return
        logger.warning("Telegram reply failed chat_id=%s error=%s", chat_id, result.error)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_updates()
            except Exception as exc:
                logger.warning("Telegram polling failure: %s", exc)
            self._sleep_func(max(float(settings.telegram_poll_seconds), 0.25))

    def _fetch_updates(self) -> list[dict[str, Any]]:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
        last_error: Exception | None = None
        for attempt in range(1, max(settings.request_retries, 1) + 1):
            try:
                response = self._get_func(
                    url,
                    params={"timeout": max(1, min(settings.request_timeout, 10)), "offset": self._offset},
                    timeout=settings.request_timeout,
                )
                response.raise_for_status()
                payload = response.json()
                return list(payload.get("result", []))
            except Exception as exc:
                last_error = exc
                logger.warning("Telegram getUpdates failed attempt=%s/%s error=%s", attempt, settings.request_retries, exc)
                if attempt < settings.request_retries:
                    self._sleep_func(float(attempt))
        if last_error is not None:
            raise last_error
        return []

    def _remember_processed(self, update_id: int) -> None:
        if len(self._processed_ids) == self._processed_ids.maxlen and self._processed_ids:
            expired = self._processed_ids.popleft()
            self._processed_lookup.discard(expired)
        self._processed_ids.append(update_id)
        self._processed_lookup.add(update_id)

    def _help_message(self) -> str:
        return "\n".join(
            [
                "🧭 Central de comandos AlphaScope",
                "",
                "Consultas",
                "• /status • /positions • /ranking • /profit • /portfolio • /apis",
                "• /ma_status • /ma_last • /ma_run BTCUSDT 1h",
                "",
                "Configuração operacional",
                "• /mode • /setmode paper • /setmode simulation • /setmode live confirm",
                "• /symbols • /addsymbol BTCUSDT • /removesymbol DOGEUSDT",
                "• /maxtrades • /setmaxtrades 3",
                "• /risk • /setrisk conservative • /setrisk moderate • /setrisk aggressive confirm",
                "",
                "Execução manual",
                "• /buy BTCUSDT • /sell BTCUSDT • /sellall confirm",
                "",
                "Operação do bot",
                "• /start • /help • /ping • /stopalerts • /startalerts • /restart",
            ]
        )

    def _welcome_message(self) -> str:
        return "\n".join(
            [
                "🤖 AlphaScope conectado com sucesso.",
                f"• Modo atual: {self.settings_manager.current_mode_label()}",
                f"• Moedas monitoradas: {len(self._current_symbols())}",
                f"• Telegram: {'ativo' if (settings.telegram_enabled or settings.enable_telegram_alerts) else 'inativo'}",
                "",
                "Comandos rápidos",
                "• /status • /ranking • /positions • /risk • /help",
            ]
        )

    def _status_message(self) -> str:
        runtime = self.runtime_status.get_status(interval=settings.default_interval)
        ranking = self.repository.get_latest_ranking(settings.default_interval)
        continuous_state = self._continuous_state()
        apis = settings.api_status_summary()
        enabled_count = sum(1 for value in apis.values() if "enabled" in value)
        payload = {
            "app_env": settings.environment,
            "mode": self.settings_manager.current_mode_label(),
            "open_trades": len(self.repository.get_trade_executions(status="OPEN")),
            "open_positions": len(self.repository.get_open_positions()),
            "monitored_coins": len(self._current_symbols()),
            "last_ranking": self._ranking_label(ranking),
            "last_cycle": continuous_state.get("last_cycle_finished_at") or continuous_state.get("updated_at") or "-",
            "telegram_state": "enabled" if settings.telegram_enabled else "disabled",
            "api_state": f"{enabled_count}/{len(apis)} enabled",
        }
        return status_message(payload)

    def _multi_agent_status_message(self) -> str:
        runtime = MultiAgentRuntime()
        try:
            status = runtime.status()
        finally:
            runtime.close()
        scheduler = status.get("scheduler", {}) if isinstance(status.get("scheduler"), dict) else {}
        heartbeat = status.get("heartbeat", {}) if isinstance(status.get("heartbeat"), dict) else {}
        symbols_map = status.get("symbols", {}) if isinstance(status.get("symbols"), dict) else {}
        symbols_summary = sorted(
            [item for item in symbols_map.values() if isinstance(item, dict)],
            key=lambda item: str(item.get("updated_at", "")),
            reverse=True,
        )
        payload = {
            "last_symbol": status.get("last_symbol"),
            "last_timeframe": status.get("last_timeframe"),
            "last_decision": status.get("last_decision"),
            "last_score": status.get("last_score"),
            "cache_backend": ((status.get("cache") or {}) if isinstance(status.get("cache"), dict) else {}).get("backend"),
            "heartbeat_status": heartbeat.get("status", heartbeat.get("component", "unknown")),
            "scheduler_jobs": scheduler.get("job_count", len(scheduler.get("jobs", [])) if isinstance(scheduler.get("jobs"), list) else 0),
            "updated_at": status.get("updated_at"),
            "symbols_summary": symbols_summary,
        }
        return multi_agent_status_message(payload)

    def _multi_agent_last_decision_message(self) -> str:
        rows = self.repository.get_audit_events(limit=10)
        if rows.empty:
            return "Nenhuma decisão multiagente auditada encontrada."
        filtered = rows.loc[rows["action"].astype(str) == "multi_agent_decision"] if "action" in rows.columns else pd.DataFrame()
        if filtered.empty:
            return "Nenhuma decisão multiagente auditada encontrada."
        record = filtered.iloc[0].to_dict()
        payload_json = record.get("payload_json", {}) if isinstance(record.get("payload_json"), dict) else {}
        decision_payload = {
            "symbol": record.get("target") or payload_json.get("symbol"),
            "timeframe": payload_json.get("timeframe"),
            "decision": payload_json.get("decision"),
            "final_score": payload_json.get("final_score"),
            "consensus": payload_json.get("consensus"),
            "execution_action": payload_json.get("execution_action"),
            "reasoning": payload_json.get("reasoning"),
        }
        return multi_agent_decision_message(decision_payload)

    def _multi_agent_run(self, args: list[str]) -> str:
        symbol = self._normalize_symbol(args[0]) if args else self._current_symbols()[0]
        timeframe = args[1] if len(args) > 1 else settings.default_interval
        runtime = MultiAgentRuntime()
        try:
            payload = runtime.run_cycle(symbol=symbol, timeframe=timeframe, mode=settings.live_trading_mode, send_telegram=False)
        finally:
            runtime.close()
        supervisor = payload.get("supervisor", {}) if isinstance(payload.get("supervisor"), dict) else {}
        execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
        return multi_agent_decision_message(
            {
                "symbol": payload.get("symbol", symbol),
                "timeframe": payload.get("timeframe", timeframe),
                "decision": supervisor.get("decision"),
                "final_score": supervisor.get("final_score"),
                "consensus": supervisor.get("consensus"),
                "execution_action": execution.get("action"),
                "reasoning": supervisor.get("reasoning"),
            }
        )

    def _ranking_message(self) -> str:
        ranking = self.repository.get_latest_ranking(settings.default_interval).head(5).copy()
        if ranking.empty:
            return "Ranking indisponivel."
        if "trend" not in ranking.columns:
            ranking["trend"] = ranking.get("market_regime", "unknown")
        return ranking_message(ranking.to_dict(orient="records"))

    def _profit_message(self) -> str:
        latest_snapshot = self.repository.get_latest_snapshot() or {}
        daily = self.repository.get_daily_performance() or {}
        realized_pnl = float(daily.get("realized_pnl", latest_snapshot.get("realized_pnl", 0.0)) or 0.0)
        win_rate = float(daily.get("win_rate", 0.0) or 0.0)
        total_trades = int(daily.get("total_trades", len(self.repository.get_trade_executions())) or 0)
        drawdown = abs(float(daily.get("max_drawdown", 0.0) or 0.0))
        return profit_message(
            {
                "equity": latest_snapshot.get("equity", 0.0),
                "cash": latest_snapshot.get("cash", 0.0),
                "realized_pnl": realized_pnl,
                "unrealized_pnl": latest_snapshot.get("unrealized_pnl", 0.0),
                "total_trades": total_trades,
                "win_rate": win_rate,
                "drawdown": drawdown,
            }
        )

    def _portfolio_message(self) -> str:
        exposure_pct = 0.0
        if settings.live_trading_enabled and settings.live_trading_mode != "paper":
            latest_account = self.repository.get_latest_account_snapshot() or {}
            exposure_pct = float(latest_account.get("exposure_pct", 0.0) or 0.0)
        else:
            snapshot = self.repository.get_latest_snapshot() or {}
            equity = float(snapshot.get("equity", 0.0) or 0.0)
            positions = snapshot.get("positions_json", {}) if isinstance(snapshot.get("positions_json"), dict) else {}
            if equity > 0:
                notional = sum(float(item.get("quantity", 0.0)) * float(item.get("market_price", item.get("current_price", 0.0)) or 0.0) for item in positions.values())
                exposure_pct = notional / equity if equity else 0.0
        return portfolio_message(
            {
                "equity": (self.repository.get_latest_snapshot() or {}).get("equity", 0.0),
                "cash": (self.repository.get_latest_snapshot() or {}).get("cash", 0.0),
                "realized_pnl": (self.repository.get_latest_snapshot() or {}).get("realized_pnl", 0.0),
                "unrealized_pnl": (self.repository.get_latest_snapshot() or {}).get("unrealized_pnl", 0.0),
                "open_positions": len(self.repository.get_open_positions()),
                "exposure_pct": exposure_pct,
            }
        )

    def _set_mode(self, args: list[str], chat_id: str) -> str:
        if not args:
            return "Uso: /setmode paper|live|simulation"
        mode = args[0].strip().lower()
        if mode == "live" and not self._confirmed(chat_id, f"setmode:{mode}", args):
            return "Confirmacao necessaria. Repita com /setmode live confirm"
        applied = self.settings_manager.set_mode(mode, persist=True)
        return f"Modo alterado para {applied}."

    def _add_symbol(self, args: list[str]) -> str:
        if not args:
            return "Uso: /addsymbol BTCUSDT"
        symbol = self._normalize_symbol(args[0])
        symbols = self.settings_manager.add_symbol(symbol, persist=True)
        self._update_pipeline_symbols(symbols)
        return "Moeda adicionada. Universo atual: " + ", ".join(symbols)

    def _remove_symbol(self, args: list[str]) -> str:
        if not args:
            return "Uso: /removesymbol DOGEUSDT"
        symbol = self._normalize_symbol(args[0])
        symbols = self.settings_manager.remove_symbol(symbol, persist=True)
        self._update_pipeline_symbols(symbols)
        return "Moeda removida. Universo atual: " + ", ".join(symbols)

    def _set_max_trades(self, args: list[str]) -> str:
        if not args:
            return "Uso: /setmaxtrades 3"
        value = int(args[0])
        self.settings_manager.set_max_open_trades(value, persist=True)
        return f"MAX_OPEN_TRADES atualizado para {value}."

    def _set_risk(self, args: list[str], chat_id: str) -> str:
        if not args:
            return "Uso: /setrisk conservative|moderate|aggressive"
        profile = args[0].strip().lower()
        if profile == "aggressive" and not self._confirmed(chat_id, f"setrisk:{profile}", args):
            return "Confirmacao necessaria. Repita com /setrisk aggressive confirm"
        risk_profile = self.settings_manager.set_risk_profile(profile, persist=True)
        return risk_message(
            {
                "max_position_size_pct": risk_profile.max_position_size_pct,
                "max_account_exposure_pct": risk_profile.max_account_exposure_pct,
                "max_daily_loss_pct": risk_profile.max_daily_loss_pct,
                "stop_loss_pct": risk_profile.stop_loss_pct,
                "take_profit_pct": risk_profile.take_profit_pct,
                "trailing_stop_pct": risk_profile.trailing_stop_pct,
            }
        )

    def _buy(self, args: list[str]) -> str:
        if not args:
            return "Uso: /buy DOGEUSDT"
        symbol = self._validate_trade_symbol(args[0])
        current_price = self._latest_price(symbol)
        if current_price <= 0:
            raise ValueError("Preco atual indisponivel para o simbolo.")
        if len(self.repository.get_open_positions()) >= settings.max_open_trades:
            return "Compra bloqueada: limite de trades abertos atingido."
        if settings.live_trading_enabled and settings.live_trading_mode != "paper":
            trader = LiveTrader(repository=self.repository)
            result = trader.process_live_signals(pd.DataFrame([{"symbol": symbol, "final_score": 1.0, "price": current_price, "source": "telegram_manual"}]))
            if not result:
                return "Nenhuma ordem enviada."
            first = result[0]
            if first.get("status") != "opened":
                return f"Compra bloqueada: {first.get('reason', 'unknown')}"
            return f"Compra executada: {symbol} qty={first.get('quantity')} price={first.get('entry_price')}"
        trader = PaperTrader(repository=self.repository, initial_cash=settings.paper_initial_cash)
        trade = trader.buy(symbol, current_price)
        if not trade:
            return "Compra bloqueada pelas regras de risco."
        self._persist_paper_trade(trader, trade)
        return f"Compra executada em paper: {symbol} qty={trade.get('quantity')} price={trade.get('price')}"

    def _sell(self, args: list[str]) -> str:
        if not args:
            return "Uso: /sell DOGEUSDT"
        symbol = self._validate_trade_symbol(args[0])
        position = self.repository.get_open_position(symbol)
        if position is None:
            return "Nao ha posicao aberta para esse simbolo."
        current_price = self._latest_price(symbol)
        if settings.live_trading_enabled and settings.live_trading_mode != "paper":
            trader = LiveTrader(repository=self.repository)
            result = trader.stop_manager.close_position(symbol, current_price, reason="manual_sell")
            return f"Venda executada: {symbol} pnl={result.get('pnl')}"
        trader = PaperTrader(repository=self.repository, initial_cash=settings.paper_initial_cash)
        trade = trader.sell(symbol, current_price)
        if not trade:
            return "Venda nao executada."
        self._persist_paper_trade(trader, trade)
        return f"Venda executada em paper: {symbol} pnl={trade.get('realized_pnl')}"

    def _sell_all(self, args: list[str], chat_id: str) -> str:
        if not self._confirmed(chat_id, "sellall", args):
            return "Confirmacao necessaria. Repita com /sellall confirm"
        positions = self.repository.get_open_positions()
        if positions.empty:
            return "Nao ha posicoes abertas."
        current_prices = {str(item["symbol"]).upper(): self._latest_price(str(item["symbol"]).upper()) for item in positions.to_dict(orient="records")}
        if settings.live_trading_enabled and settings.live_trading_mode != "paper":
            trader = LiveTrader(repository=self.repository)
            closed = trader.emergency_close_all(current_prices)
            return f"Sell all executado. Posicoes fechadas: {len(closed)}"
        trader = PaperTrader(repository=self.repository, initial_cash=settings.paper_initial_cash)
        trades: list[dict[str, object]] = []
        for symbol in list(positions["symbol"].astype(str)):
            trade = trader.sell(symbol.upper(), current_prices[symbol.upper()])
            if trade:
                trades.append(trade)
        self._persist_paper_trades(trader, trades)
        return f"Sell all executado em paper. Posicoes fechadas: {len(trades)}"

    def _persist_paper_trade(self, trader: PaperTrader, trade: dict[str, object]) -> None:
        self._persist_paper_trades(trader, [trade])

    def _persist_paper_trades(self, trader: PaperTrader, trades: list[dict[str, object]]) -> None:
        if not trades:
            return
        snapshot = {
            "timestamp": pd.Timestamp.now(tz="UTC").to_pydatetime(),
            "cash": trader.portfolio.cash,
            "equity": trader.portfolio.equity(),
            "realized_pnl": trader.portfolio.realized_pnl,
            "unrealized_pnl": trader.portfolio.unrealized_pnl(),
            "positions_json": {symbol: vars(position) for symbol, position in trader.portfolio.positions.items()},
        }
        self.repository.save_trades(trades)
        self.repository.save_snapshot(snapshot)

    def _validate_trade_symbol(self, raw_symbol: str) -> str:
        symbol = self._normalize_symbol(raw_symbol)
        if symbol not in self._current_symbols() and self.repository.get_candles(symbol=symbol, interval=settings.default_interval, limit=1).empty:
            raise ValueError("Simbolo invalido ou nao monitorado.")
        return symbol

    def _normalize_symbol(self, raw_symbol: str) -> str:
        symbol = raw_symbol.strip().upper()
        if not _SYMBOL_RE.match(symbol):
            raise ValueError("Simbolo invalido.")
        return symbol

    def _latest_price(self, symbol: str) -> float:
        candles = self.repository.get_candles(symbol=symbol, interval=settings.default_interval, limit=1)
        if candles.empty:
            return 0.0
        return float(candles.iloc[-1]["close"])

    def _current_symbols(self) -> list[str]:
        if self.continuous_pipeline is not None and getattr(self.continuous_pipeline, "config", None) is not None:
            return [str(symbol).upper() for symbol in getattr(self.continuous_pipeline.config, "symbols", [])]
        return settings.symbol_list

    def _update_pipeline_symbols(self, symbols: list[str]) -> None:
        if self.continuous_pipeline is not None and getattr(self.continuous_pipeline, "config", None) is not None:
            self.continuous_pipeline.config.symbols = list(symbols)

    def _set_runtime_alerts_enabled(self, enabled: bool) -> None:
        self.settings_manager.set_alerts_enabled(enabled, persist=False)
        self.notifier.enabled = True
        dispatcher = getattr(self.continuous_pipeline, "alert_dispatcher", None)
        telegram = getattr(dispatcher, "telegram", None)
        if telegram is not None:
            telegram.enabled = enabled

    def _risk_payload(self) -> dict[str, float]:
        return {
            "max_position_size_pct": settings.max_position_size_pct,
            "max_account_exposure_pct": settings.max_account_exposure_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "stop_loss_pct": settings.stop_loss_pct,
            "take_profit_pct": settings.take_profit_pct,
            "trailing_stop_pct": settings.trailing_stop_pct,
        }

    def _ranking_label(self, ranking: pd.DataFrame) -> str:
        if ranking.empty:
            return "-"
        top = ranking.sort_values("rank").iloc[0]
        return f"{top.get('symbol', '-')} score={float(top.get('score', 0.0)):.4f}"

    def _continuous_state(self) -> dict[str, Any]:
        if self.continuous_pipeline is not None and hasattr(self.continuous_pipeline, "get_state"):
            return dict(self.continuous_pipeline.get_state())
        return self.runtime_status.get_status(interval=settings.default_interval).get("continuous_pipeline", {})

    def _confirmed(self, chat_id: str, key: str, args: list[str]) -> bool:
        wants_confirm = any(arg.strip().lower() == "confirm" for arg in args)
        if wants_confirm and self._confirmation_state.get(chat_id) == key:
            self._confirmation_state.pop(chat_id, None)
            return True
        if wants_confirm and key in {"sellall", "setmode:live", "setrisk:aggressive"}:
            return False
        self._confirmation_state[chat_id] = key
        return False
