from datetime import datetime, timezone
from decimal import Decimal
from alphascope.domain.schemas import Asset, Candle

def test_asset_creation():
    asset = Asset(
        id=1,
        symbol="BTC/USDT",
        base_asset="BTC",
        quote_asset="USDT",
        exchange="binance",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    assert asset.symbol == "BTC/USDT"
    assert asset.base_asset == "BTC"
    assert asset.exchange == "binance"

def test_candle_creation():
    candle = Candle(
        id=1,
        asset_id=1,
        open_time=datetime.now(timezone.utc),
        open_price=Decimal("50000.00"),
        high_price=Decimal("51000.00"),
        low_price=Decimal("49000.00"),
        close_price=Decimal("50500.00"),
        volume=Decimal("10.5"),
        close_time=datetime.now(timezone.utc),
        quote_asset_volume=Decimal("525000.00"),
        number_of_trades=1000
    )
    assert candle.close_price == Decimal("50500.00")
    assert candle.volume > 0
