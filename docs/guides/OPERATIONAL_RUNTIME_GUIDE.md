# AlphaScope Operational Runtime Guide

## 1. Visao geral

O AlphaScope agora possui uma camada operacional continua, preparada para:

- execucao repetitiva do pipeline
- agendamento de jobs
- operacao em ciclos
- execucao persistente em modo daemon
- simulacao live sem ordens reais
- monitoramento de runtime

Essa camada permite que o projeto rode por longos periodos de forma mais previsivel, observavel e segura.

## 2. Componentes principais

### Runner

Responsavel por repetir o `run-pipeline` durante uma janela de tempo fixa.

Arquivos:

- [pipeline_runner.py](D:/AlphaScope/src/alphascope/runner/pipeline_runner.py)
- [__init__.py](D:/AlphaScope/src/alphascope/runner/__init__.py)

### Scheduler

Responsavel por registrar e executar jobs recorrentes com retry basico e persistencia de status.

Arquivos:

- [scheduler.py](D:/AlphaScope/src/alphascope/automation/scheduler.py)
- [job_registry.py](D:/AlphaScope/src/alphascope/automation/job_registry.py)

### Continuous pipeline

Responsavel por rodar ciclos operacionais em estilo quant trading.

Arquivos:

- [continuous_pipeline.py](D:/AlphaScope/src/alphascope/automation/continuous_pipeline.py)

### Daemon

Responsavel por manter o AlphaScope ativo como servico local foreground, com heartbeat, pid file e shutdown gracioso.

Arquivos:

- [daemon_runner.py](D:/AlphaScope/src/alphascope/automation/daemon_runner.py)
- [heartbeat.py](D:/AlphaScope/src/alphascope/automation/heartbeat.py)

### Live simulated

Responsavel por operar em modo quase live, usando ranking e precos recentes para simular sinais, execucoes e atualizacao de portfolio.

Arquivos:

- [live_simulator.py](D:/AlphaScope/src/alphascope/simulation/live_simulator.py)
- [event_loop.py](D:/AlphaScope/src/alphascope/simulation/event_loop.py)
- [signal_dispatcher.py](D:/AlphaScope/src/alphascope/simulation/signal_dispatcher.py)
- [execution_simulator.py](D:/AlphaScope/src/alphascope/simulation/execution_simulator.py)
- [portfolio_sync.py](D:/AlphaScope/src/alphascope/simulation/portfolio_sync.py)

### Monitoring

Responsavel por consolidar estado de runtime, metricas e alertas de recuperacao.

Arquivos:

- [runtime_status.py](D:/AlphaScope/src/alphascope/monitoring/runtime_status.py)
- [runtime_metrics.py](D:/AlphaScope/src/alphascope/monitoring/runtime_metrics.py)
- [failure_recovery.py](D:/AlphaScope/src/alphascope/monitoring/failure_recovery.py)

## 3. Fluxo operacional

O fluxo continuo tipico do AlphaScope e:

1. atualizar mercado
2. atualizar noticias, quando habilitado
3. gerar features
4. recalcular ranking
5. atualizar paper trading ou live simulated
6. salvar snapshots e estado
7. registrar heartbeat e metricas

Esse fluxo pode ser executado em quatro estilos:

- execucao unica
- loop por tempo fixo
- ciclos continuos
- daemon local

## 4. Comandos principais

### Pipeline unico

```bash
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

### Loop por tempo fixo

```bash
python -m alphascope.cli run-loop --symbols BTCUSDT,ETHUSDT,SOLUSDT --duration 60 --interval 120 --timeframe 1h --limit 500
```

### Pipeline continuo

```bash
python -m alphascope.cli run-continuous --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500
```

### Scheduler

```bash
python -m alphascope.cli schedule-jobs --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --news-seconds 900 --duration-seconds 600 --timeframe 1h --limit 500
python -m alphascope.cli show-jobs
```

### Daemon

```bash
python -m alphascope.cli start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500
python -m alphascope.cli status-daemon
python -m alphascope.cli stop-daemon
```

### Runtime status

```bash
python -m alphascope.cli runtime-status
```

### Live simulated

```bash
python -m alphascope.cli run-live-simulated --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500
```

Modo seco:

```bash
python -m alphascope.cli run-live-simulated --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500 --mode dry_run
```

## 5. Estrutura de runtime

Os arquivos de runtime ficam em `data/runtime/`.

Arquivos principais:

- `alphascope.pid`
- `daemon_status.json`
- `heartbeat.json`
- `scheduler_status.json`
- `continuous_pipeline_status.json`
- `live_simulated_status.json`

Esses arquivos sao lidos pelos comandos:

- `status-daemon`
- `show-jobs`
- `runtime-status`

## 6. Configuracao de ambiente

Exemplo de configuracao para operacao continua:

```env
ENABLE_SCHEDULER=true
ENABLE_CONTINUOUS_PIPELINE=true
ENABLE_LIVE_SIMULATED=true

CYCLE_INTERVAL_SECONDS=300
NEWS_REFRESH_INTERVAL_SECONDS=900
HEARTBEAT_INTERVAL_SECONDS=60

DAEMON_PID_FILE=data/runtime/alphascope.pid
DAEMON_STATUS_FILE=data/runtime/daemon_status.json
HEARTBEAT_FILE=data/runtime/heartbeat.json

ENABLE_DAILY_RETRAIN=false
DAILY_RETRAIN_HOUR=2

ENABLE_DAILY_OPTIMIZATION=false
DAILY_OPTIMIZATION_HOUR=3

MAX_CONSECUTIVE_ERRORS=10
RETRY_BACKOFF_SECONDS=5
```

## 7. Como o live simulated funciona

O encadeamento interno e:

1. ranking recente e carregado
2. o `signal_dispatcher` gera sinais
3. o `execution_simulator` aplica execucao simulada
4. o `portfolio_sync` persiste trades e snapshots
5. o `live_simulator` registra o estado do ciclo

Regras importantes:

- nenhuma ordem real e enviada para exchange
- fee e limite de posicoes sao considerados
- `dry_run` nao persiste trades e snapshots
- `live_simulated` persiste o estado continuamente

## 8. Monitoramento

O comando `runtime-status` consolida:

- status do daemon
- heartbeat
- jobs executados
- falhas recentes
- ultimo ranking
- ultimo snapshot
- equity e cash
- quantidade de posicoes abertas
- status do SQLite
- status configurado das APIs

O projeto tambem possui:

- metricas recentes de runtime
- alertas basicos de `failure_recovery`

## 9. Troubleshooting

### `runtime-status` vazio ou incompleto

Verifique:

- se existe execucao previa do daemon ou pipeline continuo
- se `data/runtime/` esta correto
- se os arquivos de status nao foram removidos

### `stop-daemon` nao para nada

Verifique:

- se `alphascope.pid` existe
- se o pid ainda corresponde a um processo ativo
- se o processo ja nao foi encerrado antes

### Daemon encerra cedo

Verifique:

- se scheduler e continuous pipeline nao estao ambos desabilitados
- se o banco SQLite esta acessivel
- se os simbolos informados sao validos

### Live simulated nao executa trades

Verifique:

- se existe ranking recente
- se o modo nao esta em `dry_run`
- se o limite maximo de posicoes ja nao foi atingido
- se os thresholds de compra e venda permitem gerar sinais

## 10. Validacao

Validacao ampla executada no projeto:

```bash
pytest tests -q --basetemp data/runtime/pytest_basetemp_full
```

Resultado:

- suite completa aprovada

## 11. Organizacao da CLI

A CLI foi modularizada por dominio:

- [cli.py](D:/AlphaScope/src/alphascope/cli.py)
- [cli_market.py](D:/AlphaScope/src/alphascope/cli_market.py)
- [cli_runtime.py](D:/AlphaScope/src/alphascope/cli_runtime.py)
- [cli_data.py](D:/AlphaScope/src/alphascope/cli_data.py)
- [cli_registry.py](D:/AlphaScope/src/alphascope/cli_registry.py)

Isso reduz acoplamento no entrypoint principal e facilita evolucao futura.

## 12. Resumo

O AlphaScope agora suporta:

- operacao em loop
- agendamento recorrente
- pipeline continuo
- daemon local
- simulacao live sem risco de ordem real
- monitoramento operacional
- observabilidade basica de runtime

Essa base permite evoluir o projeto para operacao continua de pesquisa, simulacao e paper trading com mais robustez.
