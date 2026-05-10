"""Operational CLI commands for continuous runtime and daemon management."""

from __future__ import annotations

import argparse
import json
import os
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alphascope.cli_registry import dispatch_command
from alphascope.config.settings import settings
from alphascope.ui import print_jobs_status, print_kv_panel, print_runtime_status, print_success, print_warning
from alphascope.utils.io import parse_csv_argument

if TYPE_CHECKING:
    from alphascope.storage.repositories import StorageRepository


RUNTIME_COMMANDS = {
    "run-continuous",
    "schedule-jobs",
    "show-jobs",
    "start-daemon",
    "stop-daemon",
    "status-daemon",
    "runtime-status",
    "doctor",
    "check-env",
    "backup-db",
    "verify-exchange-credentials",
    "run-live-simulated",
    "test-telegram-alert",
    "send-runtime-alert",
    "send-portfolio-alert",
    "show-trader-mode",
    "reset-live-state",
    "start-live-trading",
    "sync-account",
    "emergency-close",
}


def add_runtime_subparsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register runtime/operational commands into the main parser."""
    run_continuous_parser = subparsers.add_parser("run-continuous", help="Run the operational pipeline in cycles")
    run_continuous_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    run_continuous_parser.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    run_continuous_parser.add_argument("--news-seconds", type=int, default=settings.news_refresh_interval_seconds)
    run_continuous_parser.add_argument("--duration", type=int, default=None, help="Total duration in minutes")
    run_continuous_parser.add_argument("--timeframe", default=settings.default_interval)
    run_continuous_parser.add_argument("--limit", type=int, default=settings.default_candle_limit)
    run_continuous_parser.add_argument("--disable-news", action="store_true")
    run_continuous_parser.add_argument("--disable-market-refresh", action="store_true")
    run_continuous_parser.add_argument("--disable-paper-trading", action="store_true")

    schedule_jobs_parser = subparsers.add_parser("schedule-jobs", help="Register and run recurring operational jobs")
    schedule_jobs_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    schedule_jobs_parser.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    schedule_jobs_parser.add_argument("--news-seconds", type=int, default=settings.news_refresh_interval_seconds)
    schedule_jobs_parser.add_argument("--duration-seconds", type=int, default=60)
    schedule_jobs_parser.add_argument("--timeframe", default=settings.default_interval)
    schedule_jobs_parser.add_argument("--limit", type=int, default=settings.default_candle_limit)

    show_jobs_parser = subparsers.add_parser("show-jobs", help="Show scheduler job status from runtime state")
    show_jobs_parser.add_argument("--path", default=str(settings.runtime_dir / "scheduler_status.json"))

    start_daemon_parser = subparsers.add_parser("start-daemon", help="Start the AlphaScope foreground daemon")
    start_daemon_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    start_daemon_parser.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    start_daemon_parser.add_argument("--news-seconds", type=int, default=settings.news_refresh_interval_seconds)
    start_daemon_parser.add_argument("--heartbeat-seconds", type=int, default=settings.heartbeat_interval_seconds)
    start_daemon_parser.add_argument("--timeframe", default=settings.default_interval)
    start_daemon_parser.add_argument("--limit", type=int, default=settings.default_candle_limit)
    start_daemon_parser.add_argument("--disable-scheduler", action="store_true")
    start_daemon_parser.add_argument("--disable-continuous-pipeline", action="store_true")

    stop_daemon_parser = subparsers.add_parser("stop-daemon", help="Request daemon shutdown using the pid file")
    stop_daemon_parser.add_argument("--pid-file", default=str(settings.daemon_pid_file))

    status_daemon_parser = subparsers.add_parser("status-daemon", help="Show persisted daemon status")
    status_daemon_parser.add_argument("--interval", default=settings.default_interval)

    runtime_status_parser = subparsers.add_parser("runtime-status", help="Show aggregated runtime operational status")
    runtime_status_parser.add_argument("--interval", default=settings.default_interval)

    doctor_parser = subparsers.add_parser("doctor", help="Run non-destructive runtime readiness checks")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")

    check_env_parser = subparsers.add_parser("check-env", help="Alias for doctor")
    check_env_parser.add_argument("--json", action="store_true", dest="as_json")

    backup_db_parser = subparsers.add_parser("backup-db", help="Create a timestamped backup of the official database")
    backup_db_parser.add_argument("--output-dir", default="artifacts/backups")

    verify_exchange_parser = subparsers.add_parser("verify-exchange-credentials", help="Verify Binance credentials and clock sync without placing orders")
    verify_exchange_parser.add_argument("--mode", choices=["paper", "testnet", "live"], default=settings.live_trading_mode)

    live_simulated_parser = subparsers.add_parser("run-live-simulated", help="Run the live simulated trading loop")
    live_simulated_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    live_simulated_parser.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    live_simulated_parser.add_argument("--duration", type=int, default=None, help="Total duration in minutes")
    live_simulated_parser.add_argument("--timeframe", default=settings.default_interval)
    live_simulated_parser.add_argument("--limit", type=int, default=settings.default_candle_limit)
    live_simulated_parser.add_argument("--mode", choices=["dry_run", "live_simulated"], default="live_simulated")

    subparsers.add_parser("test-telegram-alert", help="Send a Telegram test alert")

    runtime_alert_parser = subparsers.add_parser("send-runtime-alert", help="Send a runtime summary alert")
    runtime_alert_parser.add_argument("--interval", default=settings.default_interval)

    portfolio_alert_parser = subparsers.add_parser("send-portfolio-alert", help="Send the latest portfolio snapshot alert")
    portfolio_alert_parser.add_argument("--label", default="Manual portfolio snapshot")

    subparsers.add_parser("show-trader-mode", help="Show the currently selected trader based on environment settings")

    subparsers.add_parser("reset-live-state", help="Clear persisted live trading runtime state without deleting market datasets")

    start_live_parser = subparsers.add_parser("start-live-trading", help="Process the latest ranking through Binance Spot testnet/live")
    start_live_parser.add_argument("--interval", default=settings.default_interval)
    start_live_parser.add_argument("--limit", type=int, default=20)
    start_live_parser.add_argument("--symbol", default=None)

    subparsers.add_parser("sync-account", help="Sync Binance account data and persist a fresh account snapshot")

    emergency_close_parser = subparsers.add_parser("emergency-close", help="Close all persisted open positions using latest local prices")
    emergency_close_parser.add_argument("--interval", default=settings.default_interval)
    emergency_close_parser.add_argument("--symbol", default=None)


def handle_runtime_command(args: argparse.Namespace, *, repository: StorageRepository) -> bool:
    """Dispatch runtime commands. Returns True when a command was handled."""
    return dispatch_command(args.command, RUNTIME_COMMAND_HANDLERS, args=args, repository=repository)


def _handle_run_continuous(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.automation import ContinuousPipeline, ContinuousPipelineConfig
    from alphascope.alerts.telegram_command_listener import TelegramCommandListener

    config = ContinuousPipelineConfig(
        cycle_interval_seconds=args.cycle_seconds,
        news_refresh_interval_seconds=args.news_seconds,
        symbols=parse_csv_argument(args.symbols),
        timeframe=args.timeframe,
        candle_limit=args.limit,
        enable_news=not args.disable_news,
        enable_market_refresh=not args.disable_market_refresh,
        enable_paper_trading=not args.disable_paper_trading,
        duration_minutes=args.duration,
        run_forever=args.duration is None,
    )
    continuous = ContinuousPipeline(config, repository=repository)
    listener = TelegramCommandListener(repository=repository, continuous_pipeline=continuous)
    if settings.telegram_enabled:
        listener.start()
    try:
        results = continuous.run(max_cycles=None)
    finally:
        listener.stop()
    final_state = continuous.get_state()
    print_success("Continuous pipeline finished.")
    print_kv_panel(
        "Continuous Pipeline",
        {
            "cycles_completed": final_state.get("cycles_completed", len(results)),
            "errors": final_state.get("errors", 0),
            "last_ranking_at": final_state.get("last_ranking_at"),
            "last_snapshot_at": final_state.get("last_snapshot_at"),
        },
        border_style="green",
    )


def _handle_schedule_jobs(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.automation import AutomationScheduler, ContinuousPipeline, ContinuousPipelineConfig

    pipeline = ContinuousPipeline(
        ContinuousPipelineConfig(
            cycle_interval_seconds=args.cycle_seconds,
            news_refresh_interval_seconds=args.news_seconds,
            symbols=parse_csv_argument(args.symbols),
            timeframe=args.timeframe,
            candle_limit=args.limit,
            run_forever=True,
        ),
        repository=repository,
    )
    scheduler = AutomationScheduler()
    scheduler.register_pipeline_jobs(
        pipeline,
        market_interval_seconds=args.cycle_seconds,
        news_interval_seconds=args.news_seconds,
        feature_interval_seconds=args.cycle_seconds,
        ranking_interval_seconds=args.cycle_seconds,
        paper_trading_interval_seconds=args.cycle_seconds,
    )
    scheduler.run_continuous(duration_seconds=args.duration_seconds, sleep_seconds=1)
    print_success("Scheduler run finished.")
    print_jobs_status(scheduler.list_jobs())


def _handle_show_jobs(args: argparse.Namespace, **_: Any) -> None:
    path = Path(args.path)
    if not path.exists():
        print_warning("Arquivo de status do scheduler nao encontrado.")
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    print_jobs_status(payload.get("jobs", []))


def _handle_start_daemon(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.automation import DaemonRunner, DaemonRunnerConfig

    config = DaemonRunnerConfig(
        symbols=parse_csv_argument(args.symbols),
        timeframe=args.timeframe,
        candle_limit=args.limit,
        cycle_interval_seconds=args.cycle_seconds,
        news_refresh_interval_seconds=args.news_seconds,
        heartbeat_interval_seconds=args.heartbeat_seconds,
        enable_scheduler=not args.disable_scheduler,
        enable_continuous_pipeline=not args.disable_continuous_pipeline,
    )
    status = DaemonRunner(config).start()
    print_success("Daemon finished.")
    print_kv_panel("Daemon Status", status, border_style="green")


def _handle_stop_daemon(args: argparse.Namespace, **_: Any) -> None:
    pid_file = Path(args.pid_file)
    if not pid_file.exists():
        print_warning("Pid file do daemon nao encontrado.")
        return
    pid = int(pid_file.read_text(encoding="utf-8").strip())
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        raise RuntimeError(f"Falha ao enviar sinal para o processo {pid}: {exc}") from exc
    print_success(f"Sinal de parada enviado para o processo {pid}.")


def _handle_status_daemon(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.monitoring.runtime_status import RuntimeStatusService

    status = RuntimeStatusService().get_status(interval=args.interval)
    print_runtime_status({"daemon": status.get("daemon", {}), **status})


def _handle_runtime_status(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.monitoring.runtime_status import RuntimeStatusService

    status = RuntimeStatusService(repository=repository).get_status(interval=args.interval)
    print_runtime_status(status)
    scheduler = status.get("scheduler", {})
    if isinstance(scheduler, dict):
        print_jobs_status(scheduler.get("jobs", []))


def _handle_doctor(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.runtime_validation import RuntimeValidator

    result = RuntimeValidator().run()
    if getattr(args, "as_json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    print_kv_panel(
        "Runtime Doctor",
        {
            "ok": result["ok"],
            "failures": len(result["failures"]),
            "warnings": len(result["warnings"]),
            "database": str(settings.sqlite_path),
            "mode": settings.live_trading_mode,
        },
        border_style="green" if result["ok"] else "red",
    )
    for issue in result["failures"] + result["warnings"]:
        print_warning(f"{issue['name']}: {issue['detail']}")


def _handle_backup_db(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.runtime_validation import BackupService

    backup_path = BackupService(backup_dir=Path(args.output_dir)).create_backup()
    print_success(f"Backup criado em {backup_path}")


def _handle_verify_exchange_credentials(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.execution.compat import BinanceClient, sync_binance_time_or_raise

    mode = str(args.mode).lower()
    if mode == "paper":
        print_success("Modo paper nao requer validacao de exchange. Ambiente esta seguro.")
        return
    if not (settings.binance_api_key and settings.binance_api_secret):
        raise RuntimeError("BINANCE_API_KEY e BINANCE_API_SECRET sao obrigatorios para validar credenciais.")
    client = BinanceClient(settings.binance_api_key, settings.binance_api_secret, testnet=mode == "testnet")
    if mode == "testnet":
        client.API_URL = settings.live_testnet_base_url.rstrip("/") + "/"
    drift = sync_binance_time_or_raise(client)
    account = client.get_account()
    balances = account.get("balances", []) if isinstance(account, dict) else []
    print_success("Credenciais Binance validadas com sucesso.")
    print_kv_panel(
        "Exchange Credentials",
        {
            "mode": mode,
            "clock_drift_ms": drift,
            "balances": len(balances),
            "api_url": getattr(client, "API_URL", settings.binance_base_url),
        },
        border_style="green",
    )


def _handle_run_live_simulated(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.simulation import LiveSimulationConfig, LiveSimulator

    simulator = LiveSimulator(
        LiveSimulationConfig(
            symbols=parse_csv_argument(args.symbols),
            timeframe=args.timeframe,
            candle_limit=args.limit,
            cycle_interval_seconds=args.cycle_seconds,
            mode=args.mode,
            duration_minutes=args.duration,
            run_forever=args.duration is None,
        )
    )
    results = simulator.run()
    state = simulator.get_state()
    print_success("Live simulated run finished.")
    print_kv_panel(
        "Live Simulated",
        {
            "mode": state.get("mode", args.mode),
            "cycles": len(results),
            "signals": state.get("signals", 0),
            "trades": state.get("trades", 0),
            "open_positions": state.get("open_positions", 0),
            "equity": state.get("equity"),
            "cash": state.get("cash"),
        },
        border_style="green",
    )


def _handle_test_telegram_alert(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.alerts import AlertDispatcher

    del args
    record = AlertDispatcher().send_test_alert(source="cli")
    if record.delivered:
        print_success("Telegram test alert enviado.")
        return
    print_warning(f"Telegram test alert nao entregue: {record.error}")


def _handle_send_runtime_alert(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.alerts import AlertDispatcher
    from alphascope.monitoring.runtime_status import RuntimeStatusService

    dispatcher = AlertDispatcher()
    status = RuntimeStatusService(repository=repository).get_status(interval=args.interval)
    records = dispatcher.evaluate_runtime_alerts(status)
    records.append(dispatcher.runtime_summary(status))
    delivered = sum(1 for record in records if record.delivered)
    print_success(f"{delivered}/{len(records)} alertas de runtime entregues.")


def _handle_send_portfolio_alert(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.alerts import AlertDispatcher

    snapshot = repository.get_latest_snapshot()
    if snapshot is None:
        print_warning("Nenhum snapshot de portfolio encontrado.")
        return
    record = AlertDispatcher().portfolio_snapshot(snapshot, label=args.label)
    if record.delivered:
        print_success("Alerta de portfolio enviado.")
        return
    print_warning(f"Alerta de portfolio nao entregue: {record.error}")


def _handle_show_trader_mode(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.execution.trader_selector import paper_trading_disabled, selected_trader_name

    del args
    print(f"LIVE_TRADING_ENABLED={str(settings.live_trading_enabled).lower()}")
    print(f"LIVE_TRADING_MODE={settings.live_trading_mode}")
    print(f"Trader selecionado={selected_trader_name()}")
    print(f"Paper trading desativado={str(paper_trading_disabled()).lower()}")


def _handle_reset_live_state(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.execution.trader_selector import selected_trader_name

    del args
    result = repository.reset_live_trading_state()
    settings.live_trading_state_file.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(UTC).isoformat(),
                "mode": settings.live_trading_mode,
                "live_trading_enabled": settings.live_trading_enabled,
                "selected_trader": selected_trader_name(),
                "open_positions": 0,
                "last_processed": 0,
                "exposure_pct": 0.0,
                "open_orders": 0,
                "reset": True,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("Resetting live trading state...")
    print(f"Open positions removed: {result['open_positions_removed']}")
    print(f"Stuck trades removed: {result['stuck_trades_removed']}")
    print("Exposure cache reset")
    print("Live trading state cleaned successfully")


def _handle_start_live_trading(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    import pandas as pd

    from alphascope.execution.live_trader import LiveTrader

    ranking = repository.get_latest_ranking(interval=args.interval)
    if ranking.empty:
        print_warning("Nenhum ranking encontrado para live trading.")
        return
    if args.symbol:
        ranking = ranking.loc[ranking["symbol"] == args.symbol.upper()].reset_index(drop=True)
    if ranking.empty:
        print_warning("Nenhum ativo elegivel apos o filtro informado.")
        return
    rows: list[dict[str, Any]] = []
    for record in ranking.to_dict(orient="records"):
        candles = repository.get_candles(symbol=str(record["symbol"]).upper(), interval=args.interval, limit=1)
        if candles.empty:
            continue
        record["price"] = float(candles.iloc[-1]["close"])
        rows.append(record)
    if not rows:
        print_warning("Nao ha precos locais suficientes para iniciar o live trading.")
        return
    frame = json.loads(json.dumps(rows, default=str))
    result = LiveTrader(repository=repository).process_live_signals(pd.DataFrame(frame).head(args.limit))
    print_success("Processamento de sinais live concluido.")
    print_kv_panel(
        "Live Trading",
        {
            "mode": settings.live_trading_mode,
            "enabled": settings.live_trading_enabled,
            "safe_mode": settings.live_mode_safe,
            "processed": len(result),
            "opened": sum(1 for item in result if item.get("status") == "opened"),
            "blocked": sum(1 for item in result if item.get("status") == "blocked"),
        },
        border_style="green",
    )


def _handle_sync_account(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.execution.live_trader import LiveTrader

    del args
    snapshot = LiveTrader(repository=repository).sync_account()
    print_success("Conta sincronizada.")
    print_kv_panel(
        "Account Snapshot",
        {
            "mode": snapshot["mode"],
            "total_balance": snapshot["total_balance"],
            "free_balance": snapshot["free_balance"],
            "locked_balance": snapshot["locked_balance"],
            "exposure_pct": snapshot["exposure_pct"],
            "open_positions": snapshot["open_positions"],
            "open_orders": snapshot["open_orders"],
        },
        border_style="green",
    )


def _handle_emergency_close(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    from alphascope.execution.live_trader import LiveTrader

    trader = LiveTrader(repository=repository)
    if args.symbol:
        symbol = str(args.symbol).upper()
        candles = repository.get_candles(symbol=symbol, interval=args.interval, limit=1)
        current_price = float(candles.iloc[-1]["close"]) if not candles.empty else 0.0
        result = trader.stop_manager.emergency_close_symbol(symbol, current_price=current_price)
        response = dict(result.get("response", {}))
        validation = dict(response.get("_validation", {}))
        print_success(f"Emergency close processado para {symbol}.")
        print_kv_panel(
            "Emergency Close",
            {
                "symbol": symbol,
                "real_balance": validation.get("real_balance", 0.0),
                "safe_quantity": validation.get("safe_quantity", 0.0),
                "normalized_quantity": validation.get("normalized_quantity", 0.0),
                "price": validation.get("price", current_price),
                "notional": validation.get("notional", 0.0),
                "min_notional": validation.get("min_notional", 0.0),
                "status": result.get("status", response.get("status", "UNKNOWN")),
                "reason": result.get("reason", response.get("reason", "-")),
            },
            border_style="green",
        )
        return

    positions = repository.get_open_positions()
    if positions.empty:
        print_warning("Nao ha posicoes abertas para encerrar.")
        return
    current_prices: dict[str, float] = {}
    for position in positions.to_dict(orient="records"):
        candles = repository.get_candles(symbol=str(position["symbol"]), interval=args.interval, limit=1)
        if not candles.empty:
            current_prices[str(position["symbol"])] = float(candles.iloc[-1]["close"])
    closed = trader.emergency_close_all(current_prices)
    print_success(f"{len(closed)} posicoes encerradas em emergency close.")


RUNTIME_COMMAND_HANDLERS = {
    "run-continuous": _handle_run_continuous,
    "schedule-jobs": _handle_schedule_jobs,
    "show-jobs": _handle_show_jobs,
    "start-daemon": _handle_start_daemon,
    "stop-daemon": _handle_stop_daemon,
    "status-daemon": _handle_status_daemon,
    "runtime-status": _handle_runtime_status,
    "doctor": _handle_doctor,
    "check-env": _handle_doctor,
    "backup-db": _handle_backup_db,
    "verify-exchange-credentials": _handle_verify_exchange_credentials,
    "run-live-simulated": _handle_run_live_simulated,
    "test-telegram-alert": _handle_test_telegram_alert,
    "send-runtime-alert": _handle_send_runtime_alert,
    "send-portfolio-alert": _handle_send_portfolio_alert,
    "show-trader-mode": _handle_show_trader_mode,
    "reset-live-state": _handle_reset_live_state,
    "start-live-trading": _handle_start_live_trading,
    "sync-account": _handle_sync_account,
    "emergency-close": _handle_emergency_close,
}
