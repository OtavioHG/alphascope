import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from alphascope.infrastructure.db.models import NewsModel
from alphascope.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class NewsIngestor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.NEWSAPI_KEY
        self.base_url = "https://newsapi.org/v2/everything"

    def fetch_news(self, query: str = "crypto", days_back: int = 7):
        """
        Fetches news from NewsAPI.
        """
        if not self.api_key:
            logger.error("NewsAPI key not configured.")
            return []

        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "apiKey": self.api_key,
            "language": "en"
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("articles", [])
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    def ingest_news(self, query: str, db: Session, days_back: int = 7):
        """
        Ingests news articles into the database.
        """
        articles = self.fetch_news(query, days_back)
        new_articles_count = 0

        for article in articles:
            # Check if article already exists by URL
            exists = db.query(NewsModel).filter(NewsModel.url == article["url"]).first()
            if not exists:
                try:
                    published_at = datetime.fromisoformat(article["publishedAt"].replace('Z', '+00:00'))
                    
                    news_entry = NewsModel(
                        title=article["title"],
                        content=article.get("description") or article.get("content"),
                        url=article["url"],
                        published_at=published_at,
                        source=article.get("source", {}).get("name")
                    )
                    db.add(news_entry)
                    new_articles_count += 1
                except Exception as e:
                    logger.warning(f"Failed to process article {article.get('url')}: {e}")

        db.commit()
        logger.info(f"Ingested {new_articles_count} new articles for query '{query}'.")
        return new_articles_count
