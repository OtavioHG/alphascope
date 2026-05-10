from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from alphascope.infrastructure.db.session import Base

class AssetModel(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    base_asset = Column(String, nullable=False)
    quote_asset = Column(String, nullable=False)
    exchange = Column(String, default="binance")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    candles = relationship("CandleModel", back_populates="asset")

class CandleModel(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Numeric(precision=18, scale=8), nullable=False)
    high_price = Column(Numeric(precision=18, scale=8), nullable=False)
    low_price = Column(Numeric(precision=18, scale=8), nullable=False)
    close_price = Column(Numeric(precision=18, scale=8), nullable=False)
    volume = Column(Numeric(precision=18, scale=8), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=False)
    quote_asset_volume = Column(Numeric(precision=18, scale=8), nullable=False)
    number_of_trades = Column(Integer, nullable=False)

    asset = relationship("AssetModel", back_populates="candles")

    __table_args__ = (
        Index('idx_asset_time', 'asset_id', 'open_time', unique=True),
    )

class NewsModel(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String)
    url = Column(String, unique=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String)
    sentiment_score = Column(Numeric(precision=5, scale=2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TechnicalFeatureModel(Base):
    __tablename__ = "technical_features"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    candle_id = Column(Integer, ForeignKey("candles.id"), nullable=False, unique=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    rsi = Column(Numeric(precision=18, scale=8))
    macd = Column(Numeric(precision=18, scale=8))
    macd_signal = Column(Numeric(precision=18, scale=8))
    bb_upper = Column(Numeric(precision=18, scale=8))
    bb_lower = Column(Numeric(precision=18, scale=8))
    ma_short = Column(Numeric(precision=18, scale=8))
    ma_long = Column(Numeric(precision=18, scale=8))
    pct_return = Column(Numeric(precision=18, scale=8))
    volatility = Column(Numeric(precision=18, scale=8))
    relative_volume = Column(Numeric(precision=18, scale=8))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NewsSentimentModel(Base):
    __tablename__ = "news_sentiment"

    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news.id"), nullable=False, unique=True)
    sentiment_label = Column(String, nullable=False)
    sentiment_score = Column(Numeric(precision=5, scale=2), nullable=False)
    topic = Column(String)
    asset_mentioned = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PredictionModel(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    signal = Column(String, nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Numeric(precision=5, scale=4))
    model_version = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
