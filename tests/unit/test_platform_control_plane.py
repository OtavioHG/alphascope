from __future__ import annotations

from datetime import UTC, datetime, timedelta

from alphascope.platform.config_loader import PlatformConfigLoader
from alphascope.platform.quant_models import PortfolioRiskState, PositionContext, SignalContext
from alphascope.platform.risk_engine import AdvancedRiskEngine
from alphascope.platform.signal_engine import AdvancedSignalEngine
from alphascope.platform.exit_engine import ExitDecisionEngine


def test_platform_config_loader_reads_repo_configuration() -> None:
    config = PlatformConfigLoader().load(risk_profile="aggressive", strategy_name="swing")

    assert config.risk.profile.value == "aggressive"
    assert config.entry.min_entry_score >= 0.70
    assert config.telegram.top_n_summary == 5


def test_advanced_signal_engine_blocks_sideways_and_overbought_entries() -> None:
    config = PlatformConfigLoader().load()
    engine = AdvancedSignalEngine(config)

    decision = engine.evaluate(
        SignalContext(
            symbol="ETHUSDT",
            close=3000.0,
            rsi=79.0,
            macd_histogram=0.5,
            ma_fast=3010.0,
            ma_slow=2990.0,
            trend_strength=0.8,
            relative_volume=1.8,
            volatility=0.03,
            momentum=0.6,
            breakout_strength=0.02,
            btc_aligned=True,
            timeframe_alignment=True,
            market_is_sideways=True,
        )
    )

    assert not decision.should_buy
    assert "rsi_overbought" in decision.blocked_reasons
    assert "sideways_market" in decision.blocked_reasons


def test_advanced_risk_engine_pauses_after_drawdown_and_scales_after_losses() -> None:
    config = PlatformConfigLoader().load()
    engine = AdvancedRiskEngine(config)

    paused = engine.evaluate(
        PortfolioRiskState(
            equity=10_000.0,
            free_cash=4_000.0,
            daily_pnl_pct=-0.05,
            open_positions=1,
            daily_trades=2,
            consecutive_losses=1,
            portfolio_exposure_pct=0.20,
            symbol_exposure_pct=0.05,
            candidate_volatility=0.03,
        )
    )
    approved = engine.evaluate(
        PortfolioRiskState(
            equity=10_000.0,
            free_cash=7_000.0,
            daily_pnl_pct=-0.01,
            open_positions=1,
            daily_trades=2,
            consecutive_losses=1,
            portfolio_exposure_pct=0.20,
            symbol_exposure_pct=0.05,
            candidate_volatility=0.03,
        )
    )

    assert not paused.approved
    assert paused.pause_trading
    assert approved.approved
    assert approved.recommended_position_pct < config.risk.max_position_size_pct


def test_exit_engine_emits_break_even_partial_and_close_actions() -> None:
    config = PlatformConfigLoader().load()
    engine = ExitDecisionEngine(config)

    decisions = engine.evaluate(
        PositionContext(
            symbol="SOLUSDT",
            entry_price=100.0,
            current_price=105.0,
            quantity=1.0,
            score=0.35,
            current_rank=3,
            best_alternative_score_gap=0.2,
            momentum_score=0.2,
            trailing_stop_price=101.0,
            stop_loss_price=96.0,
            opened_at=datetime.now(UTC) - timedelta(hours=30),
            now=datetime.now(UTC),
            realized_partial_pct=0.0,
        )
    )

    actions = {item.action for item in decisions}
    reasons = {item.reason for item in decisions}
    assert "MOVE_STOP" in actions
    assert "PARTIAL_SELL" in actions
    assert "CLOSE" in actions
    assert "score_deterioration" in reasons
