"""Scoring logic for asset ranking."""

from __future__ import annotations

import numpy as np
import pandas as pd

from alphascope.config.settings import settings


def score_assets(features: pd.DataFrame) -> pd.DataFrame:
    """Score the latest feature row per asset using cross-sectional normalization."""
    if features.empty:
        return pd.DataFrame()

    dataset = features.copy().reset_index(drop=True)
    dataset["momentum_component"] = _rank_to_unit(dataset["momentum"])
    dataset["volume_component"] = _rank_to_unit(dataset["relative_volume"])
    dataset["trend_component"] = _rank_to_unit(dataset["trend_strength"])
    dataset["rsi_component"] = dataset["rsi"].apply(_score_rsi)
    dataset["score"] = (
        dataset["momentum_component"] * 0.35
        + dataset["volume_component"] * 0.20
        + dataset["trend_component"] * 0.25
        + dataset["rsi_component"] * 0.20
    )
    dataset = apply_ranking_mode(dataset)
    dataset = adjust_score_with_market_sentiment(dataset)
    dataset = ensure_score_column(dataset)
    return dataset


def score_timeseries(features: pd.DataFrame) -> pd.DataFrame:
    """Score a historical feature frame row by row for backtesting."""
    if features.empty:
        return pd.DataFrame()

    dataset = features.copy()
    dataset["momentum_component"] = dataset["momentum"].apply(lambda value: _clip_unit((float(value) + 0.1) / 0.2))
    dataset["volume_component"] = dataset["relative_volume"].apply(lambda value: _clip_unit(float(value) / 2.0))
    dataset["trend_component"] = dataset["trend_strength"].apply(lambda value: _clip_unit((float(value) + 0.05) / 0.10))
    dataset["rsi_component"] = dataset["rsi"].apply(_score_rsi)
    dataset["score"] = (
        dataset["momentum_component"] * 0.35
        + dataset["volume_component"] * 0.20
        + dataset["trend_component"] * 0.25
        + dataset["rsi_component"] * 0.20
    )
    dataset = apply_ranking_mode(dataset)
    dataset = adjust_score_with_market_sentiment(dataset)
    dataset = ensure_score_column(dataset)
    return dataset


def apply_ranking_mode(dataset: pd.DataFrame) -> pd.DataFrame:
    """Apply heuristic, ML or hybrid ranking mode."""
    mode = settings.ranking_mode.strip().lower()
    dataset = dataset.copy()
    dataset["score"] = _resolve_score_series(dataset)
    if mode == "heuristic":
        dataset["heuristic_score"] = dataset["score"]
        return dataset
    if "ml_probability" not in dataset.columns:
        dataset["heuristic_score"] = dataset["score"]
        return dataset
    if mode == "ml":
        dataset["score"] = _numeric_series(dataset["ml_probability"])
        dataset["heuristic_score"] = _resolve_score_series(dataset, fallback_columns=("final_score",), default=0.0)
        return dataset
    if mode in {"hybrid", "hybrid_with_news"}:
        dataset["heuristic_score"] = _resolve_score_series(dataset, fallback_columns=("final_score",), default=0.0)
        components = [
            ("heuristic_score", settings.ranking_heuristic_weight),
            ("ml_probability", settings.ranking_ml_weight),
        ]
        if "news_score" in dataset.columns and settings.ranking_news_weight > 0:
            components.append(("news_score", settings.ranking_news_weight))
        if mode == "hybrid_with_news" and "news_score" not in dataset.columns:
            return dataset
        weighted_total = 0.0
        total_weight = 0.0
        for column, weight in components:
            if weight <= 0 or column not in dataset.columns:
                continue
            weighted_total += _numeric_series(dataset[column]) * weight
            total_weight += weight
        if total_weight > 0:
            dataset["score"] = weighted_total / total_weight
        dataset = ensure_score_column(dataset)
        return dataset
    return dataset


def adjust_score_with_market_sentiment(dataset: pd.DataFrame) -> pd.DataFrame:
    """Apply a small contrarian adjustment based on market-wide fear and greed."""
    if dataset.empty:
        return dataset
    adjusted = ensure_score_column(dataset)
    if "fear_greed_value" not in dataset.columns and "fear_greed_label" not in dataset.columns:
        return adjusted
    sentiment_delta = pd.Series(0.0, index=adjusted.index, dtype=float)
    if "fear_greed_label" in adjusted.columns:
        labels = adjusted["fear_greed_label"].fillna("").astype(str).str.lower()
        sentiment_delta = sentiment_delta.mask(labels.eq("extreme fear"), 0.05)
        sentiment_delta = sentiment_delta.mask(labels.eq("fear"), 0.02)
        sentiment_delta = sentiment_delta.mask(labels.eq("greed"), -0.02)
        sentiment_delta = sentiment_delta.mask(labels.eq("extreme greed"), -0.05)
    if "fear_greed_value" in adjusted.columns:
        values = pd.to_numeric(adjusted["fear_greed_value"], errors="coerce")
        sentiment_delta = sentiment_delta.mask(values.le(25), 0.05)
        sentiment_delta = sentiment_delta.mask(values.between(26, 40), 0.02)
        sentiment_delta = sentiment_delta.mask(values.between(60, 74), -0.02)
        sentiment_delta = sentiment_delta.mask(values.ge(75), -0.05)
    adjusted["market_sentiment_adjustment"] = sentiment_delta
    adjusted["score"] = (_numeric_series(adjusted["score"]) + sentiment_delta).clip(0.0, 1.0)
    return adjusted


def ensure_score_column(dataset: pd.DataFrame) -> pd.DataFrame:
    """Normalize the final ranking output to the mandatory `score` column."""
    if dataset.empty:
        return dataset.copy()
    normalized = dataset.copy()
    normalized["score"] = _resolve_score_series(
        normalized,
        fallback_columns=("final_score", "heuristic_score", "ml_probability", "news_score"),
        default=0.0,
    )
    return normalized


def _rank_to_unit(series: pd.Series) -> pd.Series:
    if series.nunique(dropna=False) <= 1:
        return pd.Series(0.5, index=series.index, dtype=float)
    return series.rank(method="average", pct=True)


def _score_rsi(value: float) -> float:
    distance = abs(float(value) - 55.0)
    return float(np.clip(1.0 - (distance / 55.0), 0.0, 1.0))


def _clip_unit(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _numeric_series(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default).astype(float)


def _resolve_score_series(
    dataset: pd.DataFrame,
    fallback_columns: tuple[str, ...] = ("final_score",),
    default: float = 0.0,
) -> pd.Series:
    score = pd.to_numeric(dataset["score"], errors="coerce") if "score" in dataset.columns else None
    for column in fallback_columns:
        if column not in dataset.columns:
            continue
        candidate = pd.to_numeric(dataset[column], errors="coerce")
        if score is None:
            score = candidate
        else:
            score = score.where(score.notna(), candidate)
    if score is None:
        score = pd.Series(default, index=dataset.index, dtype=float)
    return score.fillna(default).astype(float)
