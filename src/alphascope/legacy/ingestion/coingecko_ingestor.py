import requests
from sqlalchemy.orm import Session
from alphascope.infrastructure.db.models import AssetModel
from alphascope.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class CoinGeckoIngestor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.COINGECKO_API_KEY
        self.base_url = "https://api.coingecko.com/api/v3"
        self.headers = {"accept": "application/json"}
        if self.api_key:
            self.headers["x-cg-demo-api-key"] = self.api_key

    def fetch_trending(self):
        """
        Fetches trending coins from CoinGecko.
        """
        url = f"{self.base_url}/search/trending"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("coins", [])
        except Exception as e:
            logger.error(f"Error fetching trending coins: {e}")
            return []

    def ingest_trending(self, db: Session):
        """
        Ingests trending coins metadata (basic v1 implementation).
        Ensures they exist in the assets table.
        """
        trending_coins = self.fetch_trending()
        new_assets_count = 0

        for coin_data in trending_coins:
            item = coin_data.get("item", {})
            symbol = f"{item['symbol'].upper()}/USDT" # Standardizing for v1
            
            exists = db.query(AssetModel).filter(AssetModel.symbol == symbol).first()
            if not exists:
                try:
                    asset = AssetModel(
                        symbol=symbol,
                        base_asset=item['symbol'].upper(),
                        quote_asset="USDT",
                        exchange="coingecko_trending"
                    )
                    db.add(asset)
                    new_assets_count += 1
                except Exception as e:
                    logger.warning(f"Failed to process coin {symbol}: {e}")

        db.commit()
        logger.info(f"Ingested {new_assets_count} new trending coins from CoinGecko.")
        return new_assets_count
