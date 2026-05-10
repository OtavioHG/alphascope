from sqlalchemy.orm import Session
from alphascope.infrastructure.db.models import NewsSentimentModel, NewsModel
from typing import List, Dict, Optional
import pandas as pd

class SentimentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_unprocessed_news(self, limit: int = 100) -> List[NewsModel]:
        """
        Returns news that don't have an entry in news_sentiment yet.
        """
        # Optimized: left join where sentiment is null
        query = self.db.query(NewsModel).outerjoin(NewsSentimentModel).filter(
            NewsSentimentModel.id == None
        ).limit(limit)
        return query.all()

    def save_sentiment(self, news_id: int, sentiment: Dict[str, any], topic: str, asset: Optional[str]):
        """
        Saves individual news sentiment result.
        """
        # Ensure it doesn't already exist
        exists = self.db.query(NewsSentimentModel).filter_by(news_id=news_id).first()
        if exists:
            return
            
        sentiment_entry = NewsSentimentModel(
            news_id=news_id,
            sentiment_label=sentiment["sentiment_label"],
            sentiment_score=sentiment["sentiment_score"],
            topic=topic,
            asset_mentioned=asset
        )
        self.db.add(sentiment_entry)
        self.db.commit()

    def get_all_sentiments_as_df(self) -> pd.DataFrame:
        """
        Returns all sentiments joined with news info.
        """
        query = self.db.query(
            NewsSentimentModel.news_id,
            NewsSentimentModel.sentiment_label,
            NewsSentimentModel.sentiment_score,
            NewsSentimentModel.topic,
            NewsSentimentModel.asset_mentioned,
            NewsModel.published_at,
            NewsModel.title,
        ).join(NewsModel, NewsModel.id == NewsSentimentModel.news_id)
        
        results = query.all()
        if not results:
            return pd.DataFrame()
            
        data = []
        for r in results:
            data.append({
                "news_id": r.news_id,
                "sentiment_label": r.sentiment_label,
                "sentiment_score": float(r.sentiment_score),
                "topic": r.topic,
                "asset_mentioned": r.asset_mentioned,
                "published_at": r.published_at,
                "title": r.title,
            })
            
        return pd.DataFrame(data)
