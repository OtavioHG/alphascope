# Multi-Agent Go-Live Checklist

Pré-requisitos de ambiente
- [ ] venv ativo e dependências instaladas
- [ ] DATABASE_URL configurado para PostgreSQL de produção
- [ ] REDIS_URL configurado e validado
- [ ] TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID configurados
- [ ] chaves Binance corretas para paper/testnet/live
- [ ] LIVE_ALLOWED_SYMBOLS revisado
- [ ] backups e retenção de logs configurados

Schema e storage
- [ ] aplicar migrações Alembic até 0002_multi_agent_schema
- [ ] validar presença das tabelas agent_decisions, agent_debates, trade_consensus, trade_audit, runtime_events, model_outputs
- [ ] validar tabelas de memória strategy_memory, risk_memory, news_memory, market_context_memory
- [ ] confirmar escrita e leitura no PostgreSQL

Validações operacionais
- [ ] rodar python -m alphascope.cli multi-agent-runtime-status --json
- [ ] rodar python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
- [ ] verificar persistência em agent_decisions/trade_consensus/trade_audit/audit_events
- [ ] verificar export de datasets em data/training
- [ ] verificar arquivos data/runtime/multi_agent_*.json

Execução exchange / live safety
- [ ] validar testnet antes de live
- [ ] executar verify-exchange-credentials
- [ ] confirmar min_confidence_score apropriado
- [ ] confirmar max_open_trades e limites de risco
- [ ] testar bloqueio por symbol_not_allowed
- [ ] testar bloqueio por below_min_confidence
- [ ] testar recuperação após erro de exchange
- [ ] validar sync_account antes e depois de ordens multiagente

Observabilidade
- [ ] subir API com /healthz, /healthz/multi-agent e /metrics
- [ ] validar métricas multi_agent_* no endpoint /metrics
- [ ] configurar Prometheus scrape
- [ ] configurar dashboard Grafana
- [ ] configurar alerta heartbeat_down
- [ ] configurar alerta scheduler_missing

Telegram
- [ ] validar /ma_status
- [ ] validar /ma_last
- [ ] validar /ma_run BTCUSDT 1h
- [ ] validar entrega do alerta multi_agent_decision

Treino local
- [ ] rodar train-multi-agent-models
- [ ] confirmar trainer selecionado ou fallback limpo
- [ ] validar artifacts models/local_*_model.pkl
- [ ] revisar metadados JSON dos modelos locais

Backtest e regressão
- [ ] rodar backtest-multi-agent para BTCUSDT
- [ ] comparar score/consenso com trades históricos
- [ ] rodar pytest completo no ambiente do projeto
- [ ] validar novos testes multiagente, Telegram, produção e runtime

Critério de entrada em produção
- [ ] healthcheck geral OK
- [ ] healthcheck multiagente OK
- [ ] métricas multi_agent_* presentes
- [ ] Telegram operacional OK
- [ ] testnet OK por janela mínima de observação
- [ ] auditoria e persistência OK
- [ ] rollback operacional definido
