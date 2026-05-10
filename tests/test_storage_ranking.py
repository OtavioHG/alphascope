from __future__ import annotations

from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from alphascope.storage.database import Base
from alphascope.storage.models import AssetRanking
from alphascope.storage.repositories import StorageRepository


def test_asset_ranking_orm_accepts_hybrid_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)

    with local_session() as session:
        session.add(
            AssetRanking(
                timestamp=pd.Timestamp("2026-03-23T00:00:00Z").to_pydatetime(),
                symbol="BTCUSDT",
                interval="1h",
                score=0.82,
                rank=1,
                heuristic_score=0.70,
                ml_probability=0.91,
                news_score=0.66,
                market_sentiment_adjustment=0.05,
                momentum_component=0.8,
                volume_component=0.7,
                trend_component=0.9,
                rsi_component=0.6,
            )
        )
        session.commit()
        stored = session.execute(select(AssetRanking)).scalar_one()

    assert stored.heuristic_score == 0.70
    assert stored.ml_probability == 0.91
    assert stored.news_score == 0.66
    assert stored.market_sentiment_adjustment == 0.05


def test_storage_repository_saves_hybrid_ranking_fields(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    @contextmanager
    def local_session_scope() -> Session:
        session = local_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr("alphascope.storage.repositories.SessionLocal", local_session)
    monkeypatch.setattr("alphascope.storage.repositories.session_scope", local_session_scope)

    repository = StorageRepository()
    ranking = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2026-03-23T00:00:00Z").to_pydatetime(),
                "symbol": "BTCUSDT",
                "score": 0.81,
                "rank": 1,
                "heuristic_score": 0.62,
                "ml_probability": 0.87,
                "news_score": 0.58,
                "market_sentiment_adjustment": 0.05,
                "momentum_component": 0.75,
                "volume_component": 0.65,
                "trend_component": 0.78,
                "rsi_component": 0.61,
            }
        ]
    )

    saved = repository.save_ranking(ranking, interval="1h")
    latest = repository.get_latest_ranking(interval="1h")

    assert saved == 1
    assert not latest.empty
    assert float(latest.loc[0, "heuristic_score"]) == 0.62
    assert float(latest.loc[0, "ml_probability"]) == 0.87
    assert float(latest.loc[0, "news_score"]) == 0.58
    assert float(latest.loc[0, "market_sentiment_adjustment"]) == 0.05


def test_storage_repository_normalizes_final_score_to_score(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    @contextmanager
    def local_session_scope() -> Session:
        session = local_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr("alphascope.storage.repositories.SessionLocal", local_session)
    monkeypatch.setattr("alphascope.storage.repositories.session_scope", local_session_scope)

    repository = StorageRepository()
    ranking = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2026-03-23T00:00:00Z").to_pydatetime(),
                "symbol": "BTCUSDT",
                "final_score": 0.93,
                "rank": 1,
                "heuristic_score": 0.62,
            }
        ]
    )

    saved = repository.save_ranking(ranking, interval="1h")
    latest = repository.get_latest_ranking(interval="1h")

    assert saved == 1
    assert not latest.empty
    assert "score" in latest.columns
    assert float(latest.loc[0, "score"]) == 0.93
    assert pd.notna(latest.loc[0, "score"])
