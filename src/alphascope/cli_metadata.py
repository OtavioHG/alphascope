from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandProfile:
    legacy_name: str
    canonical_path: tuple[str, ...]
    category: str
    needs_database: bool = True
    needs_repository: bool = True
    needs_pipeline: bool = False
    needs_aggregator: bool = False
    needs_universe_builder: bool = False
    aliases: tuple[str, ...] = field(default_factory=tuple)


COMMAND_PROFILES: dict[str, CommandProfile] = {
    "ingest-market": CommandProfile("ingest-market", ("market", "ingest"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "build-features": CommandProfile("build-features", ("market", "features", "build"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "rank-assets": CommandProfile("rank-assets", ("market", "ranking", "run"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "explain-ranking": CommandProfile("explain-ranking", ("market", "ranking", "explain"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "backtest": CommandProfile("backtest", ("market", "backtest", "run"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "paper-trade": CommandProfile("paper-trade", ("market", "paper", "run"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "run-pipeline": CommandProfile("run-pipeline", ("market", "pipeline", "run"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "run-loop": CommandProfile("run-loop", ("market", "pipeline", "loop"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "build-universe": CommandProfile("build-universe", ("market", "universe", "build"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "show-data": CommandProfile("show-data", ("market", "data", "show"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "fetch-market-universe": CommandProfile("fetch-market-universe", ("market", "universe", "fetch"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "show-universe": CommandProfile("show-universe", ("market", "universe", "show"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "run-auto-universe": CommandProfile("run-auto-universe", ("market", "universe", "auto-run"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "compare-sources": CommandProfile("compare-sources", ("market", "sources", "compare"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "fetch-cryptocompare-history": CommandProfile("fetch-cryptocompare-history", ("market", "sources", "cryptocompare-history"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "fetch-fear-greed": CommandProfile("fetch-fear-greed", ("market", "sentiment", "fear-greed"), "market", needs_pipeline=True, needs_aggregator=True, needs_universe_builder=True),
    "build-training-dataset": CommandProfile("build-training-dataset", ("data", "dataset", "build-training"), "data", needs_pipeline=True),
    "build-market-dataset": CommandProfile("build-market-dataset", ("data", "dataset", "build-market"), "data", needs_pipeline=True),
    "import-market-dataset": CommandProfile("import-market-dataset", ("data", "dataset", "import-market"), "data", needs_pipeline=True),
    "train-market-model": CommandProfile("train-market-model", ("ml", "market", "train"), "ml", needs_pipeline=True),
    "evaluate-market-model": CommandProfile("evaluate-market-model", ("ml", "market", "evaluate"), "ml", needs_pipeline=True),
    "predict-market": CommandProfile("predict-market", ("ml", "market", "predict"), "ml", needs_pipeline=True),
    "ingest-news": CommandProfile("ingest-news", ("news", "ingest"), "news", needs_pipeline=True),
    "build-news-dataset": CommandProfile("build-news-dataset", ("news", "dataset", "build"), "news", needs_pipeline=True),
    "train-news-model": CommandProfile("train-news-model", ("ml", "news", "train"), "ml", needs_pipeline=True),
    "import-news-dataset": CommandProfile("import-news-dataset", ("news", "dataset", "import"), "news", needs_pipeline=True),
    "list-external-datasets": CommandProfile("list-external-datasets", ("data", "dataset", "list-external"), "data", needs_pipeline=True),
    "show-news-signals": CommandProfile("show-news-signals", ("news", "signals", "show"), "news", needs_pipeline=True),
    "score-news": CommandProfile("score-news", ("news", "score"), "news", needs_pipeline=True),
    "optimize-strategy": CommandProfile("optimize-strategy", ("ml", "strategy", "optimize"), "ml", needs_pipeline=True),
    "train-production-ai": CommandProfile("train-production-ai", ("ml", "production", "train"), "ml", needs_pipeline=True),
    "run-continuous": CommandProfile("run-continuous", ("runtime", "continuous", "run"), "runtime"),
    "schedule-jobs": CommandProfile("schedule-jobs", ("runtime", "scheduler", "run"), "runtime"),
    "show-jobs": CommandProfile("show-jobs", ("runtime", "scheduler", "show"), "runtime", needs_database=False, needs_repository=False),
    "start-daemon": CommandProfile("start-daemon", ("runtime", "daemon", "start"), "runtime"),
    "stop-daemon": CommandProfile("stop-daemon", ("runtime", "daemon", "stop"), "runtime", needs_database=False, needs_repository=False),
    "status-daemon": CommandProfile("status-daemon", ("runtime", "daemon", "status"), "runtime", needs_database=False, needs_repository=False),
    "runtime-status": CommandProfile("runtime-status", ("runtime", "status", "show"), "runtime"),
    "doctor": CommandProfile("doctor", ("maintenance", "doctor"), "maintenance", needs_database=False, needs_repository=False),
    "check-env": CommandProfile("check-env", ("maintenance", "check-env"), "maintenance", needs_database=False, needs_repository=False),
    "backup-db": CommandProfile("backup-db", ("maintenance", "db", "backup"), "maintenance"),
    "verify-exchange-credentials": CommandProfile("verify-exchange-credentials", ("maintenance", "exchange", "verify"), "maintenance"),
    "run-live-simulated": CommandProfile("run-live-simulated", ("runtime", "live-simulated", "run"), "runtime"),
    "test-telegram-alert": CommandProfile("test-telegram-alert", ("alerts", "telegram", "test"), "alerts"),
    "send-runtime-alert": CommandProfile("send-runtime-alert", ("alerts", "runtime", "send"), "alerts"),
    "send-portfolio-alert": CommandProfile("send-portfolio-alert", ("alerts", "portfolio", "send"), "alerts"),
    "show-trader-mode": CommandProfile("show-trader-mode", ("runtime", "trader", "mode"), "runtime", needs_database=False, needs_repository=False),
    "reset-live-state": CommandProfile("reset-live-state", ("runtime", "live", "reset-state"), "runtime"),
    "start-live-trading": CommandProfile("start-live-trading", ("runtime", "live", "start"), "runtime"),
    "sync-account": CommandProfile("sync-account", ("runtime", "account", "sync"), "runtime"),
    "emergency-close": CommandProfile("emergency-close", ("runtime", "live", "emergency-close"), "runtime"),
    "control-center": CommandProfile("control-center", ("platform", "control-center"), "platform", needs_pipeline=False),
    "platform-status": CommandProfile("platform-status", ("platform", "status"), "platform", needs_pipeline=False),
    "run-platform-api": CommandProfile("run-platform-api", ("platform", "api", "run"), "platform", needs_pipeline=False),
    "run-telegram-bot": CommandProfile("run-telegram-bot", ("platform", "telegram", "run"), "platform", needs_pipeline=False),
    "run-dashboard": CommandProfile("run-dashboard", ("platform", "dashboard", "run"), "platform", needs_pipeline=False),
    "run-multi-agent": CommandProfile("run-multi-agent", ("agents", "run"), "agents", needs_pipeline=False),
    "run-debate": CommandProfile("run-debate", ("agents", "debate", "run"), "agents", needs_pipeline=False),
    "show-agent-output": CommandProfile("show-agent-output", ("agents", "output", "show"), "agents", needs_pipeline=False),
    "show-consensus-history": CommandProfile("show-consensus-history", ("agents", "consensus", "history"), "agents", needs_pipeline=False),
    "run-supervisor": CommandProfile("run-supervisor", ("agents", "supervisor", "run"), "agents", needs_pipeline=False),
    "show-agent-performance": CommandProfile("show-agent-performance", ("agents", "performance", "show"), "agents", needs_pipeline=False),
    "compare-agent-decisions": CommandProfile("compare-agent-decisions", ("agents", "decisions", "compare"), "agents", needs_pipeline=False),
    "run-live-multi-agent": CommandProfile("run-live-multi-agent", ("agents", "live", "run"), "agents", needs_pipeline=False),
    "schedule-live-multi-agent": CommandProfile("schedule-live-multi-agent", ("agents", "live", "schedule"), "agents", needs_pipeline=False),
    "multi-agent-runtime-status": CommandProfile("multi-agent-runtime-status", ("agents", "runtime", "status"), "agents", needs_pipeline=False),
    "train-multi-agent-models": CommandProfile("train-multi-agent-models", ("agents", "models", "train"), "agents", needs_pipeline=False),
    "backtest-multi-agent": CommandProfile("backtest-multi-agent", ("agents", "backtest", "run"), "agents", needs_pipeline=False),
}
