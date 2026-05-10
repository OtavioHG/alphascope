from __future__ import annotations

import pandas as pd

from alphascope.datasets.validators import validate_market_dataframe, validate_news_dataframe


def test_validate_market_dataframe_detects_required_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "symbol": "BTCUSDT",
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 10.0,
            }
        ]
    )

    result = validate_market_dataframe(frame)

    assert result.valid is True
    assert result.row_count == 1


def test_validate_news_dataframe_detects_missing_text() -> None:
    frame = pd.DataFrame(
        [
            {
                "title": "Bitcoin update",
                "timestamp": "2025-01-01T00:00:00Z",
                "source": "example.com",
            }
        ]
    )

    result = validate_news_dataframe(frame)

    assert result.valid is False
    assert result.missing_required["text_or_description"] == 1
