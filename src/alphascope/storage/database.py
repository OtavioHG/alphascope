"""Database bootstrap and session management."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from alphascope.config.settings import settings
from alphascope.core.logger import get_logger


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


logger = get_logger(__name__)
engine = create_engine(settings.database_url, future=True, echo=settings.echo_sql)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Compatibility aliases kept while legacy modules are being retired.
StorageBase = Base
StorageSessionLocal = SessionLocal
storage_engine = engine


@contextmanager
def session_scope() -> Session:
    """Provide a transactional session scope."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()



def init_database() -> None:
    """Create database tables if they do not exist."""
    from alphascope.agents.models import (
        AgentDebateRecord,
        AgentDecisionRecord,
        HistoricalPatternRecord,
        LosingTradePatternRecord,
        MarketContextMemoryRecord,
        MemoryRecord,
        ModelOutputRecord,
        NewsMemoryRecord,
        RiskMemoryRecord,
        RuntimeEventRecord,
        StrategyMemoryRecord,
        TradeAuditRecord,
        TradeConsensusRecord,
        WinningTradePatternRecord,
    )
    from alphascope.storage.models import (
        AccountSnapshot,
        AuditEvent,
        AssetRanking,
        DailyPerformance,
        FeatureSnapshot,
        LiveTradeFeedback,
        MarketCandle,
        MarketSnapshot,
        ModelPrediction,
        ModelVersion,
        OpenPosition,
        PaperTrade,
        PortfolioAnalyticsSnapshot,
        PortfolioSnapshot,
        RankingCycle,
        RankingHistory,
        RetrainingRun,
        RiskEvent,
        SignalHistory,
        TechnicalFeature,
        TradeExecution,
        TradeHistory,
    )

    _ = (
        MarketCandle,
        TechnicalFeature,
        AssetRanking,
        PaperTrade,
        PortfolioSnapshot,
        TradeExecution,
        TradeHistory,
        OpenPosition,
        RiskEvent,
        DailyPerformance,
        AccountSnapshot,
        AuditEvent,
        RankingCycle,
        RankingHistory,
        SignalHistory,
        MarketSnapshot,
        FeatureSnapshot,
        ModelPrediction,
        RetrainingRun,
        LiveTradeFeedback,
        ModelVersion,
        PortfolioAnalyticsSnapshot,
        AgentDecisionRecord,
        AgentDebateRecord,
        TradeConsensusRecord,
        TradeAuditRecord,
        RuntimeEventRecord,
        ModelOutputRecord,
        MemoryRecord,
        HistoricalPatternRecord,
        WinningTradePatternRecord,
        LosingTradePatternRecord,
        MarketContextMemoryRecord,
        NewsMemoryRecord,
        RiskMemoryRecord,
        StrategyMemoryRecord,
    )
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized", extra={"event": "database_initialized", "mode": settings.live_trading_mode})
