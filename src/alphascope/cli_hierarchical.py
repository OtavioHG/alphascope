"""Hierarchical CLI command tree with compatibility mapping to legacy command names."""

from __future__ import annotations

import argparse

from alphascope.config.settings import settings


def add_hierarchical_subparsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    groups: dict[tuple[str, ...], argparse.ArgumentParser] = {}
    root_dest = subparsers.dest or "command"

    def ensure_group(path: tuple[str, ...], *, help_text: str) -> argparse.ArgumentParser:
        if path in groups:
            return groups[path]
        if len(path) == 1:
            parser = subparsers.add_parser(path[0], help=help_text)
        else:
            parent = ensure_group(path[:-1], help_text=path[:-1][-1].replace("-", " ").title())
            nested = getattr(parent, "_alphascope_nested_subparsers", None)
            if nested is None:
                nested = parent.add_subparsers(dest=f"{'_'.join(path[:-1])}_command", required=True)
                setattr(parent, "_alphascope_nested_subparsers", nested)
            parser = nested.add_parser(path[-1], help=help_text)
        groups[path] = parser
        return parser

    def add_leaf(path: tuple[str, ...], *, help_text: str, legacy_command: str) -> argparse.ArgumentParser:
        parent_path = path[:-1]
        if not parent_path:
            raise ValueError("Hierarchical path requires at least one group")
        parent = ensure_group(parent_path, help_text=parent_path[-1].replace("-", " ").title())
        nested = getattr(parent, "_alphascope_nested_subparsers", None)
        if nested is None:
            nested = parent.add_subparsers(dest=f"{'_'.join(parent_path)}_command", required=True)
            setattr(parent, "_alphascope_nested_subparsers", nested)
        parser = nested.add_parser(path[-1], help=help_text)
        parser.set_defaults(**{root_dest: legacy_command})
        return parser

    def add_market_args(target: argparse.ArgumentParser) -> None:
        target.add_argument("--symbols", default=",".join(settings.symbol_list))
        target.add_argument("--interval", default=settings.default_interval)
        target.add_argument("--limit", type=int, default=settings.default_candle_limit)

    market_ingest = add_leaf(("market", "ingest"), help_text="Fetch and store Binance candles", legacy_command="ingest-market")
    add_market_args(market_ingest)

    market_features_build = add_leaf(("market", "features", "build"), help_text="Compute and store technical features", legacy_command="build-features")
    market_features_build.add_argument("--symbols", default=",".join(settings.symbol_list))
    market_features_build.add_argument("--interval", default=settings.default_interval)

    market_ranking_run = add_leaf(("market", "ranking", "run"), help_text="Generate and store asset ranking", legacy_command="rank-assets")
    market_ranking_run.add_argument("--symbols", default=",".join(settings.symbol_list))
    market_ranking_run.add_argument("--interval", default=settings.default_interval)

    market_ranking_explain = add_leaf(("market", "ranking", "explain"), help_text="Explain ranking contributions by asset", legacy_command="explain-ranking")
    market_ranking_explain.add_argument("--symbols", default=",".join(settings.symbol_list))
    market_ranking_explain.add_argument("--interval", default=settings.default_interval)
    market_ranking_explain.add_argument("--limit", type=int, default=20)

    market_backtest_run = add_leaf(("market", "backtest", "run"), help_text="Run simple backtest", legacy_command="backtest")
    market_backtest_run.add_argument("--symbol", default=settings.symbol_list[0])
    market_backtest_run.add_argument("--interval", default=settings.default_interval)

    market_paper_run = add_leaf(("market", "paper", "run"), help_text="Run paper trading cycle", legacy_command="paper-trade")
    market_paper_run.add_argument("--symbols", default=",".join(settings.symbol_list))
    market_paper_run.add_argument("--interval", default=settings.default_interval)

    market_pipeline_run = add_leaf(("market", "pipeline", "run"), help_text="Run end-to-end pipeline", legacy_command="run-pipeline")
    add_market_args(market_pipeline_run)
    market_pipeline_run.add_argument("--use-auto-universe", action="store_true")
    market_pipeline_run.add_argument("--universe-path", default=None)

    market_pipeline_loop = add_leaf(("market", "pipeline", "loop"), help_text="Run the pipeline repeatedly for a fixed duration", legacy_command="run-loop")
    market_pipeline_loop.add_argument("--symbols", default=",".join(settings.symbol_list))
    market_pipeline_loop.add_argument("--duration", type=int, required=True, help="Total duration in minutes")
    market_pipeline_loop.add_argument("--interval", type=int, required=True, help="Delay between runs in seconds")
    market_pipeline_loop.add_argument("--timeframe", default=settings.default_interval)
    market_pipeline_loop.add_argument("--limit", type=int, default=settings.default_candle_limit)

    market_universe_build = add_leaf(("market", "universe", "build"), help_text="Build automatic Binance market universe", legacy_command="build-universe")
    market_universe_build.add_argument("--top", type=int, default=settings.auto_universe_top_n)
    market_universe_build.add_argument("--quote", default=settings.auto_universe_quote_asset)
    market_universe_build.add_argument("--min-volume", type=float, default=settings.auto_universe_min_volume)
    market_universe_build.add_argument("--output-path", default=None)

    market_data_show = add_leaf(("market", "data", "show"), help_text="Inspect data already saved in the local database", legacy_command="show-data")
    market_data_show.add_argument("--type", choices=["candles", "features", "ranking", "snapshot", "open-positions", "account", "live-trades"], required=True)
    market_data_show.add_argument("--symbol", default=settings.symbol_list[0])
    market_data_show.add_argument("--interval", default=settings.default_interval)
    market_data_show.add_argument("--limit", type=int, default=20)

    market_universe_fetch = add_leaf(("market", "universe", "fetch"), help_text="Fetch and consolidate market data from multiple sources", legacy_command="fetch-market-universe")
    market_universe_fetch.add_argument("--primary-source", default=settings.primary_market_source)
    market_universe_fetch.add_argument("--fallback-sources", default=",".join(settings.fallback_sources_list))
    market_universe_fetch.add_argument("--limit", type=int, default=100)

    market_universe_show = add_leaf(("market", "universe", "show"), help_text="Show saved automatic or consolidated market universe", legacy_command="show-universe")
    market_universe_show.add_argument("--kind", choices=["auto", "consolidated"], default="auto")
    market_universe_show.add_argument("--limit", type=int, default=30)
    market_universe_show.add_argument("--sort-by", choices=["rank", "rank_volume", "market_cap", "volume_24h", "price", "last_price", "canonical_symbol", "symbol"], default="volume_24h")
    market_universe_show.add_argument("--source", default=None)
    market_universe_show.add_argument("--selected-only", action="store_true")
    market_universe_show.add_argument("--path", default=None)

    market_universe_auto_run = add_leaf(("market", "universe", "auto-run"), help_text="Build the automatic universe and run the pipeline", legacy_command="run-auto-universe")
    market_universe_auto_run.add_argument("--top", type=int, default=settings.auto_universe_top_n)
    market_universe_auto_run.add_argument("--quote", default=settings.auto_universe_quote_asset)
    market_universe_auto_run.add_argument("--min-volume", type=float, default=settings.auto_universe_min_volume)
    market_universe_auto_run.add_argument("--interval", default=settings.default_interval)
    market_universe_auto_run.add_argument("--limit", type=int, default=settings.default_candle_limit)
    market_universe_auto_run.add_argument("--output-path", default=None)

    market_sources_compare = add_leaf(("market", "sources", "compare"), help_text="Compare source snapshots for the same assets", legacy_command="compare-sources")
    market_sources_compare.add_argument("--symbol", default=None)
    market_sources_compare.add_argument("--limit", type=int, default=50)

    market_sources_cc = add_leaf(("market", "sources", "cryptocompare-history"), help_text="Fetch historical OHLCV from CryptoCompare", legacy_command="fetch-cryptocompare-history")
    market_sources_cc.add_argument("--symbol", required=True)
    market_sources_cc.add_argument("--quote-symbol", default="USD")
    market_sources_cc.add_argument("--interval", choices=["1h", "1d"], default="1h")
    market_sources_cc.add_argument("--limit", type=int, default=2000)

    market_sentiment_fg = add_leaf(("market", "sentiment", "fear-greed"), help_text="Fetch Fear & Greed market sentiment data", legacy_command="fetch-fear-greed")
    market_sentiment_fg.add_argument("--limit", type=int, default=30)

    data_dataset_build_training = add_leaf(("data", "dataset", "build-training"), help_text="Build a supervised market training dataset", legacy_command="build-training-dataset")
    data_dataset_build_training.add_argument("--symbols", default=",".join(settings.symbol_list))
    data_dataset_build_training.add_argument("--interval", default=settings.default_interval)
    data_dataset_build_training.add_argument("--horizon-bars", type=int, default=settings.target_horizon_bars)
    data_dataset_build_training.add_argument("--threshold-pct", type=float, default=settings.target_threshold_pct)
    data_dataset_build_training.add_argument("--external-dataset-paths", default=None)

    data_dataset_build_market = add_leaf(("data", "dataset", "build-market"), help_text="Build a market dataset from local and external sources", legacy_command="build-market-dataset")
    data_dataset_build_market.add_argument("--symbols", default=",".join(settings.symbol_list))
    data_dataset_build_market.add_argument("--interval", default=settings.default_interval)
    data_dataset_build_market.add_argument("--horizon-bars", type=int, default=settings.target_horizon_bars)
    data_dataset_build_market.add_argument("--threshold-pct", type=float, default=settings.target_threshold_pct)
    data_dataset_build_market.add_argument("--external-dataset-paths", default=None)
    data_dataset_build_market.add_argument("--chunk-size", type=int, default=100000)

    data_dataset_import_market = add_leaf(("data", "dataset", "import-market"), help_text="Import and normalize a large external market dataset", legacy_command="import-market-dataset")
    data_dataset_import_market.add_argument("--input-path", required=True)
    data_dataset_import_market.add_argument("--output-path", default=None)
    data_dataset_import_market.add_argument("--chunk-size", type=int, default=100000)

    data_dataset_list_external = add_leaf(("data", "dataset", "list-external"), help_text="List external market/news datasets available locally", legacy_command="list-external-datasets")
    data_dataset_list_external.add_argument("--type", choices=["market", "news", "all"], default="all")

    ml_market_train = add_leaf(("ml", "market", "train"), help_text="Train and persist market ML models", legacy_command="train-market-model")
    ml_market_train.add_argument("--symbols", default=",".join(settings.symbol_list))
    ml_market_train.add_argument("--interval", default=settings.default_interval)

    ml_market_evaluate = add_leaf(("ml", "market", "evaluate"), help_text="Evaluate the saved market ML model", legacy_command="evaluate-market-model")
    ml_market_evaluate.add_argument("--symbols", default=",".join(settings.symbol_list))
    ml_market_evaluate.add_argument("--interval", default=settings.default_interval)
    ml_market_evaluate.add_argument("--artifact-path", default=str(settings.market_model_path))

    ml_market_predict = add_leaf(("ml", "market", "predict"), help_text="Generate market probabilities with the saved model", legacy_command="predict-market")
    ml_market_predict.add_argument("--symbols", default=",".join(settings.symbol_list))
    ml_market_predict.add_argument("--interval", default=settings.default_interval)

    ml_news_train = add_leaf(("ml", "news", "train"), help_text="Train a supervised news sentiment model", legacy_command="train-news-model")
    ml_news_train.add_argument("--input-path", default=str(settings.news_data_dir / "news_training_dataset.csv"))
    ml_news_train.add_argument("--text-column", default=None)
    ml_news_train.add_argument("--label-column", default="label")

    ml_strategy_optimize = add_leaf(("ml", "strategy", "optimize"), help_text="Optimize strategy parameters with Optuna", legacy_command="optimize-strategy")
    ml_strategy_optimize.add_argument("--symbol", default=settings.symbol_list[0])
    ml_strategy_optimize.add_argument("--interval", default=settings.default_interval)
    ml_strategy_optimize.add_argument("--trials", type=int, default=settings.optuna_trials)

    ml_production_train = add_leaf(("ml", "production", "train"), help_text="Build dataset, train the market model and warm the production AI stack", legacy_command="train-production-ai")
    ml_production_train.add_argument("--symbols", default=",".join(settings.symbol_list))
    ml_production_train.add_argument("--interval", default=settings.default_interval)
    ml_production_train.add_argument("--horizon-bars", type=int, default=settings.target_horizon_bars)
    ml_production_train.add_argument("--threshold-pct", type=float, default=settings.target_threshold_pct)

    news_ingest = add_leaf(("news", "ingest"), help_text="Fetch news from GDELT and store locally", legacy_command="ingest-news")
    news_ingest.add_argument("--query", default="crypto OR bitcoin OR ethereum")
    news_ingest.add_argument("--days", type=int, default=1)
    news_ingest.add_argument("--limit", type=int, default=50)

    news_dataset_build = add_leaf(("news", "dataset", "build"), help_text="Build a consolidated news dataset from multiple sources", legacy_command="build-news-dataset")
    news_dataset_build.add_argument("--query", default="crypto OR bitcoin OR ethereum")
    news_dataset_build.add_argument("--days", type=int, default=1)
    news_dataset_build.add_argument("--limit", type=int, default=50)
    news_dataset_build.add_argument("--include-hf", action="store_true")
    news_dataset_build.add_argument("--hf-export-path", default=None)
    news_dataset_build.add_argument("--kaggle-export-path", default=None)
    news_dataset_build.add_argument("--filename", default=settings.news_dataset_path.name)

    news_dataset_import = add_leaf(("news", "dataset", "import"), help_text="Import and normalize an external news dataset", legacy_command="import-news-dataset")
    news_dataset_import.add_argument("--input-path", required=True)
    news_dataset_import.add_argument("--output-path", default=None)

    news_signals_show = add_leaf(("news", "signals", "show"), help_text="Show aggregated news signals by asset", legacy_command="show-news-signals")
    news_signals_show.add_argument("--symbols", default=None)
    news_signals_show.add_argument("--limit", type=int, default=20)

    news_score = add_leaf(("news", "score"), help_text="Score news sentiment and topics", legacy_command="score-news")
    news_score.add_argument("--input-path", default=str(settings.news_data_dir / "gdelt_news_latest.csv"))

    runtime_continuous_run = add_leaf(("runtime", "continuous", "run"), help_text="Run the operational pipeline in cycles", legacy_command="run-continuous")
    runtime_continuous_run.add_argument("--symbols", default=",".join(settings.symbol_list))
    runtime_continuous_run.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    runtime_continuous_run.add_argument("--news-seconds", type=int, default=settings.news_refresh_interval_seconds)
    runtime_continuous_run.add_argument("--duration", type=int, default=None, help="Total duration in minutes")
    runtime_continuous_run.add_argument("--timeframe", default=settings.default_interval)
    runtime_continuous_run.add_argument("--limit", type=int, default=settings.default_candle_limit)
    runtime_continuous_run.add_argument("--disable-news", action="store_true")
    runtime_continuous_run.add_argument("--disable-market-refresh", action="store_true")
    runtime_continuous_run.add_argument("--disable-paper-trading", action="store_true")

    runtime_scheduler_run = add_leaf(("runtime", "scheduler", "run"), help_text="Register and run recurring operational jobs", legacy_command="schedule-jobs")
    runtime_scheduler_run.add_argument("--symbols", default=",".join(settings.symbol_list))
    runtime_scheduler_run.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    runtime_scheduler_run.add_argument("--news-seconds", type=int, default=settings.news_refresh_interval_seconds)
    runtime_scheduler_run.add_argument("--duration-seconds", type=int, default=60)
    runtime_scheduler_run.add_argument("--timeframe", default=settings.default_interval)
    runtime_scheduler_run.add_argument("--limit", type=int, default=settings.default_candle_limit)

    runtime_scheduler_show = add_leaf(("runtime", "scheduler", "show"), help_text="Show scheduler job status from runtime state", legacy_command="show-jobs")
    runtime_scheduler_show.add_argument("--path", default=str(settings.runtime_dir / "scheduler_status.json"))

    runtime_daemon_start = add_leaf(("runtime", "daemon", "start"), help_text="Start the AlphaScope foreground daemon", legacy_command="start-daemon")
    runtime_daemon_start.add_argument("--symbols", default=",".join(settings.symbol_list))
    runtime_daemon_start.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    runtime_daemon_start.add_argument("--news-seconds", type=int, default=settings.news_refresh_interval_seconds)
    runtime_daemon_start.add_argument("--heartbeat-seconds", type=int, default=settings.heartbeat_interval_seconds)
    runtime_daemon_start.add_argument("--timeframe", default=settings.default_interval)
    runtime_daemon_start.add_argument("--limit", type=int, default=settings.default_candle_limit)
    runtime_daemon_start.add_argument("--disable-scheduler", action="store_true")
    runtime_daemon_start.add_argument("--disable-continuous-pipeline", action="store_true")

    runtime_daemon_stop = add_leaf(("runtime", "daemon", "stop"), help_text="Request daemon shutdown using the pid file", legacy_command="stop-daemon")
    runtime_daemon_stop.add_argument("--pid-file", default=str(settings.daemon_pid_file))

    runtime_daemon_status = add_leaf(("runtime", "daemon", "status"), help_text="Show persisted daemon status", legacy_command="status-daemon")
    runtime_daemon_status.add_argument("--interval", default=settings.default_interval)

    runtime_status_show = add_leaf(("runtime", "status", "show"), help_text="Show aggregated runtime operational status", legacy_command="runtime-status")
    runtime_status_show.add_argument("--interval", default=settings.default_interval)

    runtime_live_simulated_run = add_leaf(("runtime", "live-simulated", "run"), help_text="Run the live simulated trading loop", legacy_command="run-live-simulated")
    runtime_live_simulated_run.add_argument("--symbols", default=",".join(settings.symbol_list))
    runtime_live_simulated_run.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    runtime_live_simulated_run.add_argument("--duration", type=int, default=None, help="Total duration in minutes")
    runtime_live_simulated_run.add_argument("--timeframe", default=settings.default_interval)
    runtime_live_simulated_run.add_argument("--limit", type=int, default=settings.default_candle_limit)
    runtime_live_simulated_run.add_argument("--mode", choices=["dry_run", "live_simulated"], default="live_simulated")

    runtime_trader_mode = add_leaf(("runtime", "trader", "mode"), help_text="Show the currently selected trader based on environment settings", legacy_command="show-trader-mode")
    runtime_live_reset = add_leaf(("runtime", "live", "reset-state"), help_text="Clear persisted live trading runtime state without deleting market datasets", legacy_command="reset-live-state")

    runtime_live_start = add_leaf(("runtime", "live", "start"), help_text="Process the latest ranking through Binance Spot testnet/live", legacy_command="start-live-trading")
    runtime_live_start.add_argument("--interval", default=settings.default_interval)
    runtime_live_start.add_argument("--limit", type=int, default=20)
    runtime_live_start.add_argument("--symbol", default=None)

    runtime_live_emergency = add_leaf(("runtime", "live", "emergency-close"), help_text="Close all persisted open positions using latest local prices", legacy_command="emergency-close")
    runtime_live_emergency.add_argument("--interval", default=settings.default_interval)
    runtime_live_emergency.add_argument("--symbol", default=None)

    runtime_account_sync = add_leaf(("runtime", "account", "sync"), help_text="Sync Binance account data and persist a fresh account snapshot", legacy_command="sync-account")

    alerts_telegram_test = add_leaf(("alerts", "telegram", "test"), help_text="Send a Telegram test alert", legacy_command="test-telegram-alert")
    alerts_runtime_send = add_leaf(("alerts", "runtime", "send"), help_text="Send a runtime summary alert", legacy_command="send-runtime-alert")
    alerts_runtime_send.add_argument("--interval", default=settings.default_interval)
    alerts_portfolio_send = add_leaf(("alerts", "portfolio", "send"), help_text="Send the latest portfolio snapshot alert", legacy_command="send-portfolio-alert")
    alerts_portfolio_send.add_argument("--label", default="Manual portfolio snapshot")

    maintenance_doctor = add_leaf(("maintenance", "doctor"), help_text="Run non-destructive runtime readiness checks", legacy_command="doctor")
    maintenance_doctor.add_argument("--json", action="store_true", dest="as_json")
    maintenance_check_env = add_leaf(("maintenance", "check-env"), help_text="Alias for doctor", legacy_command="check-env")
    maintenance_check_env.add_argument("--json", action="store_true", dest="as_json")

    maintenance_db_backup = add_leaf(("maintenance", "db", "backup"), help_text="Create a timestamped backup of the official database", legacy_command="backup-db")
    maintenance_db_backup.add_argument("--output-dir", default="artifacts/backups")

    maintenance_exchange_verify = add_leaf(("maintenance", "exchange", "verify"), help_text="Verify Binance credentials and clock sync without placing orders", legacy_command="verify-exchange-credentials")
    maintenance_exchange_verify.add_argument("--mode", choices=["paper", "testnet", "live"], default=settings.live_trading_mode)

    platform_control_center = add_leaf(("platform", "control-center"), help_text="Open the professional control center dashboard", legacy_command="control-center")
    platform_status = add_leaf(("platform", "status"), help_text="Show platform status, risk and portfolio snapshot", legacy_command="platform-status")
    platform_api_run = add_leaf(("platform", "api", "run"), help_text="Run the FastAPI platform backend", legacy_command="run-platform-api")
    platform_api_run.add_argument("--host", default="0.0.0.0")
    platform_api_run.add_argument("--port", type=int, default=8010)
    platform_telegram_run = add_leaf(("platform", "telegram", "run"), help_text="Run the Telegram control bot", legacy_command="run-telegram-bot")
    platform_telegram_run.add_argument("--once", action="store_true")
    platform_dashboard_run = add_leaf(("platform", "dashboard", "run"), help_text="Run the official Streamlit dashboard", legacy_command="run-dashboard")
    platform_dashboard_run.add_argument("--host", default="0.0.0.0")
    platform_dashboard_run.add_argument("--port", type=int, default=8501)

    agents_run = add_leaf(("agents", "run"), help_text="Run the full multi-agent decision workflow", legacy_command="run-multi-agent")
    agents_run.add_argument("--symbol", default=settings.symbol_list[0])
    agents_run.add_argument("--interval", default=settings.default_interval)

    agents_debate_run = add_leaf(("agents", "debate", "run"), help_text="Run only the internal multi-agent debate for one symbol", legacy_command="run-debate")
    agents_debate_run.add_argument("--symbol", default=settings.symbol_list[0])
    agents_debate_run.add_argument("--interval", default=settings.default_interval)

    agents_output_show = add_leaf(("agents", "output", "show"), help_text="Show persisted outputs for the selected symbol", legacy_command="show-agent-output")
    agents_output_show.add_argument("--symbol", default=settings.symbol_list[0])
    agents_output_show.add_argument("--interval", default=settings.default_interval)
    agents_output_show.add_argument("--limit", type=int, default=20)

    agents_consensus_history = add_leaf(("agents", "consensus", "history"), help_text="Show historical supervisor consensus decisions", legacy_command="show-consensus-history")
    agents_consensus_history.add_argument("--limit", type=int, default=20)
    agents_consensus_history.add_argument("--symbol", default=None)

    agents_supervisor_run = add_leaf(("agents", "supervisor", "run"), help_text="Run supervisor consensus without live execution", legacy_command="run-supervisor")
    agents_supervisor_run.add_argument("--symbol", default=settings.symbol_list[0])
    agents_supervisor_run.add_argument("--interval", default=settings.default_interval)

    agents_performance_show = add_leaf(("agents", "performance", "show"), help_text="Show aggregated agent activity/performance", legacy_command="show-agent-performance")
    agents_performance_show.add_argument("--limit", type=int, default=20)

    agents_decisions_compare = add_leaf(("agents", "decisions", "compare"), help_text="Compare how agents disagreed or aligned", legacy_command="compare-agent-decisions")
    agents_decisions_compare.add_argument("--symbol", default=settings.symbol_list[0])
    agents_decisions_compare.add_argument("--interval", default=settings.default_interval)
    agents_decisions_compare.add_argument("--limit", type=int, default=20)

    agents_live_run = add_leaf(("agents", "live", "run"), help_text="Run the live multi-agent workflow with Telegram alerts", legacy_command="run-live-multi-agent")
    agents_live_run.add_argument("--symbol", default=settings.symbol_list[0])
    agents_live_run.add_argument("--interval", default=settings.default_interval)

    agents_live_schedule = add_leaf(("agents", "live", "schedule"), help_text="Schedule continuous live multi-agent cycles", legacy_command="schedule-live-multi-agent")
    agents_live_schedule.add_argument("--symbols", default=",".join(settings.symbol_list))
    agents_live_schedule.add_argument("--interval", default=settings.default_interval)
    agents_live_schedule.add_argument("--cycle-seconds", type=int, default=settings.cycle_interval_seconds)
    agents_live_schedule.add_argument("--duration-seconds", type=int, default=60)

    agents_runtime_status = add_leaf(("agents", "runtime", "status"), help_text="Show multi-agent runtime/cache/scheduler status", legacy_command="multi-agent-runtime-status")
    agents_runtime_status.add_argument("--json", action="store_true", dest="as_json")

    agents_models_train = add_leaf(("agents", "models", "train"), help_text="Train local multi-agent models with available ML libraries", legacy_command="train-multi-agent-models")
    agents_models_train.add_argument("--limit", type=int, default=20)
    agents_models_train.add_argument("--symbols", default=",".join(settings.symbol_list))
    agents_models_train.add_argument("--interval", default=settings.default_interval)
    agents_models_train.add_argument("--cycle-count", type=int, default=1)

    agents_backtest_run = add_leaf(("agents", "backtest", "run"), help_text="Run historical multi-agent backtest", legacy_command="backtest-multi-agent")
    agents_backtest_run.add_argument("--symbol", default=settings.symbol_list[0])
    agents_backtest_run.add_argument("--interval", default=settings.default_interval)
    agents_backtest_run.add_argument("--limit", type=int, default=300)
