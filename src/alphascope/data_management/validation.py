from __future__ import annotations

import pandas as pd


class DataValidator:
    def validate(self, dataset: pd.DataFrame, expected_schema: dict[str, str] | None = None) -> dict[str, object]:
        if dataset.empty:
            return {
                "rows": 0,
                "missing_data": {},
                "outliers": {},
                "schema_changes": [],
                "data_drift": {},
            }
        missing = dataset.isna().sum().to_dict()
        numeric = dataset.select_dtypes(include=["number"])
        outliers: dict[str, int] = {}
        for column in numeric.columns:
            series = numeric[column].dropna()
            if series.empty:
                outliers[column] = 0
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                outliers[column] = 0
            else:
                mask = (series < (q1 - 1.5 * iqr)) | (series > (q3 + 1.5 * iqr))
                outliers[column] = int(mask.sum())
        schema_changes: list[str] = []
        if expected_schema:
            current_schema = {column: str(dtype) for column, dtype in dataset.dtypes.items()}
            for column, expected_dtype in expected_schema.items():
                if column not in current_schema:
                    schema_changes.append(f"missing_column:{column}")
                elif current_schema[column] != expected_dtype:
                    schema_changes.append(f"type_changed:{column}:{current_schema[column]}")
        data_drift = {
            column: float(dataset[column].astype(float).mean())
            for column in numeric.columns[: min(10, len(numeric.columns))]
        }
        return {
            "rows": int(len(dataset)),
            "missing_data": missing,
            "outliers": outliers,
            "schema_changes": schema_changes,
            "data_drift": data_drift,
        }
