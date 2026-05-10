from __future__ import annotations

from alphascope.dashboard._optional import st

from alphascope.dashboard.components.charts import candlestick_chart, indicator_chart
from alphascope.dashboard.services.data_service import DashboardDataService
from alphascope.dashboard.services.ranking_service import RankingService


def render() -> None:
    st.title("Market Analysis")
    data_service = DashboardDataService()
    ranking_service = RankingService()

    symbols = data_service.get_available_symbols() or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    selected_symbol = st.selectbox("Asset", symbols, index=0)
    selected_interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)

    market_df = data_service.load_candles(selected_symbol.replace("USDT", "/USDT") if "/" not in selected_symbol else selected_symbol)
    if market_df.empty:
        market_df = data_service.filter_market_data(selected_symbol, selected_interval)
    features_df = data_service.load_features(selected_symbol.replace("USDT", "/USDT") if "/" not in selected_symbol else selected_symbol)
    if features_df.empty:
        features_df = data_service.filter_market_data(selected_symbol, selected_interval)

    st.plotly_chart(candlestick_chart(market_df, features_df), use_container_width=True)

    ranking = ranking_service.load_latest_ranking()
    latest_asset = ranking.loc[ranking["symbol"] == selected_symbol] if not ranking.empty and "symbol" in ranking.columns else ranking
    probability = float(latest_asset["predicted_probability"].iloc[0]) if not latest_asset.empty and "predicted_probability" in latest_asset.columns else 0.0
    st.metric("Model Probability", round(probability, 4))

    left, right = st.columns(2)
    with left:
        st.plotly_chart(indicator_chart(features_df, "timestamp", ["rsi"], "RSI"), use_container_width=True)
    with right:
        st.plotly_chart(indicator_chart(features_df, "timestamp", ["macd", "macd_signal"], "MACD"), use_container_width=True)
