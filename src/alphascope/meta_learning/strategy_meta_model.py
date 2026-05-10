from __future__ import annotations

import pandas as pd


class StrategyMetaModel:
    def recommend(self, ranked_strategies: pd.DataFrame, regimes: pd.DataFrame | None = None) -> pd.DataFrame:
        if ranked_strategies.empty:
            return pd.DataFrame()
        dominant_regime = "any"
        if regimes is not None and not regimes.empty:
            dominant_regime = str(regimes["regime_label"].mode().iloc[0])
        recommendations = ranked_strategies.head(5).copy()
        recommendations["recommended_regime"] = dominant_regime
        recommendations["recommended_model"] = recommendations["promotion_status"].map(
            {"candidate": "gradient_boosting", "research_only": "logistic_regression", "promoted": "random_forest"}
        ).fillna("gradient_boosting")
        return recommendations
