from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from alphascope.platform.config_models import PlatformConfig
from alphascope.platform.quant_models import ExchangeFilters, OrderIntent, OrderValidation


class ExecutionSafetyGuard:
    def __init__(self, config: PlatformConfig) -> None:
        self.config = config

    def validate(self, intent: OrderIntent, filters: ExchangeFilters) -> OrderValidation:
        normalized_qty = self._round_down(intent.quantity, filters.step_size)
        normalized_price = self._round_down(intent.price, filters.tick_size)
        notional = normalized_qty * normalized_price

        if intent.duplicate_order_open:
            return OrderValidation(False, "duplicate_order_detected", normalized_price, normalized_qty)
        if intent.side.upper() == "BUY" and intent.existing_position:
            return OrderValidation(False, "repeated_buy_blocked", normalized_price, normalized_qty)
        if intent.last_trade_minutes_ago is not None and intent.last_trade_minutes_ago < self.config.risk.same_symbol_cooldown_minutes:
            return OrderValidation(False, "symbol_cooldown_active", normalized_price, normalized_qty)
        if normalized_qty < filters.min_qty:
            return OrderValidation(False, "below_min_quantity", normalized_price, normalized_qty)
        if notional < filters.min_notional:
            return OrderValidation(False, "below_min_notional", normalized_price, normalized_qty)
        return OrderValidation(True, "accepted", normalized_price, normalized_qty)

    @staticmethod
    def _round_down(value: float, step: float) -> float:
        if step <= 0:
            return float(value)
        decimal_value = Decimal(str(value))
        decimal_step = Decimal(str(step))
        rounded = (decimal_value / decimal_step).to_integral_value(rounding=ROUND_DOWN) * decimal_step
        return float(rounded)
