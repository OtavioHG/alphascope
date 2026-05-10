"""Optuna objective for AlphaScope strategy optimization."""

from __future__ import annotations

import pandas as pd

from alphascope.backtest.engine import BacktestEngine
from alphascope.backtest.strategy import ThresholdStrategy
from alphascope.features.technical import compute_technical_features
from alphascope.ranking.scorer import score_timeseries
from alphascope.storage.repositories import StorageRepository


def build_objective(repository: StorageRepository, symbol: str, interval: str):
    """Create an Optuna objective bound to one symbol and interval."""

    candles = repository.get_candles(symbol=symbol, interval=interval)
    if candles.empty:
        raise RuntimeError(f"No candles available for {symbol} {interval}")

    def objective(trial) -> float:
        short_window = trial.suggest_int("short_window", 5, 15)
        long_window = trial.suggest_int("long_window", short_window + 5, 40)
        rsi_window = trial.suggest_int("rsi_window", 7, 21)
        volatility_window = trial.suggest_int("volatility_window", 10, 30)
        volume_window = trial.suggest_int("volume_window", 10, 30)
        momentum_window = trial.suggest_int("momentum_window", 3, 12)
        buy_threshold = trial.suggest_float("buy_threshold", 0.55, 0.80)
        sell_threshold = trial.suggest_float("sell_threshold", 0.20, 0.45)
        fee_rate = trial.suggest_float("fee_rate", 0.0005, 0.003)

        features = compute_technical_features(
            candles=candles,
            short_window=short_window,
            long_window=long_window,
            rsi_window=rsi_window,
            volatility_window=volatility_window,
            volume_window=volume_window,
            momentum_window=momentum_window,
        )
        if features.empty:
            return -1.0
        scored = score_timeseries(features)
        dataset = candles.merge(scored[["timestamp", "symbol", "score"]], on=["timestamp", "symbol"], how="inner")
        if dataset.empty:
            return -1.0
        signal_frame = ThresholdStrategy(buy_threshold=buy_threshold, sell_threshold=sell_threshold).generate_signals(dataset)
        result = BacktestEngine(initial_cash=10_000.0, fee_rate=fee_rate).run(signal_frame)
        metrics = result["metrics"]
        objective_value = (
            float(metrics["cumulative_return"])
            + (float(metrics["profit_factor"]) * 0.05 if metrics["profit_factor"] != float("inf") else 0.25)
            + (float(metrics["win_rate"]) * 0.10)
            + (float(metrics["max_drawdown"]) * 0.50)
        )
        return objective_value

    return objective
