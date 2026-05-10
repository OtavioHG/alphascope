from __future__ import annotations

from alphascope.dashboard._optional import st

from alphascope.dashboard.components.charts import equity_curve, indicator_chart
from alphascope.dashboard.components.tables import trade_table
from alphascope.dashboard.services.trading_service import TradingService


def render() -> None:
    st.title("Trading Monitor")
    service = TradingService()
    trades = service.load_trades()
    positions = service.load_open_positions()
    curve = service.load_equity_curve()

    left, right = st.columns(2)
    with left:
        st.subheader("Equity Curve")
        st.plotly_chart(equity_curve(curve), use_container_width=True)
    with right:
        st.subheader("Profit per Trade")
        pnl_df = trades.loc[trades["status"] != "OPEN"].copy() if not trades.empty and "status" in trades.columns else trades.copy()
        if not pnl_df.empty:
            pnl_df["trade_label"] = pnl_df["trade_id"].astype(str)
            st.plotly_chart(indicator_chart(pnl_df, "trade_label", ["pnl"], "PnL by Trade"), use_container_width=True)
        else:
            st.info("No closed trades available")

    st.subheader("Trade History")
    st.dataframe(trade_table(trades), use_container_width=True)

    st.subheader("Open Positions")
    if positions.empty:
        st.info("No open positions")
    else:
        st.dataframe(positions, use_container_width=True)
