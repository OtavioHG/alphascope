from __future__ import annotations

import pandas as pd


class CrossAssetAnalyzer:
    def analyze(self, dataset: pd.DataFrame) -> dict[str, pd.DataFrame]:
        if dataset.empty:
            return {"correlation": pd.DataFrame(), "leaders_followers": pd.DataFrame()}

        frame = dataset.sort_values(["timestamp", "symbol"]).copy()
        if "pct_return" not in frame.columns:
            frame["pct_return"] = frame.groupby("symbol")["close"].pct_change().fillna(0.0)
        pivot = frame.pivot_table(index="timestamp", columns="symbol", values="pct_return", aggfunc="mean").fillna(0.0)
        correlation = pivot.corr().reset_index()

        leader_rows: list[dict[str, object]] = []
        symbols = list(pivot.columns)
        for leader in symbols:
            for follower in symbols:
                if leader == follower:
                    continue
                lagged_corr = pivot[leader].shift(1).corr(pivot[follower])
                if pd.notna(lagged_corr):
                    leader_rows.append(
                        {
                            "leader": leader,
                            "follower": follower,
                            "lagged_correlation": float(lagged_corr),
                        }
                    )
        leaders_followers = (
            pd.DataFrame(leader_rows).sort_values("lagged_correlation", ascending=False).reset_index(drop=True)
            if leader_rows
            else pd.DataFrame()
        )
        return {"correlation": correlation, "leaders_followers": leaders_followers}
