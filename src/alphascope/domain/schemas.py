from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class AssetBase(BaseModel):
    symbol: str = Field(..., description="The trading symbol, e.g., BTCUSDT")
    base_asset: str = Field(..., description="The base asset, e.g., BTC")
    quote_asset: str = Field(..., description="The quote asset, e.g., USDT")
    exchange: str = Field(default="binance")

class AssetCreate(AssetBase):
    pass

class Asset(AssetBase):
    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CandleBase(BaseModel):
    asset_id: int
    open_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: datetime
    quote_asset_volume: Decimal
    number_of_trades: int

class CandleCreate(CandleBase):
    pass

class Candle(CandleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class TechnicalFeatureBase(BaseModel):
    asset_id: int
    candle_id: int
    timestamp: datetime
    rsi: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    bb_upper: Optional[Decimal] = None
    bb_lower: Optional[Decimal] = None
    ma_short: Optional[Decimal] = None
    ma_long: Optional[Decimal] = None
    pct_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    relative_volume: Optional[Decimal] = None

class TechnicalFeature(TechnicalFeatureBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class NewsSentimentBase(BaseModel):
    news_id: int
    sentiment_label: str  # positive, neutral, negative
    sentiment_score: float
    topic: Optional[str] = None
    asset_mentioned: Optional[str] = None

class NewsSentiment(NewsSentimentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NormalizedDatasetRow(BaseModel):
    timestamp: datetime
    symbol: str
    # Market Data
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    # Technical Features
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    ma_short: Optional[float] = None
    ma_long: Optional[float] = None
    pct_return: Optional[float] = None
    volatility: Optional[float] = None
    relative_volume: Optional[float] = None
    # NLP Data
    sentiment_avg: Optional[float] = None
    sentiment_count: int = 0
    top_topic: Optional[str] = None
