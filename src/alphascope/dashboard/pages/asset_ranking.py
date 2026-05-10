from __future__ import annotations

from alphascope.dashboard._optional import st

from alphascope.dashboard.components.tables import ranking_table
from alphascope.dashboard.services.ranking_service import RankingService


def render() -> None:
    st.title("Asset Ranking")
    service = RankingService()

    interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)
    minimum_score = st.slider("Minimum Final Score", 0.0, 1.0, 0.0, 0.01)
    maximum_risk = st.slider("Maximum Risk Score", 0.0, 1.0, 1.0, 0.01)

    ranking = service.filter_ranking(minimum_score=minimum_score, maximum_risk=maximum_risk)
    if not ranking.empty and "interval" in ranking.columns:
        ranking = ranking.loc[ranking["interval"] == interval]

    st.dataframe(ranking_table(ranking), use_container_width=True)
