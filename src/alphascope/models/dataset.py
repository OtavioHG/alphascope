from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd

from alphascope.domain.model_schemas import TemporalSplitConfig

DEFAULT_FEATURE_COLUMNS = [
    "rsi",
    "macd",
    "macd_signal",
    "bb_upper",
    "bb_lower",
    "sma_20",
    "sma_50",
    "pct_return",
    "volatility",
    "relative_volume",
    "sentiment_score",
    "topic_score",
    "news_count_window",
    "avg_sentiment_window",
    "distance_sma20",
    "distance_sma50",
    "bollinger_band_width",
    "sma20_above_sma50",
    "recent_momentum",
    "volume_deviation",
]

LEAKAGE_COLUMNS = {
    "target",
    "future_close",
    "future_return",
    "future_timestamp",
    "predicted_label",
    "predicted_probability",
    "confidence_score",
}


class Phase3DatasetBuilder:
    def __init__(self, feature_columns: list[str] | None = None):
        self.feature_columns = feature_columns or DEFAULT_FEATURE_COLUMNS

    def load_dataset(self, dataset_path: str) -> pd.DataFrame:
        dataset = pd.read_csv(dataset_path)
        return self.prepare_dataset(dataset)

    def prepare_dataset(
        self,
        df: pd.DataFrame,
        symbol: str | None = None,
        interval: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        dataset = self._normalize_columns(df.copy())
        dataset["timestamp"] = pd.to_datetime(dataset["timestamp"], utc=True, errors="coerce")

        if symbol:
            dataset = dataset.loc[dataset["symbol"] == symbol].copy()
        if interval and "interval" in dataset.columns:
            dataset = dataset.loc[dataset["interval"] == interval].copy()
        if start:
            dataset = dataset.loc[dataset["timestamp"] >= pd.to_datetime(start, utc=True, errors="coerce")].copy()
        if end:
            dataset = dataset.loc[dataset["timestamp"] <= pd.to_datetime(end, utc=True, errors="coerce")].copy()

        dataset = dataset.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        dataset = self._add_topic_features(dataset)
        dataset = self._add_derived_features(dataset)
        dataset = self._fill_missing_values(dataset)
        return dataset

    def infer_feature_columns(self, df: pd.DataFrame) -> list[str]:
        columns = [column for column in self.feature_columns if column in df.columns]
        if not columns:
            raise ValueError("No supported feature columns were found in the dataset")
        return columns

    def remove_leakage_columns(
        self,
        df: pd.DataFrame,
        extra_exclusions: set[str] | None = None,
    ) -> pd.DataFrame:
        exclusions = set(LEAKAGE_COLUMNS)
        if extra_exclusions:
            exclusions |= extra_exclusions
        return df[[column for column in df.columns if column not in exclusions]].copy()

    def temporal_split(
        self,
        df: pd.DataFrame,
        config: TemporalSplitConfig | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        split_config = config or TemporalSplitConfig()
        split_config.validate()
        ordered = df.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
        total_rows = len(ordered)
        train_end = int(total_rows * split_config.train_ratio)
        validation_end = train_end + int(total_rows * split_config.validation_ratio)
        if train_end <= 0 or validation_end <= train_end or validation_end >= total_rows:
            raise ValueError("Temporal split ratios produced empty partitions")
        return (
            ordered.iloc[:train_end].copy(),
            ordered.iloc[train_end:validation_end].copy(),
            ordered.iloc[validation_end:].copy(),
        )

    def walk_forward_splits(
        self,
        df: pd.DataFrame,
        train_size: int,
        validation_size: int,
        step_size: int,
    ) -> Iterator[tuple[pd.DataFrame, pd.DataFrame]]:
        ordered = df.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
        start = 0
        while start + train_size + validation_size <= len(ordered):
            yield (
                ordered.iloc[start : start + train_size].copy(),
                ordered.iloc[start + train_size : start + train_size + validation_size].copy(),
            )
            start += step_size

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        dataset = df.rename(
            columns={
                "ma_short": "sma_20",
                "ma_long": "sma_50",
                "sentiment_avg": "avg_sentiment_window",
                "sentiment_count": "news_count_window",
                "close_price": "close",
                "open_price": "open",
                "high_price": "high",
                "low_price": "low",
            }
        )
        if "news_count_window" not in dataset.columns:
            dataset["news_count_window"] = 0.0
        if "avg_sentiment_window" not in dataset.columns:
            dataset["avg_sentiment_window"] = 0.0
        if "sentiment_score" not in dataset.columns:
            dataset["sentiment_score"] = dataset["avg_sentiment_window"]
        return dataset

    def _add_topic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        topic_column = next(
            (candidate for candidate in ("top_topic", "topic", "topic_label") if candidate in df.columns),
            None,
        )
        if topic_column is None:
            df["topic_score"] = 0.0
            return df

        categories = pd.Categorical(df[topic_column].fillna("unknown"))
        codes = categories.codes.astype(float)
        max_code = float(np.max(codes)) if len(codes) else 0.0
        df["topic_score"] = 0.0 if max_code <= 0 else codes / max_code
        return df

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        grouped = df.groupby("symbol", group_keys=False)
        if {"close", "sma_20"}.issubset(df.columns):
            df["distance_sma20"] = (df["close"] - df["sma_20"]) / df["sma_20"].replace(0, np.nan)
        if {"close", "sma_50"}.issubset(df.columns):
            df["distance_sma50"] = (df["close"] - df["sma_50"]) / df["sma_50"].replace(0, np.nan)
        if {"bb_upper", "bb_lower", "close"}.issubset(df.columns):
            df["bollinger_band_width"] = (df["bb_upper"] - df["bb_lower"]) / df["close"].replace(0, np.nan)
        if {"sma_20", "sma_50"}.issubset(df.columns):
            df["sma20_above_sma50"] = (df["sma_20"] > df["sma_50"]).astype(float)
        if "close" in df.columns:
            df["recent_momentum"] = grouped["close"].pct_change(periods=3)
        if "volume" in df.columns:
            rolling_volume = grouped["volume"].transform(lambda series: series.rolling(20, min_periods=1).mean())
            df["volume_deviation"] = (df["volume"] - rolling_volume) / rolling_volume.replace(0, np.nan)
        return df

    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        fill_columns = [column for column in self.feature_columns if column in df.columns]
        df[fill_columns] = df.groupby("symbol")[fill_columns].ffill().fillna(0.0)
        for column in fill_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
        return df


def split_summary(
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, int]:
    return {
        "train_rows": len(train_df),
        "validation_rows": len(validation_df),
        "test_rows": len(test_df),
    }
