"""Agent debate engine."""

from __future__ import annotations

from alphascope.agents.schemas import AgentOutput, DebateMessage


class DebateEngine:
    def run(self, *, market: AgentOutput, news: AgentOutput, risk: AgentOutput, memory: AgentOutput) -> list[DebateMessage]:
        messages = [
            DebateMessage(round_id=1, speaker="market_intelligence", stance=market.signal, message=f"Mercado indica {market.signal.upper()}: {market.reasoning}"),
            DebateMessage(round_id=1, speaker="news_sentiment", stance=news.signal, message=f"Notícias indicam {news.signal.upper()}: {news.reasoning}"),
            DebateMessage(round_id=1, speaker="risk_manager", stance="allow" if risk.metadata.get("allow_trade") else "block", message=f"Risco avalia: {risk.reasoning}"),
            DebateMessage(round_id=1, speaker="memory_engine", stance=memory.signal, message=f"Memória histórica responde {memory.signal.upper()}: {memory.reasoning}"),
        ]
        if market.signal != news.signal:
            messages.append(
                DebateMessage(
                    round_id=2,
                    speaker="news_sentiment",
                    target_agent="market_intelligence",
                    stance="rebuttal",
                    message="Sentimento diverge do técnico; reduzir convicção e tamanho da posição.",
                )
            )
        if not risk.metadata.get("allow_trade", False):
            messages.append(
                DebateMessage(
                    round_id=2,
                    speaker="risk_manager",
                    target_agent="supervisor",
                    stance="block",
                    message="A operação deve ser bloqueada ou executada apenas em modo observação devido ao risco agregado.",
                )
            )
        elif market.signal == news.signal == memory.signal and market.signal != "hold":
            messages.append(
                DebateMessage(
                    round_id=2,
                    speaker="supervisor_agent",
                    stance="alignment",
                    message="Há alinhamento entre técnico, notícia e memória; consenso elevado.",
                )
            )
        return messages
