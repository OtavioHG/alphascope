from __future__ import annotations

import numpy as np
import pandas as pd


class AnomalyDetector:
    def __init__(self, rolling_window: int = 12, z_threshold: float = 2.5):
        self.rolling_window = rolling_window
        self.z_threshold = z_threshold

    def detect(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty:
            return pd.DataFrame(
                columns=["timestamp", "symbol", "anomaly_score", "anomaly_type", "anomaly_window", "affected_assets"]
            )

        frame = dataset.sort_values(["symbol", "timestamp"]).copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)

        frame["volume_zscore"] = self._rolling_zscore(frame, "relative_volume")
        frame["volatility_zscore"] = self._rolling_zscore(frame, "volatility")
        frame["return_zscore"] = self._rolling_zscore(frame, "pct_return")
        news_source = "news_count_window" if "news_count_window" in frame.columns else "news_count"
        frame["news_zscore"] = self._rolling_zscore(frame, news_source) if news_source in frame.columns else 0.0
        sentiment_source = "avg_sentiment_window" if "avg_sentiment_window" in frame.columns else "sentiment_score"
        frame["sentiment_zscore"] = self._rolling_zscore(frame, sentiment_source) if sentiment_source in frame.columns else 0.0

        anomaly_type: list[str] = []
        anomaly_score: list[float] = []
        for _, row in frame.iterrows():
            candidates = {
                "volume_spike": abs(float(row["volume_zscore"])),
                "volatility_spike": abs(float(row["volatility_zscore"])),
                "price_gap": abs(float(row["return_zscore"])),
                "news_burst": abs(float(row["news_zscore"])),
                "sentiment_shift": abs(float(row["sentiment_zscore"])),
            }
            label, score = max(candidates.items(), key=lambda item: item[1])
            anomaly_type.append(label if score >= self.z_threshold else "none")
            anomaly_score.append(round(score, 4))

        result = frame[["timestamp", "symbol"]].copy()
        result["anomaly_score"] = anomaly_score
        result["anomaly_type"] = anomaly_type
        result["anomaly_window"] = self.rolling_window
        result["affected_assets"] = result["symbol"].map(lambda value: [value])
        return result.loc[result["anomaly_type"] != "none"].reset_index(drop=True)

    def _rolling_zscore(self, frame: pd.DataFrame, column: str) -> pd.Series:
        if column not in frame.columns:
            return pd.Series(0.0, index=frame.index)
        series = frame[column].fillna(0.0)
        rolling_mean = series.groupby(frame["symbol"]).transform(
            lambda value: value.rolling(self.rolling_window, min_periods=3).mean()
        )
        rolling_std = series.groupby(frame["symbol"]).transform(
            lambda value: value.rolling(self.rolling_window, min_periods=3).std()
        ).replace(0.0, np.nan)
        return ((series - rolling_mean) / rolling_std).replace([np.inf, -np.inf], 0.0).fillna(0.0)
