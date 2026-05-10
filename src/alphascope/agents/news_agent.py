"""News and sentiment agent using local proxies/fallbacks."""

from __future__ import annotations

from alphascope.agents.schemas import AgentOutput, MultiAgentContext
from alphascope.agents.scoring_engine import ScoringEngine
from alphascope.config.settings import settings


class NewsSentimentAgent:

    def analyze(self, context: MultiAgentContext) -> AgentOutput:
        ranking = context.ranking or {}
        snapshots = context.market_snapshots or []
        latest_snapshot = snapshots[0] if snapshots else {}
        news_score = float(ranking.get("news_score", latest_snapshot.get("news_score", 0.5)) or 0.5)
        sentiment_adjustment = float(ranking.get("market_sentiment_adjustment", latest_snapshot.get("sentiment_score", 0.0)) or 0.0)
        fear_greed = float(latest_snapshot.get("fear_greed_value", 50.0) or 50.0)
        reasons: list[str] = []

        combined = max(0.0, min(1.0, 0.5 + (news_score - 0.5) * 0.75 + sentiment_adjustment * 0.25 + ((fear_greed - 50.0) / 100.0) * 0.10))
        if combined >= 0.67:
            signal = "buy"
            reasons.append("Fluxo de notícias e sentimento favorecem alta")
        elif combined <= 0.33:
            signal = "sell"
            reasons.append("Sentimento agregado está defensivo")
        else:
            signal = "hold"
            reasons.append("Noticiário sem convicção suficiente")

        if fear_greed >= 65:
            reasons.append("Fear & Greed em zona otimista")
        elif fear_greed <= 35:
            reasons.append("Fear & Greed em zona de medo")
        if sentiment_adjustment > 0:
            reasons.append("Ajuste de sentimento positivo")
        elif sentiment_adjustment < 0:
            reasons.append("Ajuste de sentimento negativo")

        confidence = max(0.30, min(0.90, abs(combined - 0.5) * 1.5 + 0.40))
        model_config = settings.multi_agent_model_registry["news"]
        remote_ready = bool(model_config["external"]) and bool(snapshots)
        return AgentOutput(
            agent="news_sentiment",
            signal=signal,
            confidence=confidence,
            score=ScoringEngine.signal_score(signal, confidence),
            reasoning=", ".join(reasons[:4]),
            metadata={
                "sentiment": "bullish" if combined > 0.55 else "bearish" if combined < 0.45 else "neutral",
                "news_score": round(news_score, 4),
                "fear_greed": round(fear_greed, 2),
                "sentiment_adjustment": round(sentiment_adjustment, 4),
                "inference_backend": "local_sentiment_proxy",
                "external_llm_available": settings.external_llm_available,
                "has_recent_news_snapshots": bool(snapshots),
                "configured_primary_model": model_config["primary"],
                "configured_fallback_model": model_config["fallback"],
            },
            model_name=str(model_config["active"] if remote_ready else model_config["fallback"]),
            fallback_used=not remote_ready,
        )
