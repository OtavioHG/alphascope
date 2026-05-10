from __future__ import annotations

import pandas as pd

from alphascope.domain.model_schemas import TargetConfig


def build_binary_target(
    df: pd.DataFrame,
    config: TargetConfig | None = None,
    drop_incomplete: bool = True,
) -> pd.DataFrame:
    target_config = config or TargetConfig()
    if df.empty:
        return df.copy()

    dataset = df.sort_values([target_config.group_column, "timestamp"]).copy()
    grouped = dataset.groupby(target_config.group_column, group_keys=False)
    dataset["future_close"] = grouped[target_config.price_column].shift(-target_config.future_horizon)
    dataset["future_timestamp"] = grouped["timestamp"].shift(-target_config.future_horizon)
    dataset["future_return"] = dataset["future_close"] / dataset[target_config.price_column] - 1.0
    dataset[target_config.target_column] = (
        dataset["future_return"] > target_config.return_threshold
    ).astype("Int64")

    if drop_incomplete:
        dataset = dataset.dropna(subset=["future_close", "future_return"]).reset_index(drop=True)

    return dataset
