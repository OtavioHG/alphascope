from __future__ import annotations

import math

import numpy as np
import pandas as pd


class SignalMiner:
    def __init__(self, future_horizon: int = 4):
        self.future_horizon = future_horizon

    def mine(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty:
            return pd.DataFrame()

        frame = dataset.sort_values(["symbol", "timestamp"]).copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)
        frame["future_return"] = frame.groupby("symbol")["close"].shift(-self.future_horizon) / frame["close"] - 1.0
        frame["sma_fast"] = frame.get("sma_20", frame["close"].rolling(20, min_periods=3).mean())
        frame["sma_slow"] = frame.get("sma_50", frame["close"].rolling(50, min_periods=3).mean())
        frame["signal_breakout"] = (frame["close"] > frame["sma_fast"]).astype(int)

        templates = {
            "rsi_oversold_volume_sentiment": (
                (frame.get("rsi", pd.Series(50.0, index=frame.index)) <= 35)
                & (frame.get("relative_volume", pd.Series(1.0, index=frame.index)) >= 1.15)
                & (frame.get("sentiment_score", pd.Series(0.0, index=frame.index)) >= 0.05)
            ),
            "breakout_news_volatility": (
                (frame["signal_breakout"] == 1)
                & (frame.get("news_count_window", pd.Series(0.0, index=frame.index)) >= 1)
                & (frame.get("volatility", pd.Series(0.0, index=frame.index)).between(0.005, 0.05))
            ),
            "sma_macd_bullish": (
                (frame["sma_fast"] > frame["sma_slow"])
                & (
                    frame.get("macd", pd.Series(0.0, index=frame.index))
                    > frame.get("macd_signal", pd.Series(0.0, index=frame.index))
                )
            ),
        }

        results: list[dict[str, object]] = []
        for signal_name, mask in templates.items():
            subset = frame.loc[mask & frame["future_return"].notna()].copy()
            if subset.empty:
                continue
            per_symbol = subset.groupby("symbol")["future_return"].agg(["mean", "std", "count"]).reset_index()
            avg_return = float(subset["future_return"].mean())
            volatility = float(subset["future_return"].std(ddof=0)) if len(subset) > 1 else 0.0
            sharpe = avg_return / volatility if volatility > 0 else 0.0
            cumulative = (1.0 + subset["future_return"].clip(lower=-0.95)).cumprod()
            drawdown = ((cumulative / cumulative.cummax()) - 1.0).min() if not cumulative.empty else 0.0
            stability = self._stability_score(per_symbol["mean"].tolist(), int(per_symbol["count"].sum()))
            results.append(
                {
                    "signal_definition": signal_name,
                    "sample_count": int(len(subset)),
                    "win_rate": float((subset["future_return"] > 0).mean()),
                    "avg_return": avg_return,
                    "sharpe": float(sharpe),
                    "max_drawdown": float(abs(drawdown)),
                    "stability_score": stability,
                    "asset_count": int(subset["symbol"].nunique()),
                }
            )

        if not results:
            return pd.DataFrame(
                columns=[
                    "signal_definition",
                    "sample_count",
                    "win_rate",
                    "avg_return",
                    "sharpe",
                    "max_drawdown",
                    "stability_score",
                    "asset_count",
                ]
            )
        return pd.DataFrame(results).sort_values(["stability_score", "sharpe"], ascending=False).reset_index(drop=True)

    @staticmethod
    def _stability_score(per_symbol_returns: list[float], sample_count: int) -> float:
        if not per_symbol_returns:
            return 0.0
        mean_return = float(np.mean(per_symbol_returns))
        dispersion = float(np.std(per_symbol_returns))
        sample_bonus = min(1.0, math.log1p(sample_count) / 5.0)
        return round(max(0.0, (mean_return + 0.05) * sample_bonus - dispersion), 4)
