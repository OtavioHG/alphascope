"""Filtering helpers for automatic Binance universe selection."""

from __future__ import annotations


STABLECOIN_ASSETS = {
    "USDT",
    "USDC",
    "BUSD",
    "FDUSD",
    "DAI",
    "TUSD",
    "USDP",
    "USDS",
    "EUR",
    "FDEUR",
    "USD1",
}

LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
LEVERAGED_PREFIXES = ("LD",)


def is_trading_symbol(status: str | None) -> bool:
    """Return whether the exchange symbol is currently tradable."""
    return str(status or "").upper() == "TRADING"


def is_quote_asset_allowed(quote_asset: str | None, target_quote_asset: str) -> bool:
    """Return whether the symbol uses the desired quote asset."""
    return str(quote_asset or "").upper() == target_quote_asset.upper()


def is_stablecoin(base_asset: str | None) -> bool:
    """Return whether the asset is a known stablecoin or fiat-like asset."""
    return str(base_asset or "").upper() in STABLECOIN_ASSETS


def is_leveraged_token(base_asset: str | None) -> bool:
    """Return whether the asset looks like a Binance leveraged token."""
    normalized = str(base_asset or "").upper()
    return normalized.startswith(LEVERAGED_PREFIXES) or normalized.endswith(LEVERAGED_SUFFIXES)


def is_desired_spot_symbol(base_asset: str | None, quote_asset: str | None) -> bool:
    """Return whether the pair should be part of the automatic spot universe."""
    base = str(base_asset or "").upper()
    quote = str(quote_asset or "").upper()
    if not base or not quote:
        return False
    if is_stablecoin(base) and is_stablecoin(quote):
        return False
    if is_leveraged_token(base):
        return False
    return True
