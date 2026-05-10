from transformers import pipeline
from typing import Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

class NewsTopicClassifier:
    """
    Classifies news topics and extracts mentioned assets.
    """
    
    TOPICS = [
        "macro", "regulation", "security", "exchange", 
        "adoption", "technology", "liquidity", "listing", "delisting"
    ]
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        """
        Initializes zero-shot classification for topics.
        """
        try:
            self.classifier = pipeline("zero-shot-classification", model=model_name)
        except Exception as e:
            logger.error(f"Failed to load topic model {model_name}: {e}")
            self.classifier = None

    def classify_topic(self, text: str) -> str:
        """
        Uses zero-shot classification to find the best topic.
        """
        if not self.classifier or not text:
            return "macro"
        
        try:
            results = self.classifier(text[:512], self.TOPICS, multi_label=False)
            if results and results["labels"]:
                return results["labels"][0]
        except Exception as e:
            logger.warning(f"Error classifying topic: {e}")
            
        return "macro"

    def extract_asset(self, text: str) -> Optional[str]:
        """
        Extracts mentioned crypto assets using basic keyword matching.
        This is a simple V1 implementation.
        """
        # Mapping names to symbols
        asset_map = {
            "BITCOIN": "BTC",
            "ETHEREUM": "ETH",
            "SOLANA": "SOL",
            "BINANCE": "BNB",
            "RIPPLE": "XRP",
            "CARDANO": "ADA",
            "DOGECOIN": "DOGE",
            "POLKADOT": "DOT",
            "POLYGON": "MATIC"
        }
        
        # Common symbols as fallback
        common_symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "MATIC"]
        
        text_upper = text.upper()
        
        # Check for full names
        for name, symbol in asset_map.items():
            if name in text_upper:
                return symbol
                
        # Check for symbols
        for symbol in common_symbols:
            if re.search(rf"\b{symbol}\b", text_upper):
                return symbol
        
        return None
