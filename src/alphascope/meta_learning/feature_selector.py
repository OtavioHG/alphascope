from __future__ import annotations

import pandas as pd


class FeatureSelector:
    def select(self, dataset: pd.DataFrame, candidate_columns: list[str], top_k: int = 5) -> list[str]:
        if dataset.empty:
            return []
        available = [column for column in candidate_columns if column in dataset.columns]
        if not available:
            return []
        scored: list[tuple[str, float]] = []
        target = dataset["close"].pct_change().shift(-1) if "close" in dataset.columns else None
        for column in available:
            series = pd.to_numeric(dataset[column], errors="coerce")
            if target is None:
                score = float(series.abs().mean())
            else:
                aligned = pd.concat([series, target], axis=1).dropna()
                score = abs(float(aligned.corr().iloc[0, 1])) if len(aligned) > 3 else 0.0
            scored.append((column, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [column for column, _ in scored[:top_k]]
