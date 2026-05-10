# AlphaScope Multi-Agent Architecture

Objetivo
- adicionar uma camada multiagente institucional, auditável e resiliente ao AlphaScope existente
- preservar compatibilidade com CLI, PostgreSQL/SQLite, Redis, Telegram, paper trading e runtime atual

Módulos criados
- src/alphascope/agents/market_agent.py
- src/alphascope/agents/news_agent.py
- src/alphascope/agents/risk_agent.py
- src/alphascope/agents/execution_agent.py
- src/alphascope/agents/supervisor_agent.py
- src/alphascope/agents/debate_engine.py
- src/alphascope/agents/consensus_engine.py
- src/alphascope/agents/scoring_engine.py
- src/alphascope/agents/memory_engine.py
- src/alphascope/agents/audit_engine.py
- src/alphascope/agents/repository.py
- src/alphascope/agents/orchestrator.py
- src/alphascope/agents/models.py
- src/alphascope/agents/cache.py
- src/alphascope/agents/runtime.py
- src/alphascope/agents/learning_engine.py
- src/alphascope/agents/backtest_engine.py
- src/alphascope/cli_multi_agent.py

Fluxo operacional
1. MultiAgentRepository monta contexto a partir do storage existente
2. Market agent avalia técnico e regime
3. News agent avalia sentimento/news proxies e fear & greed
4. Risk agent avalia exposição, drawdown, volatilidade e sizing
5. Memory engine consulta histórico local e gera fallback/offline score
6. Debate engine cria trilha de debate entre agentes
7. Supervisor aplica pesos dinâmicos e produz consenso final
8. Execution agent gera plano de ordem ou bloqueio
9. Audit engine grava trilha completa
10. Memory engine exporta datasets de treino em data/training/
11. Telegram envia alerta quando trade é aprovado

Regras de consenso implementadas
- nemotron: 40%
- gpt_oss: 30%
- minimax: 20%
- trinity/local memory: 10%
- pesos são recalibrados dinamicamente por confiança histórica dos agentes

Persistência criada
- agent_decisions
- agent_debates
- trade_consensus
- trade_audit
- runtime_events
- model_outputs
- agent_memory
- historical_patterns
- winning_trade_patterns
- losing_trade_patterns
- market_context_memory
- news_memory
- risk_memory
- strategy_memory

Comandos CLI novos
- python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
- python -m alphascope.cli run-debate --symbol BTCUSDT --interval 1h
- python -m alphascope.cli show-agent-output --symbol BTCUSDT --limit 20
- python -m alphascope.cli show-consensus-history --limit 20
- python -m alphascope.cli run-supervisor --symbol BTCUSDT --interval 1h
- python -m alphascope.cli show-agent-performance --limit 20
- python -m alphascope.cli compare-agent-decisions --symbol BTCUSDT --limit 20
- python -m alphascope.cli run-live-multi-agent --symbol BTCUSDT --interval 1h
- python -m alphascope.cli schedule-live-multi-agent --symbols BTCUSDT,ETHUSDT --interval 1h --cycle-seconds 300
- python -m alphascope.cli multi-agent-runtime-status --json
- python -m alphascope.cli train-multi-agent-models --symbols BTCUSDT,ETHUSDT --interval 1h
- python -m alphascope.cli backtest-multi-agent --symbol BTCUSDT --interval 1h --limit 300

Notas de produção
- a implementação já persiste auditoria completa e datasets de treino
- quando pyarrow não estiver disponível, exports de treino caem para CSV automaticamente
- a execução agora pluga diretamente no trader selecionado: PaperTrader ou LiveTrader
- o runtime multiagente usa cache Redis quando disponível e fallback in-memory quando não estiver acessível
- há heartbeat e scheduler dedicados em data/runtime/multi_agent_*.json
- o aprendizado local tenta XGBoost, LightGBM, CatBoost ou sklearn automaticamente, com fallback quando dependências não estiverem instaladas
- init_database importa os models multiagente, então a criação de schema funciona tanto em SQLite quanto em PostgreSQL
- Alembic recebeu a migração 0002_multi_agent_schema.py

Próximos incrementos recomendados
- plugar execution_agent no live_trader/order_manager para ordem real
- consumir Redis para cache de contexto e heartbeats multiagente
- criar scheduler dedicado para run-live-multi-agent e recalibração periódica
- treinar modelos locais com sklearn/XGBoost/LightGBM quando as dependências estiverem disponíveis

Camada de endurecimento de produção adicionada
- integração Telegram para status, última decisão e execução manual multiagente por comandos /ma_status /ma_last /ma_run
- métricas Prometheus específicas do multiagente emitidas em logs/metrics.jsonl e expostas em /metrics
- healthcheck HTTP dedicado em /healthz/multi-agent
- healthcheck agora valida presença das tabelas centrais multiagente e arquivos de runtime/heartbeat
- auditoria operacional reforçada com evento audit_events.action=multi_agent_decision
- testes adicionais para métricas, runtime/healthcheck e Telegram multiagente
