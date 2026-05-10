"""Normalization helpers for external crypto data providers."""

from __future__ import annotations

from typing import Any


STABLE_QUOTES = (
    "USDT",
    "USDC",
    "BUSD",
    "FDUSD",
    "DAI",
    "TUSD",
    "USD",
    "BTC",
    "ETH",
)

CANONICAL_SYMBOL_ALIASES = {
    "BITCOIN": "BTC",
    "BTC": "BTC",
    "ETHEREUM": "ETH",
    "ETHER": "ETH",
    "ETH": "ETH",
    "BINANCECOIN": "BNB",
    "BNB": "BNB",
    "RIPPLE": "XRP",
    "XRP": "XRP",
    "DOGECOIN": "DOGE",
    "DOGE": "DOGE",
    "SOLANA": "SOL",
    "SOL": "SOL",
    "CARDANO": "ADA",
    "ADA": "ADA",
    "TRON": "TRX",
    "TRX": "TRX",
    "CHAINLINK": "LINK",
    "LINK": "LINK",
    "POLYGON": "MATIC",
    "MATIC": "MATIC",
    "SHIBA INU": "SHIB",
    "SHIB": "SHIB",
    "LITECOIN": "LTC",
    "LTC": "LTC",
}


def normalize_symbol_token(value: str | None) -> str:
    """Normalize a symbol-like token into a canonical uppercase value."""
    if value is None:
        return ""
    cleaned = "".join(character for character in value.upper().strip() if character.isalnum() or character in {" ", "_", "-"})
    return cleaned.replace("-", " ").replace("_", " ").strip()


def canonicalize_asset_symbol(symbol: str | None, name: str | None = None) -> str:
    """Map different symbol/name variants to a canonical symbol."""
    candidates = [normalize_symbol_token(symbol), normalize_symbol_token(name)]
    for candidate in candidates:
        if candidate in CANONICAL_SYMBOL_ALIASES:
            return CANONICAL_SYMBOL_ALIASES[candidate]
    for candidate in candidates:
        if candidate:
            compact = candidate.replace(" ", "")
            return compact[:15]
    return "UNKNOWN"


def split_binance_symbol(raw_symbol: str) -> tuple[str, str]:
    """Split a Binance raw symbol into base and quote assets."""
    normalized = normalize_symbol_token(raw_symbol).replace(" ", "")
    for quote in sorted(STABLE_QUOTES, key=len, reverse=True):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)], quote
    return normalized, "UNKNOWN"


def safe_float(value: Any) -> float | None:
    """Convert a raw value to float, returning None when unavailable."""
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    """Convert a raw value to int, returning None when unavailable."""
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
