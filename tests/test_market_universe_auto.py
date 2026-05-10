from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd

from alphascope.cli import build_parser
from alphascope.core.pipeline import AlphaScopePipeline
from alphascope.universe.builder import BinanceUniverseBuilder


def test_binance_universe_builder_filters_and_ranks_assets() -> None:
    builder = BinanceUniverseBuilder()
    builder._fetch_exchange_info = lambda: pd.DataFrame(  # type: ignore[method-assign]
        [
            {"symbol": "BTCUSDT", "base_asset": "BTC", "quote_asset": "USDT", "status": "TRADING"},
            {"symbol": "ETHUSDT", "base_asset": "ETH", "quote_asset": "USDT", "status": "TRADING"},
            {"symbol": "USDCUSDT", "base_asset": "USDC", "quote_asset": "USDT", "status": "TRADING"},
            {"symbol": "BTCUPUSDT", "base_asset": "BTCUP", "quote_asset": "USDT", "status": "TRADING"},
            {"symbol": "XRPBUSD", "base_asset": "XRP", "quote_asset": "BUSD", "status": "TRADING"},
            {"symbol": "ADAUSDT", "base_asset": "ADA", "quote_asset": "USDT", "status": "BREAK"},
        ]
    )
    builder._fetch_ticker_24h = lambda: pd.DataFrame(  # type: ignore[method-assign]
        [
            {"symbol": "BTCUSDT", "volume_24h": "15000000", "last_price": "70000"},
            {"symbol": "ETHUSDT", "volume_24h": "12000000", "last_price": "3500"},
            {"symbol": "USDCUSDT", "volume_24h": "50000000", "last_price": "1"},
            {"symbol": "BTCUPUSDT", "volume_24h": "18000000", "last_price": "8"},
            {"symbol": "ADAUSDT", "volume_24h": "22000000", "last_price": "0.7"},
        ]
    )

    output_dir = Path("data/processed/test_auto_universe")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = builder.build(
        top=2,
        quote_asset="USDT",
        min_volume=10_000_000,
        persist=True,
        output_path=output_dir / "universe.csv",
    )

    assert result.output_path == output_dir / "universe.csv"
    assert result.selected_assets["symbol"].tolist() == ["BTCUSDT", "ETHUSDT"]
    assert result.selected_assets["rank_volume"].tolist() == [1, 2]
    assert result.selected_assets["selected"].tolist() == [True, True]

    persisted = pd.read_csv(result.output_path)
    assert persisted["symbol"].tolist() == ["BTCUSDT", "ETHUSDT"]
    shutil.rmtree(output_dir)


def test_pipeline_resolves_symbols_from_saved_auto_universe() -> None:
    class DummyRepository:
        pass

    pipeline = AlphaScopePipeline(repository=DummyRepository())  # type: ignore[arg-type]
    pipeline.universe_builder.load = lambda path=None: pd.DataFrame(  # type: ignore[method-assign]
        [
            {"symbol": "BTCUSDT", "selected": True},
            {"symbol": "ETHUSDT", "selected": True},
            {"symbol": "XRPUSDT", "selected": False},
        ]
    )

    resolved = pipeline.resolve_symbols(symbols=None, use_auto_universe=True)

    assert resolved == ["BTCUSDT", "ETHUSDT"]


def test_cli_parser_supports_auto_universe_commands() -> None:
    parser = build_parser()

    build_args = parser.parse_args(["build-universe", "--top", "150", "--quote", "USDT", "--min-volume", "5000000"])
    run_args = parser.parse_args(["run-auto-universe", "--top", "120", "--interval", "1h", "--limit", "300"])
    pipeline_args = parser.parse_args(["run-pipeline", "--use-auto-universe", "--interval", "4h"])

    assert build_args.command == "build-universe"
    assert build_args.top == 150
    assert run_args.command == "run-auto-universe"
    assert run_args.limit == 300
    assert pipeline_args.use_auto_universe is True
