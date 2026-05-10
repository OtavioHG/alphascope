# Multi-Agent Operational Runbook

Objetivo
- executar o AlphaScope multiagente em testnet/staging de forma controlada
- validar saúde, observabilidade, Telegram e decisão operacional antes de capital real

Pré-requisitos
- PowerShell no diretório do projeto D:\AlphaScope
- venv configurado em `venv`
- banco e Redis configurados
- credenciais Telegram configuradas
- Binance testnet ou live configurada conforme ambiente

Variáveis críticas a revisar antes de qualquer execução
- `DATABASE_URL`
- `REDIS_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LIVE_TRADING_MODE`
- `LIVE_TRADING_ENABLED`
- `LIVE_ALLOWED_SYMBOLS`
- `MIN_CONFIDENCE_SCORE`
- `MAX_OPEN_TRADES`
- `STOP_LOSS_PCT`
- `TAKE_PROFIT_PCT`
- `TRAILING_STOP_PCT`

## 1. Sequência de boot para testnet

### 1.1 Ativar ambiente
```powershell
Set-Location D:\AlphaScope
.\venv\Scripts\Activate.ps1
```

### 1.2 Validar ambiente Python
```powershell
python --version
python -m pip --version
python -m pytest --version
```

### 1.3 Rodar testes críticos antes do runtime
```powershell
python -m pytest -q tests/test_multi_agent_cli.py tests/test_multi_agent_service.py tests/test_multi_agent_runtime.py tests/test_multi_agent_production.py tests/test_multi_agent_telegram.py tests/test_multi_agent_api.py
python -m pytest -q tests/test_runtime_monitoring.py tests/test_runtime_commands.py tests/integration/test_cli_runtime_commands.py
```

### 1.4 Validar exchange/credenciais
Para paper/testnet:
```powershell
python -m alphascope.cli verify-exchange-credentials --mode testnet
```

### 1.5 Validar healthcheck e status antes do primeiro ciclo
```powershell
python -m alphascope.cli multi-agent-runtime-status --json
python -m alphascope.cli runtime-status
```

## 2. Sequência de validação funcional em testnet

### 2.1 Rodar um ciclo único multiagente
```powershell
python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
python -m alphascope.cli run-supervisor --symbol BTCUSDT --interval 1h
python -m alphascope.cli run-debate --symbol BTCUSDT --interval 1h
```

### 2.2 Inspecionar persistência gerada
```powershell
python -m alphascope.cli show-agent-output --symbol BTCUSDT --limit 20
python -m alphascope.cli show-consensus-history --symbol BTCUSDT --limit 20
python -m alphascope.cli show-agent-performance --limit 20
python -m alphascope.cli compare-agent-decisions --symbol BTCUSDT --limit 20
```

### 2.3 Validar treino local e backtest
```powershell
python -m alphascope.cli train-multi-agent-models --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli backtest-multi-agent --symbol BTCUSDT --interval 1h --limit 300
```

### 2.4 Validar Telegram
No Telegram operacional, executar:
```text
/ma_status
/ma_last
/ma_run BTCUSDT 1h
```

Esperado:
- resposta sem erro
- última decisão coerente com `show-consensus-history`
- `ma_status` refletindo heartbeat/cache/scheduler

## 3. Subida da API e monitoramento

### 3.1 Subir API
```powershell
python -m alphascope.cli run-platform-api --host 0.0.0.0 --port 8010
```

### 3.2 Validar endpoints localmente
Em outro terminal PowerShell:
```powershell
Invoke-WebRequest http://127.0.0.1:8010/healthz | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:8010/healthz/multi-agent | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:8010/metrics | Select-Object -ExpandProperty Content
```

Esperado:
- `/healthz` com status ok ou degradado explicável
- `/healthz/multi-agent` com `multi_agent_tables=true`
- após um ciclo real do runtime, `/healthz/multi-agent` com `multi_agent.healthy=true`
- `/metrics` contendo séries `multi_agent_*`

### 3.3 Subir dashboard interno
```powershell
python -m alphascope.cli run-dashboard --host 0.0.0.0 --port 8501
```

Validar página:
- `Multi-Agent Monitor`

## 4. Soak test em testnet com scheduler

### 4.1 Iniciar scheduler multiagente
```powershell
python -m alphascope.cli schedule-live-multi-agent --symbols BTCUSDT,ETHUSDT --interval 1h --cycle-seconds 300 --duration-seconds 3600
```

### 4.2 Durante o soak test, acompanhar
```powershell
python -m alphascope.cli multi-agent-runtime-status --json
python -m alphascope.cli runtime-status
```

Endpoints úteis:
- `http://127.0.0.1:8010/healthz/multi-agent`
- `http://127.0.0.1:8010/metrics`

Arquivos úteis:
- `data/runtime/multi_agent_runtime_status.json`
- `data/runtime/multi_agent_scheduler_status.json`
- `data/runtime/multi_agent_heartbeat.json`
- `logs/metrics.jsonl`
- `logs/alphascope.log`

### 4.3 Critérios mínimos para concluir soak test com sucesso
- sem exceções críticas repetidas no log
- heartbeat presente durante toda a janela
- scheduler multiagente com jobs válidos
- Telegram respondendo a `/ma_status`
- `/metrics` expondo séries multi_agent_*
- decisões persistidas em histórico/auditoria

## 5. Sequência de preparação para capital real

### 5.1 Trocar de paper/testnet para live controlado
Somente após soak test aprovado.

Validar:
```powershell
python -m alphascope.cli show-trader-mode
python -m alphascope.cli verify-exchange-credentials --mode live
```

### 5.2 Conferir escopo de símbolos autorizados
```powershell
python -m alphascope.cli show-agent-performance --limit 20
```

Revisar em `.env`:
- `LIVE_ALLOWED_SYMBOLS`
- `MAX_OPEN_TRADES`
- `MIN_CONFIDENCE_SCORE`

### 5.3 Primeira execução controlada
```powershell
python -m alphascope.cli run-live-multi-agent --symbol BTCUSDT --interval 1h
```

## 6. Verificações obrigatórias após cada execução live
- decisão e score no terminal
- `show-consensus-history`
- `show-agent-output`
- `runtime-status`
- `/healthz/multi-agent`
- Telegram de decisão
- logs em `logs/alphascope.log`

## 7. Comandos de contenção/rollback operacional
Parar/mitigar rapidamente:
```powershell
python -m alphascope.cli emergency-close --symbol BTCUSDT --interval 1h
python -m alphascope.cli sync-account
python -m alphascope.cli reset-live-state
python -m alphascope.cli runtime-status
```

Se houver daemon/scheduler do runtime rodando em outra frente:
```powershell
python -m alphascope.cli stop-daemon
python -m alphascope.cli status-daemon
```

## 8. Sinais de bloqueio imediato de go-live
Não prosseguir para capital real se houver qualquer um abaixo:
- `/healthz/multi-agent` sem `healthy=true` após ciclos válidos
- métricas `multi_agent_*` ausentes em `/metrics`
- falha recorrente de Telegram em `/ma_status` ou `/ma_run`
- falha de credenciais Binance
- decisões persistidas sem auditoria correspondente
- exceções repetidas de exchange no fluxo live
- divergência entre estado local e account sync
