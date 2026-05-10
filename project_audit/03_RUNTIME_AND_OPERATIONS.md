# 03_RUNTIME_AND_OPERATIONS - AlphaScope Audit

## 1. Como Iniciar o Projeto
O sistema é operado via CLI Python (módulo `alphascope.cli`).

### Comandos de Início Rápido:
1.  **Configurar Ambiente:**
    ```bash
    pip install -r requirements-full.txt
    pip install -e .
    cp .env.example .env  # Configurar chaves API
    ```
2.  **Pipeline Único:**
    ```bash
    python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT --interval 1h
    ```
3.  **Paper Trading Local:**
    ```bash
    python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT --interval 1h
    ```

## 2. CLI e Subcomandos
O AlphaScope organiza seus comandos em três grupos principais (Mapeados em `cli_registry.py`):
- **Mercado e Pipeline:** Ingestão de candles, feature building, ranking e backtest.
- **Runtime Operacional:** Automação, Daemon, Scheduler, Status e Live Simulation.
- **Dados e IA:** Datasets, ML, NLP, Notícias e Otimização.

### Comandos Críticos:
- `ingest-market`: Inicia a carga de OHLCV da Binance.
- `start-daemon`: Roda o sistema em background operacional contínuo.
- `runtime-status`: Mostra um painel textual com o estado de tudo (Scheduler, Heartbeat, Daemon, Portfolio).
- `run-live-simulated`: Inicia o loop operacional completo em tempo real simulado.

## 3. Modos de Operação
- **Pipeline Único (`run-pipeline`):** Execução única fim-a-fim.
- **Loop (`run-loop`):** Executa o pipeline repetidamente por uma duração fixa.
- **Contínuo (`run-continuous`):** Execução cíclica baseada em tempo de ciclo (`cycle-seconds`).
- **Daemon Operacional (`start-daemon`):** Modo de serviço local que coordena o Scheduler e o Pipeline Contínuo com persistência de PID e status.

## 4. Monitoramento e Observabilidade
- **Heartbeat:** Implementado em `automation/heartbeat.py`. Registra um sinal de vida a cada N segundos em `data/runtime/heartbeat.json`.
- **Runtime Status:** Agregador de estado em `monitoring/runtime_status.py`. Consolida:
    - Status do Daemon (Active/Inactive).
    - Últimos Jobs (Success/Failure).
    - Métricas de Sistema (CPU/Memória).
    - Alertas Recentes.
- **Alertas Telegram:** Sistema de notificação configurável no `.env` para avisos de lucro, perda ou falhas de sistema.

## 5. Status Operacional Real (Auditoria)
- O sistema grava arquivos de estado em `data/runtime/`:
    - `alphascope.pid` (PID do Daemon ativo).
    - `daemon_status.json` (Metadados do processo).
    - `scheduler_status.json` (Agenda de tarefas).
    - `continuous_pipeline_status.json` (Estado do ciclo atual).
- **Recuperação de Falhas:** O módulo `monitoring/failure_recovery.py` detecta PIDs órfãos e heartbeats expirados, reportando degradado no `runtime-status`.
