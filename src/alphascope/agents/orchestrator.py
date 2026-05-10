"""End-to-end multi-agent orchestration service."""

from __future__ import annotations

import logging
from typing import Any

from alphascope.agents.audit_engine import AuditEngine
from alphascope.agents.debate_engine import DebateEngine
from alphascope.agents.execution_agent import ExecutionAgent
from alphascope.agents.market_agent import MarketIntelligenceAgent
from alphascope.agents.memory_engine import MemoryEngine
from alphascope.agents.metrics import MultiAgentMetricsService
from alphascope.agents.news_agent import NewsSentimentAgent
from alphascope.agents.repository import MultiAgentRepository
from alphascope.agents.risk_agent import RiskManagementAgent
from alphascope.agents.schemas import MultiAgentContext, MultiAgentRunResult
from alphascope.agents.supervisor_agent import SupervisorAgent
from alphascope.alerts.alert_dispatcher import AlertDispatcher
from alphascope.alerts.telegram_notifier import TelegramNotifier
from alphascope.config.settings import settings
from alphascope.execution.trader_selector import build_trader

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    def __init__(self, repository: MultiAgentRepository | None = None) -> None:
        self.repository = repository or MultiAgentRepository()
        self.market_agent = MarketIntelligenceAgent()
        self.news_agent = NewsSentimentAgent()
        self.risk_agent = RiskManagementAgent()
        self.memory_engine = MemoryEngine(self.repository)
        self.debate_engine = DebateEngine()
        self.supervisor = SupervisorAgent(self.repository)
        self.execution_agent = ExecutionAgent()
        self.audit_engine = AuditEngine(self.repository)
        self.metrics = MultiAgentMetricsService()
        self.telegram = TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            enabled=settings.telegram_enabled,
        )
        self.alert_dispatcher = AlertDispatcher(telegram=self.telegram)

    def run(self, *, symbol: str, timeframe: str, mode: str = "paper", send_telegram: bool = True, execute_plan: bool = True) -> MultiAgentRunResult:
        raw_context = self.repository.build_context(symbol=symbol.upper(), timeframe=timeframe)
        context = MultiAgentContext(**raw_context)

        market_output = self.market_agent.analyze(context)
        news_output = self.news_agent.analyze(context)
        risk_output = self.risk_agent.analyze(context)
        memory_output = self.memory_engine.analyze(context)
        debate = self.debate_engine.run(market=market_output, news=news_output, risk=risk_output, memory=memory_output)
        supervisor = self.supervisor.supervise(market=market_output, news=news_output, risk=risk_output, memory=memory_output)
        execution = self.execution_agent.build_plan(
            symbol=symbol.upper(),
            supervisor=supervisor,
            risk_metadata=risk_output.metadata,
            account=context.account,
        )

        result = MultiAgentRunResult(
            symbol=symbol.upper(),
            timeframe=timeframe,
            market_output=market_output,
            news_output=news_output,
            risk_output=risk_output,
            memory_output=memory_output,
            debate=debate,
            supervisor=supervisor,
            execution=execution,
            mode=mode,
            runtime_event={
                "event_type": "multi_agent_cycle",
                "status": "completed",
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "summary": supervisor.reasoning,
            },
        )
        self._persist(result)
        if execute_plan and execution.action == "place_order":
            execution_result = self._execute_via_trader(result, context.account)
            result.runtime_event["execution_result"] = execution_result
        exported = self.memory_engine.export_training_datasets()
        result.exported_training_paths.extend(exported)
        if send_telegram:
            self.alert_dispatcher.multi_agent_decision(
                {
                    "symbol": result.symbol,
                    "timeframe": result.timeframe,
                    "decision": result.supervisor.decision,
                    "final_score": result.supervisor.final_score,
                    "consensus": result.supervisor.consensus,
                    "execution_action": result.execution.action,
                    "reasoning": result.supervisor.reasoning,
                }
            )
        return result

    def run_live(self, *, symbol: str, timeframe: str) -> MultiAgentRunResult:
        result = self.run(symbol=symbol, timeframe=timeframe, mode="live", send_telegram=True, execute_plan=True)
        return result

    def _execute_via_trader(self, result: MultiAgentRunResult, account: dict[str, Any]) -> dict[str, Any]:
        price = float(account.get("last_price", 0.0) or result.market_output.metadata.get("reference_price", 0.0) or result.market_output.metadata.get("close", 0.0) or 0.0)
        if price <= 0:
            price = float(result.market_output.metadata.get("last_close", 0.0) or 1.0)
        trader = build_trader(repository=self.repository.storage)
        try:
            if hasattr(trader, "execute_multi_agent_plan"):
                execution_result = trader.execute_multi_agent_plan(
                    symbol=result.symbol,
                    side=result.execution.side,
                    price=price,
                    final_score=result.supervisor.final_score,
                    execution_plan=result.execution.to_dict(),
                    supervisor=result.supervisor.to_dict(),
                    market_output=result.market_output.to_dict(),
                    news_output=result.news_output.to_dict(),
                    risk_output=result.risk_output.to_dict(),
                    memory_output=result.memory_output.to_dict(),
                )
            else:
                execution_result = {"status": "ignored", "reason": "selected_trader_has_no_multi_agent_interface"}
        except Exception as exc:
            logger.exception("multi_agent_trader_execution_failed symbol=%s", result.symbol)
            self.repository.save_runtime_event(
                {
                    "event_type": "multi_agent_execution_failure",
                    "status": "error",
                    "symbol": result.symbol,
                    "timeframe": result.timeframe,
                    "summary": str(exc),
                    "payload_json": {"symbol": result.symbol, "error": str(exc), "mode": result.mode},
                    "created_at": result.supervisor.created_at.isoformat(),
                }
            )
            execution_result = {"status": "blocked", "reason": str(exc)}
        return execution_result

    def _persist(self, result: MultiAgentRunResult) -> None:
        payload = result.to_dict()
        logger.info("[Market Agent] %s", result.market_output.reasoning)
        logger.info("[News Agent] %s", result.news_output.reasoning)
        logger.info("[Risk Agent] %s", result.risk_output.reasoning)
        logger.info("[Supervisor] Consensus reached: %s", result.supervisor.decision)
        logger.info("[Execution] %s", result.execution.reasoning)

        self.repository.save_agent_output(symbol=result.symbol, timeframe=result.timeframe, output=payload["market_output"])
        self.repository.save_agent_output(symbol=result.symbol, timeframe=result.timeframe, output=payload["news_output"])
        self.repository.save_agent_output(symbol=result.symbol, timeframe=result.timeframe, output=payload["risk_output"])
        self.repository.save_agent_output(symbol=result.symbol, timeframe=result.timeframe, output=payload["memory_output"])
        self.repository.save_debate_messages(symbol=result.symbol, timeframe=result.timeframe, debate=payload["debate"])
        self.repository.save_consensus(payload["supervisor"], symbol=result.symbol, timeframe=result.timeframe)
        self.repository.open_execution_intent(
            symbol=result.symbol,
            timeframe=result.timeframe,
            execution=payload["execution"],
            consensus=payload["supervisor"],
        )
        self.repository.save_runtime_event(payload["runtime_event"])
        self.audit_engine.persist_full_audit(payload)
        self.memory_engine.persist_context_memory(payload)
        self.metrics.record_decision(payload)

    @staticmethod
    def _render_telegram_message(result: MultiAgentRunResult) -> str:
        return "\n".join(
            [
                "🚀 Multi-Agent Trade Approved",
                f"Symbol: {result.symbol}",
                f"Decision: {result.supervisor.decision}",
                f"Consensus: {result.supervisor.consensus}",
                f"Final Score: {result.supervisor.final_score:.4f}",
                f"Stop Loss: {result.execution.stop_loss:.3f}%",
                f"Take Profit: {result.execution.take_profit:.3f}%",
            ]
        )

    def close(self) -> None:
        self.telegram.close()
