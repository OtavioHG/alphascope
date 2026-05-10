"""Market intelligence agent."""

from __future__ import annotations

from typing import Any

from alphascope.agents.schemas import AgentOutput, MultiAgentContext
from alphascope.agents.scoring_engine import ScoringEngine
from alphascope.config.settings import settings


class MarketIntelligenceAgent:

    def analyze(self, context: MultiAgentContext) -> AgentOutput:
        features = context.features or {}
        ranking = context.ranking or {}
        rsi = float(features.get("rsi", 50.0) or 50.0)
        momentum = float(features.get("momentum", 0.0) or 0.0)
        relative_volume = float(features.get("relative_volume", 1.0) or 1.0)
        ma_short = float(features.get("ma_short", features.get("close", 0.0)) or 0.0)
        ma_long = float(features.get("ma_long", ma_short) or ma_short)
        volatility = float(features.get("volatility", 0.0) or 0.0)
        trend_strength = float(features.get("trend_strength", 0.0) or 0.0)
        ranking_score = float(ranking.get("score", 0.5) or 0.5)
        regime = str(ranking.get("market_regime", "sideways"))

        bullish = 0
        bearish = 0
        reasons: list[str] = []

        if ma_short >= ma_long:
            bullish += 1
            reasons.append("SMA curta acima da longa")
        else:
            bearish += 1
            reasons.append("SMA curta abaixo da longa")

        if 45 <= rsi <= 68:
            bullish += 1
            reasons.append("RSI em zona saudável para continuação")
        elif rsi > 72:
            bearish += 1
            reasons.append("RSI em sobrecompra")
        elif rsi < 35:
            bullish += 1
            reasons.append("RSI em sobrevenda com potencial de reversão")

        if momentum > 0:
            bullish += 1
            reasons.append("Momentum positivo")
        elif momentum < 0:
            bearish += 1
            reasons.append("Momentum negativo")

        if relative_volume >= 1.2:
            bullish += 1
            reasons.append("Volume relativo acima de 1.2x")
        elif relative_volume < 0.8:
            bearish += 1
            reasons.append("Volume relativo fraco")

        if volatility > 0.08:
            bearish += 1
            reasons.append("Volatilidade elevada")
        if regime.lower() in {"bullish", "trending_up", "risk_on"}:
            bullish += 1
            reasons.append("Regime de mercado favorável")
        if trend_strength > 0:
            bullish += 1

        raw_score = max(0.0, min(1.0, 0.5 + ((bullish - bearish) * 0.08) + (ranking_score - 0.5) * 0.35))
        if raw_score >= 0.67:
            signal = "buy"
        elif raw_score <= 0.33:
            signal = "sell"
        else:
            signal = "hold"
        confidence = max(0.35, min(0.95, abs(raw_score - 0.5) * 1.8 + 0.45))
        score = ScoringEngine.signal_score(signal, confidence)
        model_config = settings.multi_agent_model_registry["market"]
        return AgentOutput(
            agent="market_intelligence",
            signal=signal,
            confidence=confidence,
            score=score,
            reasoning=", ".join(reasons[:5]) or "Dados insuficientes, mantendo neutralidade",
            metadata={
                "trend": "bullish" if ma_short >= ma_long else "bearish",
                "breakout_strength": round(max(0.0, min(1.0, relative_volume / 2.0 + momentum)), 4),
                "relative_volume": round(relative_volume, 4),
                "volatility": round(volatility, 6),
                "market_regime": regime,
                "close": float(features.get("close", 0.0) or 0.0),
                "last_close": float(features.get("close", 0.0) or 0.0),
                "inference_backend": "local_heuristic_proxy",
                "external_llm_available": settings.external_llm_available,
                "configured_primary_model": model_config["primary"],
                "configured_fallback_model": model_config["fallback"],
            },
            model_name=str(model_config["active"]),
            fallback_used=not bool(model_config["external"]),
        )
