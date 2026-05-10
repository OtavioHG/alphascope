from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def equal_weight_allocation(symbols: list[str], total_capital: float) -> dict[str, float]:
    if not symbols or total_capital <= 0:
        return {}
    weight = total_capital / len(symbols)
    return {symbol: weight for symbol in symbols}


def risk_parity_allocation(volatility_map: dict[str, float], total_capital: float) -> dict[str, float]:
    if not volatility_map or total_capital <= 0:
        return {}
    inverse_vol = {
        symbol: (1.0 / volatility) if volatility and volatility > 0 else 0.0
        for symbol, volatility in volatility_map.items()
    }
    total_inverse = sum(inverse_vol.values())
    if total_inverse <= 0:
        return equal_weight_allocation(list(volatility_map.keys()), total_capital)
    return {
        symbol: total_capital * (value / total_inverse)
        for symbol, value in inverse_vol.items()
    }


def kelly_fraction_allocation(
    probability_map: dict[str, float],
    payoff_map: dict[str, float],
    total_capital: float,
    max_fraction: float = 0.25,
) -> dict[str, float]:
    allocations: dict[str, float] = {}
    for symbol, probability in probability_map.items():
        payoff = payoff_map.get(symbol, 1.0)
        if payoff <= 0:
            allocations[symbol] = 0.0
            continue
        fraction = probability - ((1.0 - probability) / payoff)
        fraction = float(np.clip(fraction, 0.0, max_fraction))
        allocations[symbol] = total_capital * fraction
    return allocations


@dataclass(slots=True)
class AllocationEngine:
    method: str = "equal_weight"

    def allocate(self, candidates_df: pd.DataFrame, total_capital: float) -> dict[str, float]:
        if candidates_df.empty or total_capital <= 0:
            return {}
        symbols = candidates_df["symbol"].astype(str).tolist()
        if self.method == "equal_weight":
            return equal_weight_allocation(symbols, total_capital)
        if self.method == "risk_parity":
            vol_map = dict(zip(symbols, candidates_df.get("volatility", pd.Series([1.0] * len(symbols)))))
            return risk_parity_allocation(vol_map, total_capital)
        if self.method == "kelly_fraction":
            prob_map = dict(zip(symbols, candidates_df.get("predicted_probability", pd.Series([0.5] * len(symbols)))))
            payoff_map = dict(zip(symbols, candidates_df.get("expected_payoff", pd.Series([1.5] * len(symbols)))))
            return kelly_fraction_allocation(prob_map, payoff_map, total_capital)
        raise ValueError(f"Unknown allocation method: {self.method}")
