from __future__ import annotations

import pandas as pd

from alphascope.datasets.dataset_merger import DatasetMerger
from alphascope.datasets.news_dataset_builder import NewsDatasetBuilder


class FakeGDELTClient:
    def fetch_articles(self, query: str, *, max_records: int = 50, days: int = 1) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "title": "Bitcoin jumps",
                    "description": "BTC rallies after ETF flows",
                    "text": "Bitcoin rallies after ETF inflows.",
                    "timestamp": "2025-01-01T10:00:00Z",
                    "source": "example.com",
                    "link": "https://example.com/btc",
                    "dataset_source": "gdelt",
                }
            ]
        )


class FakeHuggingFaceLoader:
    def load_financial_phrasebank(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"text": "Company outlook improves.", "label": 2, "dataset_source": "huggingface_financial_phrasebank"},
            ]
        )

    def load_export(self, path: str) -> pd.DataFrame:
        return pd.DataFrame()


class FakeKaggleLoader:
    def load(self, path: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "headline": "Bitcoin jumps",
                    "summary": "BTC rallies after ETF flows",
                    "content": "Bitcoin rallies after ETF inflows.",
                    "published_at": "2025-01-01T10:00:00Z",
                    "domain": "example.com",
                    "url": "https://example.com/btc",
                    "dataset_source": "kaggle",
                }
            ]
        )


def test_dataset_merger_normalizes_and_deduplicates_news_rows() -> None:
    merger = DatasetMerger()
    merged = merger.merge_news_frames(
        [
            pd.DataFrame(
                [
                    {
                        "headline": "Bitcoin jumps",
                        "summary": "BTC rallies after ETF flows",
                        "content": "Bitcoin rallies after ETF inflows.",
                        "published_at": "2025-01-01T10:00:00Z",
                    }
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "title": "Bitcoin jumps",
                        "description": "BTC rallies after ETF flows",
                        "text": "Bitcoin rallies after ETF inflows.",
                        "timestamp": "2025-01-01T10:00:00Z",
                    }
                ]
            ),
        ]
    )

    assert len(merged) == 1
    assert merged.loc[0, "clean_text"].startswith("Bitcoin jumps")


def test_news_dataset_builder_combines_multiple_sources() -> None:
    builder = NewsDatasetBuilder(
        gdelt_client=FakeGDELTClient(),
        huggingface_loader=FakeHuggingFaceLoader(),
        kaggle_loader=FakeKaggleLoader(),
    )

    dataset = builder.build(
        gdelt_query="bitcoin",
        include_huggingface_financial_phrasebank=True,
        kaggle_export_path="ignored.csv",
        export=False,
    )

    assert len(dataset) == 2
    assert set(dataset["dataset_source"]) == {"gdelt", "huggingface_financial_phrasebank"}


def test_gdelt_client_wraps_or_queries() -> None:
    from alphascope.news_sources.gdelt_client import GDELTNewsClient

    assert GDELTNewsClient._normalize_query("crypto OR bitcoin OR ethereum") == "(crypto OR bitcoin OR ethereum)"
    assert GDELTNewsClient._normalize_query("(crypto OR bitcoin)") == "(crypto OR bitcoin)"
