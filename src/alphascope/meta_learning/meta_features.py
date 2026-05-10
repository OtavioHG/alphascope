from __future__ import annotations

import pandas as pd


class MetaFeatureBuilder:
    def build(
        self,
        dataset: pd.DataFrame,
        regimes: pd.DataFrame | None = None,
        anomalies: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        if dataset.empty:
            return pd.DataFrame()
        frame = dataset.copy()
        if regimes is not None and not regimes.empty:
            frame = frame.merge(
                regimes[["timestamp", "symbol", "regime_label", "regime_confidence"]],
                on=["timestamp", "symbol"],
                how="left",
            )
        if anomalies is not None and not anomalies.empty:
            anomaly_counts = anomalies.groupby("symbol").size().rename("anomaly_count").reset_index()
            frame = frame.merge(anomaly_counts, on="symbol", how="left")
        frame["anomaly_count"] = frame.get("anomaly_count", 0).fillna(0)
        frame["regime_code"] = (
            frame.get("regime_label", pd.Series("unknown", index=frame.index))
            .fillna("unknown")
            .astype("category")
            .cat.codes
        )
        return frame
