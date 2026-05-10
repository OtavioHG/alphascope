from __future__ import annotations

import pandas as pd


class RollingEvaluator:
    def __init__(self, window: int = 24, step: int = 12):
        self.window = window
        self.step = step

    def evaluate(self, dataset: pd.DataFrame, strategies: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty or strategies.empty:
            return pd.DataFrame()
        frame = dataset.sort_values("timestamp").copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)
        windows: list[dict[str, object]] = []
        max_start = max(1, len(frame) - self.window + 1)
        for _, strategy in strategies.iterrows():
            series = frame["pct_return"].fillna(0.0).reset_index(drop=True)
            rolling_scores: list[float] = []
            rolling_drawdowns: list[float] = []
            rolling_win_rates: list[float] = []
            rolling_profit_factor: list[float] = []
            for start in range(0, max_start, self.step):
                window_series = series.iloc[start : start + self.window]
                if len(window_series) < max(5, self.window // 3):
                    continue
                mean_return = float(window_series.mean())
                std_return = float(window_series.std(ddof=0))
                sharpe = mean_return / std_return if std_return > 0 else 0.0
                equity = (1.0 + window_series.clip(lower=-0.95)).cumprod()
                drawdown = float(abs(((equity / equity.cummax()) - 1.0).min()))
                positive = window_series[window_series > 0].sum()
                negative = abs(window_series[window_series < 0].sum())
                profit_factor = float(positive / negative) if negative > 0 else float(positive)
                rolling_scores.append(sharpe)
                rolling_drawdowns.append(drawdown)
                rolling_win_rates.append(float((window_series > 0).mean()))
                rolling_profit_factor.append(profit_factor)
            windows.append(
                {
                    "strategy_id": strategy["strategy_id"],
                    "rolling_sharpe": float(pd.Series(rolling_scores).mean()) if rolling_scores else 0.0,
                    "rolling_drawdown": float(pd.Series(rolling_drawdowns).mean()) if rolling_drawdowns else 0.0,
                    "rolling_win_rate": float(pd.Series(rolling_win_rates).mean()) if rolling_win_rates else 0.0,
                    "rolling_profit_factor": float(pd.Series(rolling_profit_factor).mean()) if rolling_profit_factor else 0.0,
                    "window_count": len(rolling_scores),
                }
            )
        return pd.DataFrame(windows)
