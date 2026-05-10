from __future__ import annotations

from pathlib import Path

import pandas as pd


def _normalize_series(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    minimum = float(series.min())
    maximum = float(series.max())
    if maximum - minimum == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - minimum) / (maximum - minimum)


def build_asset_ranking(predictions_df: pd.DataFrame) -> pd.DataFrame:
    if predictions_df.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "score_high",
                "score_risk",
                "score_final",
                "predicted_label",
                "predicted_probability",
                "confidence_score",
                "timestamp",
            ]
        )

    ranking = predictions_df.copy()
    volatility = ranking["volatility"] if "volatility" in ranking.columns else pd.Series([0.0] * len(ranking))
    relative_volume = ranking["relative_volume"] if "relative_volume" in ranking.columns else pd.Series([0.0] * len(ranking))
    normalized_volatility = _normalize_series(volatility.astype(float))
    normalized_liquidity = _normalize_series(relative_volume.astype(float))

    ranking["score_high"] = ranking["predicted_probability"].clip(0.0, 1.0)
    ranking["score_risk"] = ((0.7 * normalized_volatility) + (0.3 * (1.0 - normalized_liquidity))).clip(0.0, 1.0)
    ranking["score_final"] = (ranking["score_high"] * (1.0 - ranking["score_risk"])).clip(0.0, 1.0)

    columns = [
        "symbol",
        "score_high",
        "score_risk",
        "score_final",
        "predicted_label",
        "predicted_probability",
        "confidence_score",
        "timestamp",
    ]
    return ranking.sort_values("score_final", ascending=False)[columns].reset_index(drop=True)


def export_ranking_csv(ranking_df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ranking_df.to_csv(path, index=False)
    return path
