"""multi-agent storage schema

Revision ID: 0002_multi_agent_schema
Revises: 0001_initial_schema
Create Date: 2026-04-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_multi_agent_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _create_memory_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index(f"ix_{name}_created_at", name, ["created_at"])
    op.create_index(f"ix_{name}_symbol", name, ["symbol"])
    op.create_index(f"ix_{name}_timeframe", name, ["timeframe"])


def upgrade() -> None:
    op.create_table(
        "agent_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("signal", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("model_name", sa.String(length=128), nullable=False, server_default="local"),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "symbol", "timeframe", "agent_name", "signal"):
        op.create_index(f"ix_agent_decisions_{column}", "agent_decisions", [column])

    op.create_table(
        "agent_debates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("speaker", sa.String(length=64), nullable=False),
        sa.Column("stance", sa.String(length=32), nullable=False),
        sa.Column("target_agent", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "symbol", "timeframe", "speaker", "stance"):
        op.create_index(f"ix_agent_debates_{column}", "agent_debates", [column])

    op.create_table(
        "trade_consensus",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("consensus", sa.String(length=128), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "symbol", "timeframe", "decision"):
        op.create_index(f"ix_trade_consensus_{column}", "trade_consensus", [column])

    op.create_table(
        "trade_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "symbol", "timeframe", "decision"):
        op.create_index(f"ix_trade_audit_{column}", "trade_audit", [column])

    op.create_table(
        "runtime_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("timeframe", sa.String(length=10), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "event_type", "status", "symbol", "timeframe"):
        op.create_index(f"ix_runtime_events_{column}", "runtime_events", [column])

    op.create_table(
        "model_outputs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("output_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "symbol", "timeframe", "provider", "model_name", "output_type"):
        op.create_index(f"ix_model_outputs_{column}", "model_outputs", [column])

    _create_memory_table("agent_memory")
    op.create_table(
        "historical_patterns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    for column in ("created_at", "symbol", "timeframe", "pattern_type"):
        op.create_index(f"ix_historical_patterns_{column}", "historical_patterns", [column])

    for name in ("winning_trade_patterns", "losing_trade_patterns"):
        op.create_table(
            name,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("timeframe", sa.String(length=10), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        )
        for column in ("created_at", "symbol", "timeframe"):
            op.create_index(f"ix_{name}_{column}", name, [column])

    _create_memory_table("market_context_memory")
    _create_memory_table("news_memory")
    _create_memory_table("risk_memory")
    _create_memory_table("strategy_memory")


def downgrade() -> None:
    for name in (
        "strategy_memory",
        "risk_memory",
        "news_memory",
        "market_context_memory",
        "losing_trade_patterns",
        "winning_trade_patterns",
        "historical_patterns",
        "agent_memory",
        "model_outputs",
        "runtime_events",
        "trade_audit",
        "trade_consensus",
        "agent_debates",
        "agent_decisions",
    ):
        op.drop_table(name)
