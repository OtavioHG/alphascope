from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class RiskProfile(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"
    sniper = "sniper"
    scalping = "scalping"


class ScoreWeights(BaseModel):
    technical: float = 0.25
    trend: float = 0.15
    volatility: float = 0.10
    volume: float = 0.15
    momentum: float = 0.15
    risk: float = 0.10
    regime: float = 0.05
    news: float = 0.05


class EntryPolicy(BaseModel):
    min_entry_score: float = 0.72
    max_entry_rsi: float = 72.0
    min_relative_volume: float = 1.15
    min_breakout_strength: float = 0.01
    min_momentum_score: float = 0.55
    min_trend_score: float = 0.60
    require_btc_confirmation: bool = True
    require_multi_timeframe_alignment: bool = True
    reject_sideways_market: bool = True


class ExitPolicy(BaseModel):
    partial_take_profit_levels: list[float] = Field(default_factory=lambda: [0.02, 0.04, 0.07])
    partial_take_profit_sizes: list[float] = Field(default_factory=lambda: [0.25, 0.35, 0.40])
    trailing_stop_pct: float = 0.0125
    break_even_trigger_pct: float = 0.01
    max_trade_hours: int = 24
    score_exit_threshold: float = 0.48
    rank_exit_threshold: int = 1
    momentum_floor: float = 0.40
    stronger_asset_gap: float = 0.18


class RiskPolicy(BaseModel):
    profile: RiskProfile = RiskProfile.moderate
    max_trades_per_day: int = 8
    max_consecutive_losses: int = 3
    daily_drawdown_pause_pct: float = 0.04
    emergency_drawdown_pct: float = 0.08
    max_symbol_exposure_pct: float = 0.12
    max_portfolio_exposure_pct: float = 0.55
    max_simultaneous_positions: int = 4
    max_position_size_pct: float = 0.10
    min_cash_reserve_pct: float = 0.20
    same_symbol_cooldown_minutes: int = 60
    reduce_size_after_loss_factor: float = 0.75
    volatile_asset_threshold: float = 0.09


class TelegramPolicy(BaseModel):
    enabled: bool = False
    allow_remote_trading: bool = False
    top_n_summary: int = 5
    commands_enabled: list[str] = Field(
        default_factory=lambda: [
            "/start",
            "/status",
            "/dashboard",
            "/positions",
            "/ranking",
            "/history",
            "/risk",
            "/startbot",
            "/stopbot",
            "/restartbot",
            "/sellall",
            "/buy",
            "/sell",
            "/top",
            "/logs",
            "/errors",
            "/pnl",
            "/winrate",
            "/config",
            "/help",
        ]
    )


class PlatformPaths(BaseModel):
    config_root: Path = Path("config")
    strategies_dir: Path = Path("config/strategies")
    risk_dir: Path = Path("config/risk")
    telegram_dir: Path = Path("config/telegram")
    env_dir: Path = Path("config/env")


class PlatformConfig(BaseModel):
    weights: ScoreWeights = Field(default_factory=ScoreWeights)
    entry: EntryPolicy = Field(default_factory=EntryPolicy)
    exit: ExitPolicy = Field(default_factory=ExitPolicy)
    risk: RiskPolicy = Field(default_factory=RiskPolicy)
    telegram: TelegramPolicy = Field(default_factory=TelegramPolicy)
    paths: PlatformPaths = Field(default_factory=PlatformPaths)

