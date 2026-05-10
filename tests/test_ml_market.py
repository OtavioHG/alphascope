from __future__ import annotations

import pandas as pd

from alphascope.config.settings import settings
from alphascope.ml.targets import future_return_target, up_move_target
from alphascope.ranking.scorer import apply_ranking_mode


def test_market_targets_respect_horizon_and_threshold() -> None:
    close = pd.Series([100.0, 101.0, 103.0, 106.0])
    returns = future_return_target(close, horizon_bars=1)
    target = up_move_target(close, horizon_bars=1, threshold_pct=0.015)

    assert round(float(returns.iloc[0]), 4) == 0.01
    assert int(target.iloc[0]) == 0
    assert int(target.iloc[1]) == 1


def test_apply_ranking_mode_hybrid_combines_scores() -> None:
    original_mode = settings.ranking_mode
    original_ml = settings.ranking_ml_weight
    original_heuristic = settings.ranking_heuristic_weight
    original_news = settings.ranking_news_weight
    object.__setattr__(settings, "ranking_mode", "hybrid")
    object.__setattr__(settings, "ranking_ml_weight", 0.7)
    object.__setattr__(settings, "ranking_heuristic_weight", 0.3)
    object.__setattr__(settings, "ranking_news_weight", 0.0)
    try:
        frame = pd.DataFrame({"score": [0.4], "ml_probability": [0.8]})
        scored = apply_ranking_mode(frame)
        assert round(float(scored.loc[0, "score"]), 4) == 0.68
    finally:
        object.__setattr__(settings, "ranking_mode", original_mode)
        object.__setattr__(settings, "ranking_ml_weight", original_ml)
        object.__setattr__(settings, "ranking_heuristic_weight", original_heuristic)
        object.__setattr__(settings, "ranking_news_weight", original_news)


def test_apply_ranking_mode_hybrid_includes_news_score_when_enabled() -> None:
    original_mode = settings.ranking_mode
    original_ml = settings.ranking_ml_weight
    original_heuristic = settings.ranking_heuristic_weight
    original_news = settings.ranking_news_weight
    object.__setattr__(settings, "ranking_mode", "hybrid")
    object.__setattr__(settings, "ranking_ml_weight", 0.6)
    object.__setattr__(settings, "ranking_heuristic_weight", 0.2)
    object.__setattr__(settings, "ranking_news_weight", 0.2)
    try:
        frame = pd.DataFrame({"score": [0.4], "ml_probability": [0.8], "news_score": [0.9]})
        scored = apply_ranking_mode(frame)
        assert round(float(scored.loc[0, "score"]), 4) == 0.74
    finally:
        object.__setattr__(settings, "ranking_mode", original_mode)
        object.__setattr__(settings, "ranking_ml_weight", original_ml)
        object.__setattr__(settings, "ranking_heuristic_weight", original_heuristic)
        object.__setattr__(settings, "ranking_news_weight", original_news)
