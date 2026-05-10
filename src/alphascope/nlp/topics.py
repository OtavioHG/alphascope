"""Topic and asset inference helpers for financial news."""

from __future__ import annotations

import logging
import re
from importlib.util import find_spec

from transformers import pipeline

from alphascope.config.settings import settings

logger = logging.getLogger(__name__)

TOPICS = [
    "macro",
    "regulation",
    "security",
    "exchange",
    "adoption",
    "technology",
    "liquidity",
    "listing",
    "delisting",
]

ASSET_ALIASES = {
    "BITCOIN": "BTC",
    "BTC": "BTC",
    "ETHEREUM": "ETH",
    "ETH": "ETH",
    "SOLANA": "SOL",
    "SOL": "SOL",
    "BINANCE": "BNB",
    "BNB": "BNB",
    "RIPPLE": "XRP",
    "XRP": "XRP",
    "CARDANO": "ADA",
    "ADA": "ADA",
    "DOGECOIN": "DOGE",
    "DOGE": "DOGE",
}


class NewsTopicClassifier:
    """Classify topics with zero-shot transformers and detect related assets."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.nlp_topic_model_name
        if find_spec("torch") is None:
            logger.warning("PyTorch is not installed; topic model %s will run in heuristic fallback mode", self.model_name)
            self.classifier = None
            return
        try:
            self.classifier = pipeline("zero-shot-classification", model=self.model_name)
        except Exception as exc:
            logger.error("Failed to load topic model %s: %s", self.model_name, exc)
            self.classifier = None

    def classify_topic(self, text: str) -> str:
        if not text or self.classifier is None:
            return "macro"
        try:
            result = self.classifier(text[:512], TOPICS, multi_label=False)
            return str(result["labels"][0]) if result and result.get("labels") else "macro"
        except Exception as exc:
            logger.warning("Topic classification failed: %s", exc)
            return "macro"

    def extract_asset(self, text: str) -> str | None:
        text_upper = text.upper()
        for alias, symbol in ASSET_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", text_upper):
                return symbol
        return None
