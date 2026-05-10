"""Custom exceptions for AlphaScope V1."""

from __future__ import annotations


class AlphaScopeError(Exception):
    """Base project exception."""


class IngestionError(AlphaScopeError):
    """Raised when market ingestion fails."""


class StorageError(AlphaScopeError):
    """Raised when persistence operations fail."""


class FeatureError(AlphaScopeError):
    """Raised when feature generation fails."""


class RankingError(AlphaScopeError):
    """Raised when ranking generation fails."""


class BacktestError(AlphaScopeError):
    """Raised when backtesting fails."""


class ExecutionError(AlphaScopeError):
    """Raised when paper trading execution fails."""
