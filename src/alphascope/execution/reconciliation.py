from __future__ import annotations


class ReconciliationEngine:
    def compare_positions(self, internal_positions: list[dict], exchange_positions: list[dict]) -> dict[str, list[dict]]:
        internal_map = {item.get("symbol"): item for item in internal_positions}
        exchange_map = {item.get("symbol"): item for item in exchange_positions}

        matched = [internal_map[symbol] for symbol in internal_map.keys() & exchange_map.keys()]
        missing_on_exchange = [internal_map[symbol] for symbol in internal_map.keys() - exchange_map.keys()]
        missing_internal = [exchange_map[symbol] for symbol in exchange_map.keys() - internal_map.keys()]

        return {
            "matched": matched,
            "missing_on_exchange": missing_on_exchange,
            "missing_internal": missing_internal,
        }
