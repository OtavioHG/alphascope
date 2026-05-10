from __future__ import annotations

import pandas as pd


class StrategyGenerator:
    def generate(
        self,
        mined_signals: pd.DataFrame,
        regimes: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        if mined_signals.empty:
            return pd.DataFrame()

        dominant_regime = "any"
        if regimes is not None and not regimes.empty:
            dominant_regime = str(regimes["regime_label"].mode().iloc[0])

        strategies: list[dict[str, object]] = []
        for index, row in mined_signals.iterrows():
            promotion_status = "candidate" if float(row["stability_score"]) >= 0.02 else "research_only"
            strategies.append(
                {
                    "strategy_id": f"strategy_{index + 1:03d}",
                    "signal_definition": row["signal_definition"],
                    "entry_rules": [f"trigger:{row['signal_definition']}", f"regime:{dominant_regime}"],
                    "exit_rules": ["take_profit:0.03", "stop_loss:0.015", "time_exit:4_candles"],
                    "filters": ["max_volatility:0.05", "min_relative_volume:1.0"],
                    "target_definition": {"future_horizon": 4, "return_threshold": 0.015},
                    "evaluation_metrics": {
                        "win_rate": float(row["win_rate"]),
                        "avg_return": float(row["avg_return"]),
                        "sharpe": float(row["sharpe"]),
                        "max_drawdown": float(row["max_drawdown"]),
                        "stability_score": float(row["stability_score"]),
                        "sample_count": int(row["sample_count"]),
                    },
                    "promotion_status": promotion_status,
                }
            )
        return pd.DataFrame(strategies)
