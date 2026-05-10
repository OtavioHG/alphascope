from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Any


def _to_decimal(value: float | str | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _get_symbol_info(symbol: str, exchange_info: dict[str, Any]) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    for symbol_info in exchange_info.get("symbols", []):
        if str(symbol_info.get("symbol", "")).upper() == normalized_symbol:
            return symbol_info
    raise ValueError(f"Symbol {symbol} not found in exchange_info")


def _get_filter(symbol_info: dict[str, Any], filter_type: str) -> dict[str, Any] | None:
    for filter_info in symbol_info.get("filters", []):
        if filter_info.get("filterType") == filter_type:
            return filter_info
    return None


def normalize_quantity(symbol: str, quantity: float, exchange_info: dict[str, Any], *, side: str = "BUY") -> dict[str, Any]:
    symbol_info = _get_symbol_info(symbol, exchange_info)
    lot_filter = _get_filter(symbol_info, "LOT_SIZE")
    if lot_filter is None:
        raise ValueError(f"LOT_SIZE filter not found for {symbol}")

    min_notional_filter = _get_filter(symbol_info, "MIN_NOTIONAL") or _get_filter(symbol_info, "NOTIONAL")

    step_size = _to_decimal(lot_filter["stepSize"])
    min_qty = _to_decimal(lot_filter["minQty"])
    max_qty = _to_decimal(lot_filter["maxQty"])

    quantity_decimal = _to_decimal(quantity)
    rounding = ROUND_UP if side.upper() == "BUY" else ROUND_DOWN
    normalized_quantity = (quantity_decimal / step_size).to_integral_value(rounding=rounding) * step_size
    normalized_quantity = normalized_quantity.quantize(step_size, rounding=ROUND_DOWN)

    min_notional = Decimal("0")
    if min_notional_filter:
        min_notional = _to_decimal(min_notional_filter.get("minNotional", "0"))

    normalized_quantity_str = format(normalized_quantity, "f")
    return {
        "raw_quantity": float(quantity_decimal),
        "raw_quantity_decimal": quantity_decimal,
        "normalized_quantity": float(normalized_quantity),
        "normalized_quantity_decimal": normalized_quantity,
        "normalized_quantity_str": normalized_quantity_str,
        "step_size": str(step_size),
        "step_size_decimal": step_size,
        "min_qty": float(min_qty),
        "min_qty_decimal": min_qty,
        "max_qty": float(max_qty),
        "max_qty_decimal": max_qty,
        "min_notional": float(min_notional),
        "min_notional_decimal": min_notional,
    }


def validate_order_quantity(
    symbol: str,
    quantity: float,
    price: float,
    exchange_info: dict[str, Any],
    *,
    side: str = "BUY",
) -> tuple[bool, dict[str, Any]]:
    normalized = normalize_quantity(symbol, quantity, exchange_info, side=side)
    price_decimal = _to_decimal(price)
    normalized_quantity = normalized["normalized_quantity_decimal"]
    min_qty = normalized["min_qty_decimal"]
    max_qty = normalized["max_qty_decimal"]
    min_notional = normalized["min_notional_decimal"]
    notional_value = normalized_quantity * price_decimal

    reason = "approved"
    valid = True
    if normalized_quantity <= Decimal("0"):
        valid = False
        reason = "invalid_quantity"
    elif normalized_quantity < min_qty:
        valid = False
        reason = "min_qty_not_met"
    elif normalized_quantity > max_qty:
        valid = False
        reason = "max_qty_exceeded"
    elif min_notional > Decimal("0") and notional_value < min_notional:
        valid = False
        reason = "min_notional_not_met"

    details = {
        **normalized,
        "symbol": symbol.upper(),
        "price": float(price_decimal),
        "price_decimal": price_decimal,
        "notional_value": float(notional_value),
        "notional_value_decimal": notional_value,
        "reason": reason,
        "valid": valid,
        "filters_applied": {
            "step_size": normalized["step_size"],
            "min_qty": normalized["min_qty"],
            "max_qty": normalized["max_qty"],
            "min_notional": normalized["min_notional"],
        },
        "side": side.upper(),
    }
    return valid, details


def is_quantity_precision_error_message(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "parameter 'quantity' has too much precision",
            "precision is over the maximum defined for this asset",
            "filter failure: lot_size",
            "filter failure: min_notional",
        )
    )
