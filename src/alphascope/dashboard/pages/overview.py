from __future__ import annotations

import pandas as pd
from alphascope.dashboard._optional import st

from alphascope.dashboard.components.charts import equity_curve, indicator_chart
from alphascope.dashboard.components.metrics import metric_card
from alphascope.dashboard.services.data_service import DashboardDataService
from alphascope.dashboard.services.trading_service import TradingService
from alphascope.monitoring.system_status import SystemStatusService


def render() -> None:
    st.title("Overview")
    trading_service = TradingService()
    status_service = SystemStatusService()
    data_service = DashboardDataService()

    status = status_service.get_status()
    metrics = trading_service.calculate_metrics()
    portfolio = status.get("portfolio", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("Scheduler", status.get("scheduler", {}).get("status", "unknown"))
    with col2:
        metric_card("Last Cycle", status.get("pipeline", {}).get("last_run_at", "n/a"))
    with col3:
        metric_card("Capital", round(float(portfolio.get("cash_balance", 0.0)), 2))
    with col4:
        metric_card("Open Positions", metrics["open_positions"])
    with col5:
        metric_card("Accumulated PnL", round(metrics["realized_pnl"], 2))

    col6, col7, col8, col9 = st.columns(4)
    with col6:
        metric_card("Win Rate", round(float(metrics.get("win_rate_live", metrics.get("win_rate", 0.0))) * 100, 2))
    with col7:
        metric_card("Drawdown", round(float(metrics.get("drawdown", 0.0)) * 100, 2))
    with col8:
        metric_card("Profit Factor", round(float(metrics.get("profit_factor", 0.0)), 2))
    with col9:
        versions = trading_service.load_model_versions()
        best_model = "-" if versions.empty else f"{versions.iloc[0]['model_name']} {versions.iloc[0]['version']}"
        metric_card("Best Model", best_model)

    curve = trading_service.load_equity_curve()
    trades = trading_service.load_trades()
    dataset = data_service.load_dataset()

    left, right = st.columns(2)
    with left:
        st.subheader("Equity Curve")
        st.plotly_chart(equity_curve(curve), use_container_width=True)
    with right:
        st.subheader("Trade Distribution")
        distribution_df = trades.copy()
        if not distribution_df.empty:
            distribution_df["count"] = 1
            chart_df = distribution_df.groupby("status", as_index=False)["count"].sum()
            st.plotly_chart(indicator_chart(chart_df, "status", ["count"], "Trades by Status"), use_container_width=True)
        else:
            st.info("No trades available")

    st.subheader("Signals per Day")
    if not dataset.empty and "timestamp" in dataset.columns:
        signals_df = dataset.copy()
        signals_df["signal_day"] = pd.to_datetime(signals_df["timestamp"], utc=True, errors="coerce").dt.date
        if "sentiment_score" not in signals_df.columns:
            signals_df["sentiment_score"] = 0.0
        counts = signals_df.groupby("signal_day", as_index=False)["symbol"].count().rename(columns={"symbol": "signals"})
        st.plotly_chart(indicator_chart(counts, "signal_day", ["signals"], "Signals per Day"), use_container_width=True)
    else:
        st.info("No signal history available")

    retraining_runs = trading_service.load_retraining_runs()
    if not retraining_runs.empty:
        st.subheader("Retraining History")
        st.dataframe(
            retraining_runs.loc[:, [column for column in ["started_at", "trigger_reason", "selected_model_name", "selected_model_version", "promoted", "rollback_triggered"] if column in retraining_runs.columns]],
            use_container_width=True,
        )
