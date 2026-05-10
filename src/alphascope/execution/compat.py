from __future__ import annotations

import logging
import time
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Any, Callable


try:
    from binance.client import Client as BinanceClient
    from binance.exceptions import BinanceAPIException, BinanceOrderException
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in local fallback environments
    class BinanceAPIException(Exception):
        def __init__(self, message: str = "", code: int | None = None) -> None:
            super().__init__(message)
            self.code = code

    class BinanceOrderException(Exception):
        pass

    class BinanceClient:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.API_URL = ""

        def __getattr__(self, name: str) -> Any:
            raise ModuleNotFoundError("python-binance is required for real Binance connectivity")


try:
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
except ModuleNotFoundError:  # pragma: no cover
    def retry(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func
        return decorator

    def retry_if_exception_type(*args: Any, **kwargs: Any) -> None:
        return None

    def stop_after_attempt(*args: Any, **kwargs: Any) -> None:
        return None

    def wait_exponential(*args: Any, **kwargs: Any) -> None:
        return None


try:
    from loguru import logger as loguru_logger
except ModuleNotFoundError:  # pragma: no cover
    class _LoguruShim:
        def __init__(self) -> None:
            logging.basicConfig(level=logging.INFO)
            self._logger = logging.getLogger("alphascope.loguru_shim")

        def bind(self, **kwargs: Any) -> "_LoguruShim":
            return self

        def add(self, *args: Any, **kwargs: Any) -> int:
            return 0

        def info(self, message: str, *args: Any) -> None:
            self._logger.info(message.format(*args))

        def warning(self, message: str, *args: Any) -> None:
            self._logger.warning(message.format(*args))

        def error(self, message: str, *args: Any) -> None:
            self._logger.error(message.format(*args))

    loguru_logger = _LoguruShim()


def _log_if_available(logger: Any | None, level: str, message: str, *args: Any) -> None:
    if logger is None:
        return
    log_method = getattr(logger, level, None)
    if callable(log_method):
        rendered = message.format(*args) if args else message
        log_method(rendered)


def is_binance_timestamp_error(exc: Exception) -> bool:
    return getattr(exc, "code", None) == -1021 or "Timestamp for this request" in str(exc)


def sync_binance_time(client: Any, logger: Any | None = None) -> int:
    server_time = client.get_server_time()
    system_time = int(time.time() * 1000)
    offset = int(server_time["serverTime"]) - system_time
    client.timestamp_offset = offset
    _log_if_available(
        logger,
        "info",
        "Binance timestamp synchronized | server_time={} | system_time={} | offset={}ms",
        server_time["serverTime"],
        system_time,
        offset,
    )
    return offset


def sync_binance_time_or_raise(
    client: Any,
    logger: Any | None = None,
    *,
    max_allowed_drift_ms: int | None = None,
) -> int:
    offset = sync_binance_time(client, logger=logger)
    if max_allowed_drift_ms is not None and abs(offset) > max_allowed_drift_ms:
        raise RuntimeError(f"Clock difference too large: {offset}ms")
    return offset


def call_authenticated_binance(
    client: Any,
    operation: Callable[..., Any],
    *args: Any,
    logger: Any | None = None,
    sync_before: bool = False,
    max_allowed_drift_ms: int | None = None,
    **kwargs: Any,
) -> Any:
    if sync_before:
        sync_binance_time_or_raise(
            client,
            logger=logger,
            max_allowed_drift_ms=max_allowed_drift_ms,
        )
    try:
        return operation(*args, **kwargs)
    except BinanceAPIException as exc:
        if not is_binance_timestamp_error(exc):
            raise
        _log_if_available(logger, "warning", "Timestamp error detected. Resyncing Binance clock...")
        sync_binance_time_or_raise(
            client,
            logger=logger,
            max_allowed_drift_ms=max_allowed_drift_ms,
        )
        return operation(*args, **kwargs)


EXECUTION_STATUS_OPEN = "OPEN"
EXECUTION_STATUS_CLOSED = "CLOSED"
EXECUTION_STATUS_CLOSED_ORPHAN = "CLOSED_ORPHAN"
EXECUTION_STATUS_DUST_POSITION = "DUST_POSITION"
EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL = "BLOCKED_MIN_NOTIONAL"
EXECUTION_STATUS_BLOCKED_INSUFFICIENT_BALANCE = "BLOCKED_INSUFFICIENT_BALANCE"
EXECUTION_STATUS_BLOCKED_INVALID_STEP_SIZE = "BLOCKED_INVALID_STEP_SIZE"
EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY = "BLOCKED_INVALID_QUANTITY"

SAFE_SELL_FEE_BUFFER = 0.995
SAFE_BUY_BALANCE_BUFFER = 0.995
SUPPORTED_QUOTE_ASSETS = ("USDT", "FDUSD", "USDC", "BUSD", "BRL", "BTC", "ETH")


def _to_decimal(value: object, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def infer_base_asset(symbol: str) -> str:
    normalized = str(symbol).upper()
    for quote_asset in SUPPORTED_QUOTE_ASSETS:
        if normalized.endswith(quote_asset) and len(normalized) > len(quote_asset):
            return normalized[: -len(quote_asset)]
    return normalized


def floor_to_step(quantity: float | Decimal, step_size: float | Decimal) -> Decimal:
    quantity_decimal = _to_decimal(quantity)
    step_decimal = _to_decimal(step_size)
    if step_decimal <= 0:
        raise ValueError("step_size must be greater than zero")
    floored = (quantity_decimal / step_decimal).to_integral_value(rounding=ROUND_DOWN) * step_decimal
    return floored.quantize(step_decimal, rounding=ROUND_DOWN)


def get_symbol_filters(symbol: str, exchange_info: dict[str, Any]) -> dict[str, Any]:
    normalized_symbol = str(symbol).upper()
    for symbol_info in exchange_info.get("symbols", []):
        if str(symbol_info.get("symbol", "")).upper() != normalized_symbol:
            continue
        filters = {str(item.get("filterType")): item for item in symbol_info.get("filters", [])}
        lot_filter = filters.get("LOT_SIZE")
        notional_filter = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
        if not lot_filter:
            raise ValueError(f"LOT_SIZE filter not found for {normalized_symbol}")
        step_size = _to_decimal(lot_filter.get("stepSize"))
        min_qty = _to_decimal(lot_filter.get("minQty"))
        max_qty = _to_decimal(lot_filter.get("maxQty"))
        min_notional = _to_decimal((notional_filter or {}).get("minNotional", "0"))
        precision = int(symbol_info.get("baseAssetPrecision", max(0, -step_size.normalize().as_tuple().exponent)))
        return {
            "symbol": normalized_symbol,
            "symbol_info": symbol_info,
            "step_size": step_size,
            "min_qty": min_qty,
            "max_qty": max_qty,
            "min_notional": min_notional,
            "precision": precision,
        }
    raise ValueError(f"Symbol {normalized_symbol} not found in exchange_info")


def get_asset_balance_from_account(account_info: dict[str, Any], asset: str) -> dict[str, float]:
    for balance in account_info.get("balances", []):
        if str(balance.get("asset", "")).upper() == str(asset).upper():
            free_balance = float(balance.get("free", 0.0) or 0.0)
            locked_balance = float(balance.get("locked", 0.0) or 0.0)
            return {
                "free": free_balance,
                "locked": locked_balance,
                "total": free_balance + locked_balance,
            }
    return {"free": 0.0, "locked": 0.0, "total": 0.0}


def get_safe_sell_quantity(
    client: Any,
    symbol: str,
    requested_quantity: float | None = None,
    *,
    exchange_info: dict[str, Any] | None = None,
    price: float | None = None,
    account_info: dict[str, Any] | None = None,
    fee_buffer: float = SAFE_SELL_FEE_BUFFER,
) -> dict[str, Any]:
    return get_safe_quantity(
        client,
        symbol,
        requested_quantity,
        side="SELL",
        exchange_info=exchange_info,
        price=price,
        account_info=account_info,
        balance_buffer=fee_buffer,
    )


def get_safe_quantity(
    client: Any,
    symbol: str,
    requested_quantity: float | None = None,
    *,
    side: str,
    exchange_info: dict[str, Any] | None = None,
    price: float | None = None,
    account_info: dict[str, Any] | None = None,
    balance_buffer: float = SAFE_SELL_FEE_BUFFER,
) -> dict[str, Any]:
    normalized_symbol = str(symbol).upper()
    normalized_side = str(side).upper()
    resolved_exchange_info = exchange_info or dict(client.get_exchange_info())
    account_payload = account_info or dict(client.get_account())
    filters = get_symbol_filters(normalized_symbol, resolved_exchange_info)
    base_asset = infer_base_asset(normalized_symbol)
    resolved_price = float(price or 0.0)
    if resolved_price <= 0:
        ticker = client.get_symbol_ticker(symbol=normalized_symbol)
        resolved_price = float(ticker["price"])
    requested = 0.0 if requested_quantity is None else max(float(requested_quantity), 0.0)
    if normalized_side == "BUY":
        quote_asset = next(
            (
                str(filters["symbol_info"].get("quoteAsset", quote_asset)).upper()
                for quote_asset in SUPPORTED_QUOTE_ASSETS
                if normalized_symbol.endswith(quote_asset)
            ),
            "USDT",
        )
        asset_balance = get_asset_balance_from_account(account_payload, quote_asset)
        real_balance = float(asset_balance["free"])
        safe_quote_balance = real_balance * float(balance_buffer)
        max_requested = safe_quote_balance / resolved_price if resolved_price > 0 else 0.0
        capped_requested = min(requested, max_requested)
        safe_quantity = capped_requested
    else:
        asset_balance = get_asset_balance_from_account(account_payload, base_asset)
        real_balance = float(asset_balance["free"])
        requested = real_balance if requested_quantity is None else requested
        capped_requested = min(requested, real_balance)
        safe_quantity = capped_requested * float(balance_buffer)
    step_size = filters["step_size"]

    validation_status = "APPROVED"
    validation_reason = "approved"
    normalized_quantity_decimal = Decimal("0")
    try:
        if normalized_side == "BUY":
            normalized_quantity_decimal = (_to_decimal(safe_quantity) / step_size).to_integral_value(rounding=ROUND_UP) * step_size
            normalized_quantity_decimal = normalized_quantity_decimal.quantize(step_size, rounding=ROUND_DOWN)
            safe_quote_limit = _to_decimal(real_balance * float(balance_buffer))
            if normalized_quantity_decimal * _to_decimal(resolved_price) > safe_quote_limit:
                normalized_quantity_decimal = floor_to_step(safe_quantity, step_size)
        else:
            normalized_quantity_decimal = floor_to_step(safe_quantity, step_size)
    except ValueError:
        validation_status = EXECUTION_STATUS_BLOCKED_INVALID_STEP_SIZE
        validation_reason = "invalid_step_size"

    min_qty = filters["min_qty"]
    max_qty = filters["max_qty"]
    min_notional = filters["min_notional"]
    notional_decimal = normalized_quantity_decimal * _to_decimal(resolved_price)

    if validation_status == "APPROVED":
        if real_balance <= 0:
            validation_status = EXECUTION_STATUS_BLOCKED_INSUFFICIENT_BALANCE
            validation_reason = "real_balance_zero"
        elif requested_quantity is not None and requested <= 0:
            validation_status = EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY
            validation_reason = "requested_quantity_zero"
        elif normalized_quantity_decimal <= 0:
            validation_status = EXECUTION_STATUS_DUST_POSITION
            validation_reason = "normalized_quantity_zero"
        elif normalized_quantity_decimal < min_qty:
            validation_status = EXECUTION_STATUS_DUST_POSITION
            validation_reason = "below_min_qty"
        elif max_qty > 0 and normalized_quantity_decimal > max_qty:
            validation_status = EXECUTION_STATUS_BLOCKED_INVALID_QUANTITY
            validation_reason = "above_max_qty"
        elif min_notional > 0 and notional_decimal < min_notional:
            validation_status = EXECUTION_STATUS_BLOCKED_MIN_NOTIONAL
            validation_reason = "min_notional_not_met"

    return {
        "symbol": normalized_symbol,
        "side": normalized_side,
        "base_asset": base_asset,
        "real_balance": real_balance,
        "requested_quantity": None if requested_quantity is None else float(requested_quantity),
        "effective_requested_quantity": capped_requested,
        "safe_quantity": safe_quantity,
        "normalized_quantity": float(normalized_quantity_decimal),
        "normalized_quantity_str": format(normalized_quantity_decimal, "f"),
        "step_size": float(step_size),
        "min_qty": float(min_qty),
        "max_qty": float(max_qty),
        "min_notional": float(min_notional),
        "precision": int(filters["precision"]),
        "price": resolved_price,
        "notional": float(notional_decimal),
        "validation_status": validation_status,
        "validation_reason": validation_reason,
        "valid": validation_status == "APPROVED",
    }
