from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class FeatureDefinition:
    name: str
    description: str
    source: str
    online_ready: bool = True
    version: str = "v1"
    owner: str = "alphascope"
    tags: tuple[str, ...] = ()


class FeatureRegistry:
    def __init__(self, output_dir: str = "data/processed/feature_store"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.output_dir / "feature_registry.json"
        self._features: dict[str, FeatureDefinition] = {}
        for feature in (
            FeatureDefinition("RSI", "Relative Strength Index", "technical", tags=("momentum", "oscillator")),
            FeatureDefinition("MACD", "Moving Average Convergence Divergence", "technical", tags=("trend", "momentum")),
            FeatureDefinition("Bollinger", "Bollinger Bands", "technical", tags=("volatility", "bands")),
            FeatureDefinition("volatility", "Rolling volatility", "technical", tags=("risk", "volatility")),
            FeatureDefinition("volume_ratio", "Relative volume", "technical", tags=("volume",)),
            FeatureDefinition("sentiment_score", "Average sentiment score", "nlp", tags=("sentiment", "news")),
            FeatureDefinition("news_count", "News count per window", "nlp", tags=("news", "flow")),
            FeatureDefinition("momentum", "Recent momentum", "technical", tags=("momentum",)),
        ):
            self.register(feature)

    def register(self, feature: FeatureDefinition) -> None:
        self._features[feature.name] = feature
        self._persist()

    def list_features(self) -> list[FeatureDefinition]:
        return list(self._features.values())

    def get(self, name: str) -> FeatureDefinition | None:
        return self._features.get(name)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "name": feature.name,
                    "description": feature.description,
                    "source": feature.source,
                    "online_ready": feature.online_ready,
                    "version": feature.version,
                    "owner": feature.owner,
                    "tags": list(feature.tags),
                }
                for feature in self.list_features()
            ]
        )

    def _persist(self) -> None:
        payload = [
            {
                "name": feature.name,
                "description": feature.description,
                "source": feature.source,
                "online_ready": feature.online_ready,
                "version": feature.version,
                "owner": feature.owner,
                "tags": list(feature.tags),
            }
            for feature in self.list_features()
        ]
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
