from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from alphascope.infrastructure.db.models import TechnicalFeatureModel
from typing import List, Dict
import pandas as pd

class TechnicalRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_features(self, df: pd.DataFrame, asset_id: int):
        """
        Saves calculated features from a DataFrame into the database.
        """
        for _, row in df.iterrows():
            # Use candle_id if available in df
            candle_id = row.get("candle_id")
            if not candle_id:
                continue
                
            # Check if exists
            existing = self.db.query(TechnicalFeatureModel).filter_by(candle_id=candle_id).first()
            if existing:
                continue
                
            feat = TechnicalFeatureModel(
                asset_id=asset_id,
                candle_id=candle_id,
                timestamp=row["timestamp"],
                rsi=row.get("rsi"),
                macd=row.get("macd"),
                macd_signal=row.get("macd_signal"),
                bb_upper=row.get("bb_upper"),
                bb_lower=row.get("bb_lower"),
                ma_short=row.get("ma_short"),
                ma_long=row.get("ma_long"),
                pct_return=row.get("pct_return"),
                volatility=row.get("volatility"),
                relative_volume=row.get("relative_volume")
            )
            self.db.add(feat)
        
        self.db.commit()

    def get_features_as_df(self, asset_id: int, limit: int = 1000) -> pd.DataFrame:
        query = self.db.query(TechnicalFeatureModel).filter_by(asset_id=asset_id).order_by(TechnicalFeatureModel.timestamp.asc()).limit(limit)
        df = pd.read_sql(query.statement, self.db.get_bind())
        return df
