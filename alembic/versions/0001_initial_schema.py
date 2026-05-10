"""initial official storage schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_candles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.UniqueConstraint("timestamp", "symbol", "interval", name="uq_market_candle"),
    )
    op.create_index("ix_market_candles_timestamp", "market_candles", ["timestamp"])
    op.create_index("ix_market_candles_symbol", "market_candles", ["symbol"])
    op.create_index("ix_market_candles_interval", "market_candles", ["interval"])

    op.create_table(
        "technical_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("return_pct", sa.Float(), nullable=False),
        sa.Column("ma_short", sa.Float(), nullable=False),
        sa.Column("ma_long", sa.Float(), nullable=False),
        sa.Column("rsi", sa.Float(), nullable=False),
        sa.Column("volatility", sa.Float(), nullable=False),
        sa.Column("avg_volume", sa.Float(), nullable=False),
        sa.Column("relative_volume", sa.Float(), nullable=False),
        sa.Column("momentum", sa.Float(), nullable=False),
        sa.Column("trend_strength", sa.Float(), nullable=False),
        sa.UniqueConstraint("timestamp", "symbol", "interval", name="uq_technical_feature"),
    )
    op.create_index("ix_technical_features_timestamp", "technical_features", ["timestamp"])
    op.create_index("ix_technical_features_symbol", "technical_features", ["symbol"])
    op.create_index("ix_technical_features_interval", "technical_features", ["interval"])

    op.create_table(
        "asset_rankings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("heuristic_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("ml_probability", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("news_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("market_sentiment_adjustment", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("momentum_component", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("volume_component", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("trend_component", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("rsi_component", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("technical_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("trend_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("volatility_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("volume_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("risk_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("regime_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("market_regime", sa.String(length=16), server_default="sideways", nullable=False),
        sa.UniqueConstraint("timestamp", "symbol", "interval", name="uq_asset_ranking"),
    )
    op.create_index("ix_asset_rankings_timestamp", "asset_rankings", ["timestamp"])
    op.create_index("ix_asset_rankings_symbol", "asset_rankings", ["symbol"])
    op.create_index("ix_asset_rankings_interval", "asset_rankings", ["interval"])


def downgrade() -> None:
    op.drop_table("asset_rankings")
    op.drop_table("technical_features")
    op.drop_table("market_candles")
