from __future__ import annotations

from alphascope.dashboard._optional import st

from alphascope.dashboard.components.charts import indicator_chart, sentiment_distribution
from alphascope.dashboard.components.tables import news_table
from alphascope.dashboard.services.data_service import DashboardDataService


def render() -> None:
    st.title("News Sentiment")
    service = DashboardDataService()
    news_df = service.load_recent_news(limit=100)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(sentiment_distribution(news_df), use_container_width=True)
    with right:
        if not news_df.empty and "asset" in news_df.columns:
            sentiment_by_asset = news_df.groupby("asset", as_index=False)["sentiment_score"].mean() if "sentiment_score" in news_df.columns else news_df.groupby("asset", as_index=False).size()
            value_cols = [column for column in sentiment_by_asset.columns if column != "asset"]
            st.plotly_chart(indicator_chart(sentiment_by_asset, "asset", value_cols, "Average Sentiment by Asset"), use_container_width=True)
        else:
            st.info("No sentiment distribution available")

    if not news_df.empty and "timestamp" in news_df.columns:
        volume_df = news_df.copy()
        volume_df["day"] = volume_df["timestamp"].dt.date
        counts = volume_df.groupby("day", as_index=False)["news_id"].count() if "news_id" in volume_df.columns else volume_df.groupby("day", as_index=False).size()
        value_cols = [column for column in counts.columns if column != "day"]
        st.plotly_chart(indicator_chart(counts, "day", value_cols, "News Volume"), use_container_width=True)

    st.dataframe(news_table(news_df), use_container_width=True)
