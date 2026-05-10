from __future__ import annotations

import pandas as pd
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:  # pragma: no cover - optional dependency
    class _Figure:
        def add_trace(self, *args, **kwargs):
            return None
        def update_layout(self, *args, **kwargs):
            return None
    class _GoShim:
        Figure = _Figure
        class Candlestick:
            def __init__(self, *args, **kwargs):
                pass
        class Scatter:
            def __init__(self, *args, **kwargs):
                pass
        class Bar:
            def __init__(self, *args, **kwargs):
                pass
        class Pie:
            def __init__(self, *args, **kwargs):
                pass
    go = _GoShim()
    def make_subplots(*args, **kwargs):
        return _Figure()


def candlestick_chart(market_df: pd.DataFrame, indicators_df: pd.DataFrame | None = None) -> go.Figure:
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.55, 0.2, 0.25],
    )
    if market_df.empty:
        return figure

    figure.add_trace(
        go.Candlestick(
            x=market_df["timestamp"],
            open=market_df["open"],
            high=market_df["high"],
            low=market_df["low"],
            close=market_df["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    if indicators_df is not None and not indicators_df.empty:
        for column, name in (("rsi", "RSI"), ("macd", "MACD"), ("macd_signal", "MACD Signal"), ("bb_upper", "BB Upper"), ("bb_lower", "BB Lower")):
            if column in indicators_df.columns:
                target_row = 2 if column == "rsi" else 1
                figure.add_trace(
                    go.Scatter(x=indicators_df["timestamp"], y=indicators_df[column], mode="lines", name=name),
                    row=target_row,
                    col=1,
                )

    if "volume" in market_df.columns:
        figure.add_trace(
            go.Bar(x=market_df["timestamp"], y=market_df["volume"], name="Volume"),
            row=3,
            col=1,
        )

    figure.update_layout(height=800, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20))
    return figure


def equity_curve(curve_df: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    if curve_df.empty:
        return figure
    y_column = None
    for candidate in ("equity", "total_equity", "capital", "available_balance", "cash"):
        if candidate in curve_df.columns:
            y_column = candidate
            break
    if y_column is None or "timestamp" not in curve_df.columns:
        return figure
    figure.add_trace(go.Scatter(x=curve_df["timestamp"], y=curve_df[y_column], mode="lines", name="Equity"))
    figure.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
    return figure


def indicator_chart(df: pd.DataFrame, x_column: str, y_columns: list[str], title: str) -> go.Figure:
    figure = go.Figure()
    if df.empty:
        return figure
    for column in y_columns:
        if column in df.columns:
            figure.add_trace(go.Scatter(x=df[x_column], y=df[column], mode="lines", name=column))
    figure.update_layout(title=title, height=320, margin=dict(l=20, r=20, t=40, b=20))
    return figure


def sentiment_distribution(news_df: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    if news_df.empty or "sentiment" not in news_df.columns:
        return figure
    counts = news_df["sentiment"].fillna("unknown").value_counts()
    figure.add_trace(go.Pie(labels=counts.index.tolist(), values=counts.values.tolist(), hole=0.4))
    figure.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
    return figure
