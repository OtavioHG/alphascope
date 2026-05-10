from __future__ import annotations

import pandas as pd


class RegimeDetector:
    def __init__(self, trend_window: int = 12, volatility_window: int = 12):
        self.trend_window = trend_window
        self.volatility_window = volatility_window

    def detect(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty:
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "symbol",
                    "regime_label",
                    "regime_confidence",
                    "trend_strength",
                    "volatility_level",
                    "liquidity_level",
                    "news_intensity",
                ]
            )

        frame = dataset.sort_values(["symbol", "timestamp"]).copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)
        frame["trend_strength"] = (
            frame.groupby("symbol")["pct_return"]
            .transform(lambda series: series.rolling(self.trend_window, min_periods=3).mean())
            .fillna(0.0)
        )
        frame["volatility_level"] = (
            frame.groupby("symbol")["pct_return"]
            .transform(lambda series: series.rolling(self.volatility_window, min_periods=3).std())
            .fillna(0.0)
        )
        frame["liquidity_level"] = frame.get("relative_volume", pd.Series(1.0, index=frame.index)).fillna(1.0)
        frame["news_intensity"] = frame.get("news_count_window", pd.Series(0.0, index=frame.index)).fillna(0.0)
        frame["sentiment_shift"] = frame.get(
            "avg_sentiment_window",
            frame.get("sentiment_score", pd.Series(0.0, index=frame.index)),
        ).fillna(0.0)

        labels: list[str] = []
        confidences: list[float] = []
        for _, row in frame.iterrows():
            label = "sideways"
            confidence = 0.55
            trend = float(row["trend_strength"])
            volatility = float(row["volatility_level"])
            liquidity = float(row["liquidity_level"])
            news_intensity = float(row["news_intensity"])
            sentiment_shift = float(row["sentiment_shift"])

            if liquidity < 0.65:
                label = "low_liquidity"
                confidence = min(0.95, 0.55 + (0.65 - liquidity))
            elif news_intensity >= 2 and abs(sentiment_shift) >= 0.15:
                label = "news_driven"
                confidence = min(0.95, 0.6 + abs(sentiment_shift))
            elif volatility >= 0.04:
                label = "high_volatility"
                confidence = min(0.95, 0.6 + volatility * 3)
            elif trend >= 0.01:
                label = "bullish"
                confidence = min(0.95, 0.6 + trend * 10)
            elif trend <= -0.01:
                label = "bearish"
                confidence = min(0.95, 0.6 + abs(trend) * 10)
            else:
                label = "sideways"
                confidence = 0.6 - min(0.2, volatility)

            labels.append(label)
            confidences.append(round(max(0.5, confidence), 4))

        result = frame[["timestamp", "symbol", "trend_strength", "volatility_level", "liquidity_level", "news_intensity"]].copy()
        result["regime_label"] = labels
        result["regime_confidence"] = confidences
        result["regime_features"] = result.apply(
            lambda row: {
                "trend_strength": round(float(row["trend_strength"]), 6),
                "volatility_level": round(float(row["volatility_level"]), 6),
                "liquidity_level": round(float(row["liquidity_level"]), 6),
                "news_intensity": round(float(row["news_intensity"]), 6),
            },
            axis=1,
        )
        return result[
            [
                "timestamp",
                "symbol",
                "regime_label",
                "regime_confidence",
                "regime_features",
                "trend_strength",
                "volatility_level",
                "liquidity_level",
                "news_intensity",
            ]
        ]
