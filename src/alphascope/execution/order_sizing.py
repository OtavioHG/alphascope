from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alphascope.config.settings import settings


def _extract_exchange_min_notional(symbol: str | None, exchange_info: dict[str, Any] | None) -> float:
    if not symbol or not exchange_info:
        return 0.0
    normalized_symbol = symbol.upper()
    for symbol_info in exchange_info.get("symbols", []):
        if str(symbol_info.get("symbol", "")).upper() != normalized_symbol:
            continue
        for filter_info in symbol_info.get("filters", []):
            if filter_info.get("filterType") in {"MIN_NOTIONAL", "NOTIONAL"}:
                return float(filter_info.get("minNotional") or 0.0)
    return 0.0


@dataclass(frozen=True, slots=True)
class OrderSizing:
    order_value_usd: float
    calculated_quantity: float
    final_quantity: float
    min_notional_required: float
    final_notional: float
    blocked_reason: str | None = None


def calculate_order_sizing(
    current_price: float,
    *,
    available_balance: float | None = None,
    symbol: str | None = None,
    exchange_info: dict[str, Any] | None = None,
) -> OrderSizing:
    if current_price <= 0:
        raise ValueError("current_price must be greater than zero")

    min_notional_required = max(
        settings.min_notional_usdt,
        _extract_exchange_min_notional(symbol, exchange_info),
    )
    order_value_usd = max(settings.default_order_usd, settings.order_size_usdt, settings.min_position_usd, settings.min_trade_value)
    order_value_usd = max(order_value_usd, min_notional_required)

    blocked_reason: str | None = None
    if order_value_usd > settings.max_position_usd:
        blocked_reason = "min_notional_not_met"
        order_value_usd = settings.max_position_usd
    elif available_balance is not None and available_balance < order_value_usd:
        blocked_reason = "insufficient_balance"

    quantity = order_value_usd / current_price
    if quantity * current_price < min_notional_required:
        quantity = min_notional_required / current_price

    final_notional = quantity * current_price
    return OrderSizing(
        order_value_usd=order_value_usd,
        calculated_quantity=order_value_usd / current_price,
        final_quantity=quantity,
        min_notional_required=min_notional_required,
        final_notional=final_notional,
        blocked_reason=blocked_reason,
    )


def calculate_order_quantity(current_price: float) -> float:
    return calculate_order_sizing(current_price).final_quantity
