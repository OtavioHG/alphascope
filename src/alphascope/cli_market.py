"""Core market and pipeline CLI commands for AlphaScope."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from alphascope.cli_registry import dispatch_command
from alphascope.config.settings import settings
from alphascope.ui import (
    print_backtest_result,
    print_kv_panel,
    print_pipeline_summary,
    print_section,
    print_snapshot,
    print_success,
    print_table_from_dataframe,
    print_warning,
)
from alphascope.utils.io import parse_csv_argument


def add_market_subparsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register market, pipeline and source commands into the main parser."""

    def add_market_args(target: argparse.ArgumentParser) -> None:
        target.add_argument("--symbols", default=",".join(settings.symbol_list))
        target.add_argument("--interval", default=settings.default_interval)
        target.add_argument("--limit", type=int, default=settings.default_candle_limit)

    add_market_args(subparsers.add_parser("ingest-market", help="Fetch and store Binance candles"))

    features_parser = subparsers.add_parser("build-features", help="Compute and store technical features")
    features_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    features_parser.add_argument("--interval", default=settings.default_interval)

    rank_parser = subparsers.add_parser("rank-assets", help="Generate and store asset ranking")
    rank_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    rank_parser.add_argument("--interval", default=settings.default_interval)

    explain_rank_parser = subparsers.add_parser("explain-ranking", help="Explain ranking contributions by asset")
    explain_rank_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    explain_rank_parser.add_argument("--interval", default=settings.default_interval)
    explain_rank_parser.add_argument("--limit", type=int, default=20)

    backtest_parser = subparsers.add_parser("backtest", help="Run simple backtest")
    backtest_parser.add_argument("--symbol", default=settings.symbol_list[0])
    backtest_parser.add_argument("--interval", default=settings.default_interval)

    paper_parser = subparsers.add_parser("paper-trade", help="Run paper trading cycle")
    paper_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    paper_parser.add_argument("--interval", default=settings.default_interval)

    run_pipeline_parser = subparsers.add_parser("run-pipeline", help="Run end-to-end pipeline")
    add_market_args(run_pipeline_parser)
    run_pipeline_parser.add_argument("--use-auto-universe", action="store_true")
    run_pipeline_parser.add_argument("--universe-path", default=None)

    run_loop_parser = subparsers.add_parser("run-loop", help="Run the pipeline repeatedly for a fixed duration")
    run_loop_parser.add_argument("--symbols", default=",".join(settings.symbol_list))
    run_loop_parser.add_argument("--duration", type=int, required=True, help="Total duration in minutes")
    run_loop_parser.add_argument("--interval", type=int, required=True, help="Delay between runs in seconds")
    run_loop_parser.add_argument("--timeframe", default=settings.default_interval)
    run_loop_parser.add_argument("--limit", type=int, default=settings.default_candle_limit)

    build_universe_parser = subparsers.add_parser("build-universe", help="Build automatic Binance market universe")
    build_universe_parser.add_argument("--top", type=int, default=settings.auto_universe_top_n)
    build_universe_parser.add_argument("--quote", default=settings.auto_universe_quote_asset)
    build_universe_parser.add_argument("--min-volume", type=float, default=settings.auto_universe_min_volume)
    build_universe_parser.add_argument("--output-path", default=None)

    show_parser = subparsers.add_parser("show-data", help="Inspect data already saved in the local database")
    show_parser.add_argument(
        "--type",
        choices=["candles", "features", "ranking", "snapshot", "open-positions", "account", "live-trades"],
        required=True,
    )
    show_parser.add_argument("--symbol", default=settings.symbol_list[0])
    show_parser.add_argument("--interval", default=settings.default_interval)
    show_parser.add_argument("--limit", type=int, default=20)

    universe_parser = subparsers.add_parser("fetch-market-universe", help="Fetch and consolidate market data from multiple sources")
    universe_parser.add_argument("--primary-source", default=settings.primary_market_source)
    universe_parser.add_argument("--fallback-sources", default=",".join(settings.fallback_sources_list))
    universe_parser.add_argument("--limit", type=int, default=100)

    show_universe_parser = subparsers.add_parser("show-universe", help="Show saved automatic or consolidated market universe")
    show_universe_parser.add_argument("--kind", choices=["auto", "consolidated"], default="auto")
    show_universe_parser.add_argument("--limit", type=int, default=30)
    show_universe_parser.add_argument(
        "--sort-by",
        choices=["rank", "rank_volume", "market_cap", "volume_24h", "price", "last_price", "canonical_symbol", "symbol"],
        default="volume_24h",
    )
    show_universe_parser.add_argument("--source", default=None)
    show_universe_parser.add_argument("--selected-only", action="store_true")
    show_universe_parser.add_argument("--path", default=None)

    auto_pipeline_parser = subparsers.add_parser("run-auto-universe", help="Build the automatic universe and run the pipeline")
    auto_pipeline_parser.add_argument("--top", type=int, default=settings.auto_universe_top_n)
    auto_pipeline_parser.add_argument("--quote", default=settings.auto_universe_quote_asset)
    auto_pipeline_parser.add_argument("--min-volume", type=float, default=settings.auto_universe_min_volume)
    auto_pipeline_parser.add_argument("--interval", default=settings.default_interval)
    auto_pipeline_parser.add_argument("--limit", type=int, default=settings.default_candle_limit)
    auto_pipeline_parser.add_argument("--output-path", default=None)

    compare_parser = subparsers.add_parser("compare-sources", help="Compare source snapshots for the same assets")
    compare_parser.add_argument("--symbol", default=None)
    compare_parser.add_argument("--limit", type=int, default=50)

    cryptocompare_parser = subparsers.add_parser("fetch-cryptocompare-history", help="Fetch historical OHLCV from CryptoCompare")
    cryptocompare_parser.add_argument("--symbol", required=True)
    cryptocompare_parser.add_argument("--quote-symbol", default="USD")
    cryptocompare_parser.add_argument("--interval", choices=["1h", "1d"], default="1h")
    cryptocompare_parser.add_argument("--limit", type=int, default=2000)

    fear_greed_parser = subparsers.add_parser("fetch-fear-greed", help="Fetch Fear & Greed market sentiment data")
    fear_greed_parser.add_argument("--limit", type=int, default=30)


def handle_market_command(
    args: argparse.Namespace,
    *,
    pipeline: AlphaScopePipeline,
    repository: StorageRepository,
    aggregator: MarketDataAggregator,
    universe_builder: BinanceUniverseBuilder,
) -> bool:
    """Dispatch core market and pipeline commands."""
    return dispatch_command(
        args.command,
        MARKET_COMMAND_HANDLERS,
        args=args,
        pipeline=pipeline,
        repository=repository,
        aggregator=aggregator,
        universe_builder=universe_builder,
    )


def _handle_ingest_market(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    result = pipeline.ingest_market(parse_csv_argument(args.symbols), [args.interval], args.limit)
    frame = pd.DataFrame(result, columns=["symbol", "interval", "rows"])
    print_success("Ingestao concluida com sucesso.")
    print_table_from_dataframe(frame, title="Market Ingestion")


def _handle_build_universe(args: argparse.Namespace, universe_builder: BinanceUniverseBuilder, **_: Any) -> None:
    builder = universe_builder
    result = builder.build(
        top=args.top,
        quote_asset=args.quote,
        min_volume=args.min_volume,
        persist=True,
        output_path=Path(args.output_path) if args.output_path else None,
    )
    print_success(f"Universo automatico gerado com {len(result.selected_assets)} ativos selecionados.")
    print_kv_panel(
        "Automatic Universe",
        {
            "output_path": str(result.output_path),
            "selected_assets": len(result.selected_assets),
            "eligible_assets": len(result.all_assets),
            "quote_asset": args.quote.upper(),
            "min_volume": args.min_volume,
        },
    )
    print_table_from_dataframe(result.selected_assets, title="Automatic Market Universe", max_rows=min(args.top, 30))


def _handle_build_features(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    features = pipeline.build_features(parse_csv_argument(args.symbols), args.interval)
    print_success(f"{len(features)} linhas de features geradas.")
    columns = ["timestamp", "symbol", "close", "return_pct", "ma_short", "ma_long", "rsi", "volatility", "relative_volume", "momentum"]
    visible_columns = [column for column in columns if column in features.columns]
    print_table_from_dataframe(features.loc[:, visible_columns], title="Technical Features", max_rows=20)


def _handle_rank_assets(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    ranking = pipeline.rank_assets(parse_csv_argument(args.symbols), args.interval)
    print_success("Ranking atualizado.")
    print_table_from_dataframe(ranking, title="Asset Ranking")


def _handle_explain_ranking(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    explanation = pipeline.explain_ranking(parse_csv_argument(args.symbols), args.interval)
    if explanation.empty:
        print_warning("Nenhum ativo disponivel para explicar o ranking.")
        return
    print_success("Explicacao do ranking gerada.")
    columns = [
        "rank",
        "symbol",
        "score",
        "heuristic_score",
        "ml_probability",
        "news_score",
        "heuristic_contribution",
        "ml_contribution",
        "news_contribution",
        "momentum_component",
        "volume_component",
        "trend_component",
        "rsi_component",
    ]
    visible = [column for column in columns if column in explanation.columns]
    print_table_from_dataframe(explanation.loc[:, visible], title="Ranking Explanation", max_rows=args.limit)


def _handle_backtest(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    result = pipeline.backtest(args.symbol.upper(), args.interval)
    print_success(f"Backtest concluido para {args.symbol.upper()} {args.interval}.")
    print_backtest_result(metrics=result["metrics"], trades=result["trades"], equity_curve=result["equity_curve"])  # type: ignore[arg-type]


def _handle_paper_trade(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    result = pipeline.paper_trade(parse_csv_argument(args.symbols), args.interval)
    trades = pd.DataFrame(result["trades"])
    snapshot = result["snapshot"]
    if trades.empty:
        print_warning("Nenhum trade executado neste ciclo.")
    else:
        print_success(f"{len(trades)} trades simulados executados.")
        print_table_from_dataframe(trades, title="Paper Trades")
    print_snapshot(snapshot)


def _handle_run_pipeline(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    result = pipeline.run_pipeline(
        parse_csv_argument(args.symbols) if not args.use_auto_universe else None,
        args.interval,
        args.limit,
        use_auto_universe=args.use_auto_universe,
        universe_path=Path(args.universe_path) if args.universe_path else None,
    )
    print_success("Pipeline executado com sucesso.")
    print_pipeline_summary(result)
    print_kv_panel("Universe Source", {"mode": "automatic" if args.use_auto_universe else "manual", "assets": len(result.get("symbols", []))})
    ingestion_frame = pd.DataFrame(result["ingestion"])
    if not ingestion_frame.empty:
        print_section("Ingestion Details")
        print_table_from_dataframe(ingestion_frame, title="Pipeline Ingestion")


def _handle_run_loop(args: argparse.Namespace, pipeline: AlphaScopePipeline, **_: Any) -> None:
    from alphascope.runner import PipelineRunLoopConfig, PipelineRunner

    runner = PipelineRunner(pipeline=pipeline)
    config = PipelineRunLoopConfig(
        duration_minutes=args.duration,
        interval_seconds=args.interval,
        symbols=parse_csv_argument(args.symbols),
        timeframe=args.timeframe,
        limit=args.limit,
    )
    result = runner.run_loop(config)
    summary = runner.result_to_dict(result)
    print_success("Execution finished successfully.")
    print_kv_panel(
        "Pipeline Runner Summary",
        {
            "started_at": summary["started_at"],
            "finished_at": summary["finished_at"],
            "duration_minutes": summary["duration_minutes"],
            "interval_seconds": summary["interval_seconds"],
            "total_runs": summary["total_runs"],
            "successful_runs": summary["successful_runs"],
            "failed_runs": summary["failed_runs"],
            "timeframe": summary["timeframe"],
            "limit": summary["limit"],
            "symbols": ", ".join(summary["symbols"]),
        },
        border_style="green",
    )


def _handle_show_data(args: argparse.Namespace, repository: StorageRepository, **_: Any) -> None:
    data_type = args.type
    if data_type == "candles":
        frame = repository.get_candles(symbol=args.symbol.upper(), interval=args.interval, limit=args.limit)
        print_table_from_dataframe(frame, title=f"Candles | {args.symbol.upper()} | {args.interval}")
        return
    if data_type == "features":
        frame = repository.get_features(symbol=args.symbol.upper(), interval=args.interval)
        if not frame.empty:
            frame = frame.tail(args.limit).reset_index(drop=True)
        print_table_from_dataframe(frame, title=f"Features | {args.symbol.upper()} | {args.interval}")
        return
    if data_type == "ranking":
        frame = repository.get_latest_ranking(interval=args.interval)
        print_table_from_dataframe(frame, title=f"Latest Ranking | {args.interval}")
        return
    if data_type == "snapshot":
        snapshot = repository.get_latest_snapshot()
        if snapshot is None:
            print_warning("Nenhum snapshot encontrado.")
            return
        print_snapshot(snapshot)
        return
    if data_type == "open-positions":
        frame = repository.get_open_positions()
        print_table_from_dataframe(frame, title="Open Positions", max_rows=args.limit)
        return
    if data_type == "account":
        account = repository.get_live_account_view()
        print_kv_panel(
            "Live Account",
            {
                "exposure_pct": account.get("exposure_pct", 0.0),
                "open_positions_count": account.get("open_positions_count", 0),
                "total_balance": (account.get("account_snapshot", {}) or {}).get("total_balance"),
                "free_balance": (account.get("account_snapshot", {}) or {}).get("free_balance"),
                "open_orders": (account.get("account_snapshot", {}) or {}).get("open_orders"),
            },
        )
        positions = pd.DataFrame(account.get("open_positions", []))
        if not positions.empty:
            print_table_from_dataframe(positions, title="Open Positions", max_rows=args.limit)
        return
    if data_type == "live-trades":
        frame = repository.get_trade_executions(limit=args.limit)
        print_table_from_dataframe(frame, title="Live Trades", max_rows=args.limit)
        return
    raise ValueError(f"Unsupported show-data type: {data_type}")


def _handle_fetch_market_universe(args: argparse.Namespace, aggregator: MarketDataAggregator, **_: Any) -> None:
    fallback_sources = parse_csv_argument(args.fallback_sources) if args.fallback_sources else []
    universe = aggregator.fetch_market_universe(
        primary_source=args.primary_source.lower(),
        fallback_sources=[item.lower() for item in fallback_sources],
        limit=args.limit,
        persist=True,
    )
    print_success(f"Universo consolidado gerado com {len(universe)} ativos.")
    columns = ["source", "canonical_symbol", "symbol", "price", "volume_24h", "market_cap", "rank"]
    print_table_from_dataframe(universe.loc[:, columns], title="Consolidated Market Universe", max_rows=30)


def _handle_show_universe(
    args: argparse.Namespace,
    universe_builder: BinanceUniverseBuilder,
    aggregator: MarketDataAggregator,
    **_: Any,
) -> None:
    builder = universe_builder
    if args.kind == "auto":
        path = Path(args.path) if args.path else None
        universe = builder.load(path=path)
        if universe.empty:
            print_warning("Nenhum universo automatico salvo encontrado. Rode build-universe primeiro.")
            return
        frame = universe.copy()
        if args.selected_only and "selected" in frame.columns:
            frame = frame.loc[frame["selected"]].reset_index(drop=True)
        sort_column = "last_price" if args.sort_by == "price" else args.sort_by
        if sort_column not in frame.columns:
            raise ValueError(f"sort-by invalido para universo automatico: {args.sort_by}")
        ascending = sort_column in {"rank_volume", "symbol"}
        frame = frame.sort_values(sort_column, ascending=ascending, na_position="last").head(args.limit)
        print_table_from_dataframe(frame, title="Automatic Market Universe")
        return

    universe = aggregator.load_saved_universe()
    if universe.empty:
        print_warning("Nenhum universo consolidado salvo encontrado. Rode fetch-market-universe primeiro.")
        return
    frame = universe.copy()
    if args.source:
        frame = frame.loc[frame["source"] == args.source.lower()].reset_index(drop=True)
    sort_column = "price" if args.sort_by == "last_price" else args.sort_by
    if sort_column not in frame.columns:
        raise ValueError(f"sort-by invalido para universo consolidado: {args.sort_by}")
    ascending = sort_column in {"rank", "canonical_symbol", "symbol"}
    frame = frame.sort_values(sort_column, ascending=ascending, na_position="last").head(args.limit)
    print_table_from_dataframe(frame, title="Saved Consolidated Market Universe")


def _handle_run_auto_universe(
    args: argparse.Namespace,
    universe_builder: BinanceUniverseBuilder,
    pipeline: AlphaScopePipeline,
    **_: Any,
) -> None:
    builder = universe_builder
    universe_result = builder.build(
        top=args.top,
        quote_asset=args.quote,
        min_volume=args.min_volume,
        persist=True,
        output_path=Path(args.output_path) if args.output_path else None,
    )
    pipeline_result = pipeline.run_pipeline(
        symbols=None,
        interval=args.interval,
        limit=args.limit,
        use_auto_universe=True,
        universe_path=universe_result.output_path,
    )
    print_success("Pipeline executado com universo automatico.")
    print_kv_panel(
        "Automatic Universe Run",
        {
            "universe_path": str(universe_result.output_path),
            "selected_assets": len(universe_result.selected_assets),
            "interval": args.interval,
            "limit": args.limit,
        },
    )
    print_table_from_dataframe(universe_result.selected_assets, title="Selected Universe", max_rows=min(args.top, 20))
    print_pipeline_summary(pipeline_result)


def _handle_compare_sources(args: argparse.Namespace, aggregator: MarketDataAggregator, **_: Any) -> None:
    comparison = aggregator.compare_sources(symbol=args.symbol.upper() if args.symbol else None, limit=args.limit)
    if comparison.empty:
        print_warning("Nenhum dado disponivel para comparacao entre fontes.")
        return
    title = f"Source Comparison | {args.symbol.upper()}" if args.symbol else "Source Comparison"
    print_table_from_dataframe(comparison, title=title, max_rows=100)


def _handle_fetch_cryptocompare_history(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.data_sources.cryptocompare_client import CryptoCompareMarketDataClient
    from alphascope.datasets.parquet_utils import export_dataset

    client = CryptoCompareMarketDataClient()
    if args.interval == "1h":
        frame = client.fetch_hourly_history(args.symbol.upper(), quote_symbol=args.quote_symbol.upper(), limit=args.limit)
    else:
        frame = client.fetch_daily_history(args.symbol.upper(), quote_symbol=args.quote_symbol.upper(), limit=args.limit)
    output_path = settings.cryptocompare_raw_dir / f"{args.symbol.lower()}_{args.interval}.parquet"
    export_dataset(frame, output_path, include_csv=True)
    print_success(f"Historico CryptoCompare coletado: {len(frame)} linhas.")
    print_kv_panel("CryptoCompare History", {"path": str(output_path), "rows": len(frame), "symbol": args.symbol.upper()})
    print_table_from_dataframe(frame, title="CryptoCompare History", max_rows=20)


def _handle_fetch_fear_greed(args: argparse.Namespace, **_: Any) -> None:
    from alphascope.data_sources.fear_greed_client import FearGreedIndexClient
    from alphascope.datasets.parquet_utils import export_dataset

    frame = FearGreedIndexClient().fetch_fear_greed_index(limit=args.limit)
    output_path = settings.fear_greed_raw_dir / "fear_greed_latest.parquet"
    export_dataset(frame, output_path, include_csv=True)
    print_success(f"Fear & Greed coletado: {len(frame)} linhas.")
    print_kv_panel("Fear & Greed", {"path": str(output_path), "rows": len(frame)})
    print_table_from_dataframe(frame, title="Fear & Greed Index", max_rows=20)


MARKET_COMMAND_HANDLERS = {
    "ingest-market": _handle_ingest_market,
    "build-universe": _handle_build_universe,
    "build-features": _handle_build_features,
    "rank-assets": _handle_rank_assets,
    "explain-ranking": _handle_explain_ranking,
    "backtest": _handle_backtest,
    "paper-trade": _handle_paper_trade,
    "run-pipeline": _handle_run_pipeline,
    "run-loop": _handle_run_loop,
    "show-data": _handle_show_data,
    "fetch-market-universe": _handle_fetch_market_universe,
    "show-universe": _handle_show_universe,
    "run-auto-universe": _handle_run_auto_universe,
    "compare-sources": _handle_compare_sources,
    "fetch-cryptocompare-history": _handle_fetch_cryptocompare_history,
    "fetch-fear-greed": _handle_fetch_fear_greed,
}
