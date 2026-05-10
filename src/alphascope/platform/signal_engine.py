from __future__ import annotations

from alphascope.platform.config_models import PlatformConfig
from alphascope.platform.quant_models import MarketRegime, SignalContext, SignalDecision


class AdvancedSignalEngine:
    """Production-grade entry evaluator with explicit component scores."""

    def __init__(self, config: PlatformConfig) -> None:
        self.config = config

    def classify_regime(self, context: SignalContext) -> MarketRegime:
        if context.market_is_sideways:
            return MarketRegime.sideways
        if context.ma_fast > context.ma_slow and context.trend_strength >= 0.6 and context.momentum > 0:
            return MarketRegime.bull
        if context.ma_fast < context.ma_slow and context.momentum < 0:
            return MarketRegime.bear
        return MarketRegime.sideways

    def evaluate(self, context: SignalContext) -> SignalDecision:
        regime = self.classify_regime(context)
        trend_score = self._clamp(
            ((1.0 if context.ma_fast > context.ma_slow else 0.0) * 0.35)
            + ((1.0 if context.macd_histogram > 0 else 0.0) * 0.25)
            + (context.trend_strength * 0.40)
        )
        volume_score = self._clamp(min(context.relative_volume / 2.0, 1.0))
        volatility_score = self._clamp(1.0 - min(abs(context.volatility - 0.035) / 0.07, 1.0))
        momentum_score = self._clamp(
            ((1.0 if context.breakout_strength >= self.config.entry.min_breakout_strength else 0.0) * 0.45)
            + ((1.0 if context.momentum > 0 else 0.0) * 0.25)
            + min(abs(context.momentum), 1.0) * 0.30
        )
        technical_score = self._clamp(
            ((1.0 if context.rsi < self.config.entry.max_entry_rsi else 0.0) * 0.30)
            + ((1.0 if context.rsi >= 50 else 0.0) * 0.25)
            + ((1.0 if context.macd_histogram > 0 else 0.0) * 0.20)
            + ((1.0 if context.ma_fast > context.ma_slow else 0.0) * 0.25)
        )
        risk_score = self._clamp(1.0 - min(context.volatility / 0.12, 1.0))
        regime_score = {
            MarketRegime.bull: 1.0,
            MarketRegime.sideways: 0.25,
            MarketRegime.bear: 0.05,
        }[regime]
        total_score = self._clamp(
            (technical_score * self.config.weights.technical)
            + (trend_score * self.config.weights.trend)
            + (volatility_score * self.config.weights.volatility)
            + (volume_score * self.config.weights.volume)
            + (momentum_score * self.config.weights.momentum)
            + (risk_score * self.config.weights.risk)
            + (regime_score * self.config.weights.regime)
        )

        blocked_reasons: list[str] = []
        if context.rsi >= self.config.entry.max_entry_rsi:
            blocked_reasons.append("rsi_overbought")
        if trend_score < self.config.entry.min_trend_score:
            blocked_reasons.append("trend_not_confirmed")
        if volume_score < self.config.entry.min_relative_volume / 2.0:
            blocked_reasons.append("volume_below_average")
        if momentum_score < self.config.entry.min_momentum_score:
            blocked_reasons.append("momentum_missing")
        if self.config.entry.require_btc_confirmation and not context.btc_aligned:
            blocked_reasons.append("btc_not_confirmed")
        if self.config.entry.require_multi_timeframe_alignment and not context.timeframe_alignment:
            blocked_reasons.append("timeframes_misaligned")
        if self.config.entry.reject_sideways_market and regime is MarketRegime.sideways:
            blocked_reasons.append("sideways_market")

        should_buy = total_score >= self.config.entry.min_entry_score and not blocked_reasons
        return SignalDecision(
            symbol=context.symbol,
            should_buy=should_buy,
            regime=regime,
            total_score=total_score,
            trend_score=trend_score,
            volume_score=volume_score,
            volatility_score=volatility_score,
            momentum_score=momentum_score,
            blocked_reasons=blocked_reasons,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
