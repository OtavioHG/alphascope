from sqlalchemy.orm import Session
from alphascope.infrastructure.db.models import CandleModel, AssetModel
from typing import List, Optional
import pandas as pd

class MarketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_candles(self, asset_id: int, limit: int = 1000) -> List[CandleModel]:
        return self.db.query(CandleModel).filter(
            CandleModel.asset_id == asset_id
        ).order_by(CandleModel.open_time.asc()).limit(limit).all()

    def get_candles_as_df(self, asset_id: int, limit: int = 1000) -> pd.DataFrame:
        candles = self.get_candles(asset_id, limit)
        if not candles:
            return pd.DataFrame()
            
        data = []
        for c in candles:
            data.append({
                "candle_id": c.id,
                "asset_id": c.asset_id,
                "timestamp": c.open_time,
                "open": float(c.open_price),
                "high": float(c.high_price),
                "low": float(c.low_price),
                "close": float(c.close_price),
                "volume": float(c.volume)
            })
        
        return pd.DataFrame(data)

    def get_assets(self) -> List[AssetModel]:
        return self.db.query(AssetModel).filter(AssetModel.is_active == True).all()
