from __future__ import annotations

import pandas as pd


def ranking_table(ranking_df: pd.DataFrame) -> pd.DataFrame:
    if ranking_df.empty:
        return ranking_df
    preferred = [column for column in ["symbol", "predicted_probability", "score_high", "score_risk", "score_final", "confidence_score", "timestamp"] if column in ranking_df.columns]
    return ranking_df[preferred].copy()


def trade_table(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return trades_df
    preferred = [column for column in ["trade_id", "symbol", "entry_price", "exit_price", "quantity", "pnl", "status", "timestamp"] if column in trades_df.columns]
    return trades_df[preferred].copy()


def news_table(news_df: pd.DataFrame) -> pd.DataFrame:
    if news_df.empty:
        return news_df
    preferred = [column for column in ["title", "sentiment", "topic", "asset", "timestamp"] if column in news_df.columns]
    return news_df[preferred].copy()
