# Comandos CLI do AlphaScope

Este arquivo reúne os comandos principais da CLI do projeto, organizados por categoria, com exemplos prontos para uso na sua própria máquina.

A CLI agora possui dois formatos válidos:

1. formato canônico hierárquico
2. formato legado compatível

Exemplos equivalentes:

```bash
python -m alphascope.cli market pipeline run --symbols BTCUSDT,ETHUSDT --interval 1h --limit 500
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT --interval 1h --limit 500
```

```bash
python -m alphascope.cli platform api run --host 127.0.0.1 --port 8010
python -m alphascope.cli run-platform-api --host 127.0.0.1 --port 8010
```

Ponto de entrada padrão:

```bash
python -m alphascope.cli <comando> [opções]
```

Se o pacote estiver instalado em modo editável, você também pode usar:

```bash
alphascope <comando> [opções]
```

---

## 1. Comandos de mercado e pipeline

### 1.1 Ingestão de candles

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

Função:
- baixa candles da Binance
- persiste no banco local

### 1.2 Construção de features técnicas

```bash
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Função:
- calcula RSI, médias, volatilidade, momentum e volume relativo

### 1.3 Ranking de ativos

```bash
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Função:
- gera e salva o ranking atual dos ativos

### 1.4 Explicação do ranking

```bash
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

Função:
- mostra score final, score heurístico, score de ML e contribuições

### 1.5 Backtest

```bash
python -m alphascope.cli backtest --symbol BTCUSDT --interval 1h
```

Função:
- executa um backtest simples por ativo

### 1.6 Paper trading manual de um ciclo

```bash
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Função:
- executa um ciclo de trading em modo paper

### 1.7 Pipeline fim a fim

```bash
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

Função:
- ingestão
- features
- ranking
- ciclo de trading

### 1.8 Loop do pipeline por tempo fixo

```bash
python -m alphascope.cli run-loop --symbols BTCUSDT,ETHUSDT,SOLUSDT --duration 60 --interval 120 --timeframe 1h --limit 500
```

Função:
- roda o pipeline repetidamente por N minutos

---

## 2. Universo de mercado e comparação de fontes

### 2.1 Construir universo automático Binance

```bash
python -m alphascope.cli build-universe --top 200 --quote USDT --min-volume 10000000
```

### 2.2 Mostrar universo salvo

```bash
python -m alphascope.cli show-universe --kind auto --limit 30
python -m alphascope.cli show-universe --kind consolidated --limit 30
```

### 2.3 Buscar universo consolidado multi-source

```bash
python -m alphascope.cli fetch-market-universe --primary-source binance --fallback-sources coingecko,coinmarketcap --limit 100
```

### 2.4 Rodar pipeline com universo automático

```bash
python -m alphascope.cli run-auto-universe --top 200 --quote USDT --min-volume 10000000 --interval 1h --limit 500
```

### 2.5 Comparar fontes externas

```bash
python -m alphascope.cli compare-sources --symbol BTC --limit 50
```

### 2.6 Buscar histórico no CryptoCompare

```bash
python -m alphascope.cli fetch-cryptocompare-history --symbol BTC --quote-symbol USD --interval 1h --limit 2000
```

### 2.7 Buscar Fear & Greed

```bash
python -m alphascope.cli fetch-fear-greed --limit 30
```

---

## 3. Dados, datasets e machine learning

### 3.1 Build de dataset de treino supervisionado

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT --interval 1h --horizon-bars 8 --threshold-pct 0.015
```

### 3.2 Build de dataset de mercado

```bash
python -m alphascope.cli build-market-dataset --symbols BTCUSDT,ETHUSDT --interval 1h --chunk-size 100000
```

### 3.3 Importar dataset externo de mercado

```bash
python -m alphascope.cli import-market-dataset --input-path data/externo/market.csv --chunk-size 100000
```

### 3.4 Treinar modelo de mercado

```bash
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
```

### 3.5 Avaliar modelo de mercado

```bash
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT --interval 1h --artifact-path models/market/best_market_model.joblib
```

### 3.6 Predizer com modelo de mercado

```bash
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### 3.7 Otimização com Optuna

```bash
python -m alphascope.cli optimize-strategy --symbol BTCUSDT --interval 1h --trials 20
```

### 3.8 Warm start da IA para produção

```bash
python -m alphascope.cli train-production-ai --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --horizon-bars 8 --threshold-pct 0.015
```

Função:
- constrói dataset supervisionado
- treina o modelo de mercado
- avalia o artefato salvo
- prepara a IA para operar junto com o runtime

---

## 4. Notícias, NLP e sinais de notícia

### 4.1 Ingerir notícias GDELT

```bash
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
```

### 4.2 Construir dataset consolidado de notícias

```bash
python -m alphascope.cli build-news-dataset --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50 --include-hf
```

### 4.3 Importar dataset externo de notícias

```bash
python -m alphascope.cli import-news-dataset --input-path data/externo/news.csv
```

### 4.4 Treinar modelo supervisionado de notícias

```bash
python -m alphascope.cli train-news-model --input-path data/news/news_training_dataset.csv --label-column label
```

### 4.5 Pontuar notícias com NLP

```bash
python -m alphascope.cli score-news --input-path data/news/gdelt_news_latest.csv
```

### 4.6 Mostrar sinais agregados de notícias

```bash
python -m alphascope.cli show-news-signals --symbols BTC,ETH,SOL --limit 20
```

### 4.7 Listar datasets externos locais

```bash
python -m alphascope.cli list-external-datasets --type all
python -m alphascope.cli list-external-datasets --type market
python -m alphascope.cli list-external-datasets --type news
```

---

## 5. Runtime, automação e operação contínua

### 5.1 Rodar pipeline contínuo

```bash
python -m alphascope.cli run-continuous --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --news-seconds 3600 --timeframe 1h --limit 500
```

### 5.2 Agendar jobs recorrentes

```bash
python -m alphascope.cli schedule-jobs --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --news-seconds 900 --duration-seconds 60 --timeframe 1h --limit 500
```

### 5.3 Ver jobs salvos

```bash
python -m alphascope.cli show-jobs
```

### 5.4 Iniciar daemon

```bash
python -m alphascope.cli start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --news-seconds 3600 --heartbeat-seconds 60 --timeframe 1h --limit 500
```

### 5.5 Parar daemon

```bash
python -m alphascope.cli stop-daemon
```

### 5.6 Ver status do daemon

```bash
python -m alphascope.cli status-daemon
```

### 5.7 Ver status consolidado de runtime

```bash
python -m alphascope.cli runtime-status
```

### 5.8 Rodar modo live simulado

```bash
python -m alphascope.cli run-live-simulated --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500 --mode live_simulated
```

### 5.9 Rodar ciclo multiagente

```bash
python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
```

Função:
- monta contexto multiagente
- executa market, news, risk, memory e supervisor
- gera plano de execução
- persiste auditoria e histórico

### 5.10 Rodar debate multiagente

```bash
python -m alphascope.cli run-debate --symbol BTCUSDT --interval 1h
```

Função:
- mostra a trilha de debate interna entre os agentes

### 5.11 Mostrar outputs dos agentes

```bash
python -m alphascope.cli show-agent-output --symbol BTCUSDT --limit 20
```

Função:
- exibe os outputs persistidos de market, news, risk e memory

### 5.12 Mostrar histórico de consenso

```bash
python -m alphascope.cli show-consensus-history --limit 20
python -m alphascope.cli show-consensus-history --symbol BTCUSDT --limit 20
```

Função:
- exibe decisões históricas do supervisor multiagente

### 5.13 Rodar apenas o supervisor multiagente

```bash
python -m alphascope.cli run-supervisor --symbol BTCUSDT --interval 1h
```

Função:
- calcula o consenso final sem foco na execução live

### 5.14 Mostrar performance agregada dos agentes

```bash
python -m alphascope.cli show-agent-performance --limit 20
```

Função:
- mostra estatísticas agregadas de atividade e confiança dos agentes

### 5.15 Comparar decisões dos agentes

```bash
python -m alphascope.cli compare-agent-decisions --symbol BTCUSDT --limit 20
```

Função:
- compara alinhamentos e divergências entre os agentes

### 5.16 Rodar fluxo live multiagente

```bash
python -m alphascope.cli run-live-multi-agent --symbol BTCUSDT --interval 1h
```

Função:
- usa o supervisor multiagente junto do trader selecionado
- respeita regras de risco, símbolo permitido e confiança mínima

### 5.17 Agendar runtime live multiagente

```bash
python -m alphascope.cli schedule-live-multi-agent --symbols BTCUSDT,ETHUSDT --interval 1h --cycle-seconds 300 --duration-seconds 3600
```

Função:
- agenda ciclos contínuos do runtime multiagente
- grava heartbeat e status do scheduler multiagente

### 5.18 Ver status do runtime multiagente

```bash
python -m alphascope.cli multi-agent-runtime-status --json
```

Função:
- exibe status do runtime, cache, heartbeat e scheduler do multiagente

### 5.19 Treinar modelos locais do multiagente

```bash
python -m alphascope.cli train-multi-agent-models --symbols BTCUSDT,ETHUSDT --interval 1h
```

Função:
- tenta treinar modelos locais do multiagente com as bibliotecas disponíveis
- integra com o learning/retraining engine

### 5.20 Backtest multiagente

```bash
python -m alphascope.cli backtest-multi-agent --symbol BTCUSDT --interval 1h --limit 300
```

Função:
- executa replay histórico do consenso multiagente
- gera trades, curva de equity e trilha de consenso

---

## 6. Comandos de segurança, diagnóstico e manutenção

### 6.1 Doctor do ambiente

```bash
python -m alphascope.cli doctor
python -m alphascope.cli doctor --json
```

### 6.2 Alias de checagem do ambiente

```bash
python -m alphascope.cli check-env
python -m alphascope.cli check-env --json
```

### 6.3 Backup do banco oficial

```bash
python -m alphascope.cli backup-db
python -m alphascope.cli backup-db --output-dir artifacts/backups
```

### 6.4 Verificar credenciais da exchange

```bash
python -m alphascope.cli verify-exchange-credentials --mode paper
python -m alphascope.cli verify-exchange-credentials --mode testnet
python -m alphascope.cli verify-exchange-credentials --mode live
```

Observação:
- em `paper`, a checagem é segura e não envia ordens
- em `testnet` e `live`, o comando valida credenciais e sincronização de relógio, sem abrir trade

---

## 7. Alertas e utilitários operacionais

### 7.1 Testar alerta do Telegram

```bash
python -m alphascope.cli test-telegram-alert
```

### 7.2 Enviar alerta de runtime

```bash
python -m alphascope.cli send-runtime-alert --interval 1h
```

### 7.3 Enviar alerta de snapshot do portfólio

```bash
python -m alphascope.cli send-portfolio-alert --label "Snapshot manual"
```

### 7.4 Mostrar modo atual do trader

```bash
python -m alphascope.cli show-trader-mode
```

### 7.5 Resetar estado persistido de live trading

```bash
python -m alphascope.cli reset-live-state
```

---

## 8. Live trading e conta

> Atenção: esses comandos só devem ser usados se você souber exatamente o que está fazendo.
> O projeto agora está configurado para PAPER por padrão.

### 8.1 Iniciar processamento de sinais no trader live/testnet

```bash
python -m alphascope.cli start-live-trading --interval 1h --limit 20
python -m alphascope.cli start-live-trading --interval 1h --limit 20 --symbol BTCUSDT
```

### 8.2 Sincronizar conta da Binance

```bash
python -m alphascope.cli sync-account
```

### 8.3 Emergency close

```bash
python -m alphascope.cli emergency-close --interval 1h
python -m alphascope.cli emergency-close --interval 1h --symbol BTCUSDT
```

---

## 9. API, dashboard e painel

### 9.1 Subir API oficial

```bash
python -m alphascope.cli run-platform-api --host 0.0.0.0 --port 8010
```

### 9.2 Subir dashboard oficial

```bash
python -m alphascope.cli run-dashboard --host 0.0.0.0 --port 8501
```

### 9.3 Ver status da plataforma

```bash
python -m alphascope.cli platform-status
```

### 9.4 Abrir control center

```bash
python -m alphascope.cli control-center
```

### 9.5 Rodar bot de Telegram da plataforma

```bash
python -m alphascope.cli run-telegram-bot
python -m alphascope.cli run-telegram-bot --once
```

---

## 10. Inspeção de dados já salvos

### 10.1 Mostrar candles

```bash
python -m alphascope.cli show-data --type candles --symbol BTCUSDT --interval 1h --limit 20
```

### 10.2 Mostrar features

```bash
python -m alphascope.cli show-data --type features --symbol BTCUSDT --interval 1h --limit 20
```

### 10.3 Mostrar ranking

```bash
python -m alphascope.cli show-data --type ranking --interval 1h --limit 20
```

### 10.4 Mostrar snapshot

```bash
python -m alphascope.cli show-data --type snapshot --limit 20
```

### 10.5 Mostrar posições abertas

```bash
python -m alphascope.cli show-data --type open-positions --limit 20
```

### 10.6 Mostrar conta

```bash
python -m alphascope.cli show-data --type account --limit 20
```

### 10.7 Mostrar trades live

```bash
python -m alphascope.cli show-data --type live-trades --limit 20
```

---

## 11. Sequências prontas de uso

### 11.1 Fluxo seguro local (paper)

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli runtime-status
```

### 11.2 Fluxo de treino de IA de mercado

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### 11.3 Fluxo de operação contínua

```bash
python -m alphascope.cli doctor
python -m alphascope.cli backup-db
python -m alphascope.cli start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500
```

### 11.5 Fluxo multiagente local / testnet

```bash
python -m alphascope.cli multi-agent-runtime-status --json
python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
python -m alphascope.cli run-debate --symbol BTCUSDT --interval 1h
python -m alphascope.cli show-consensus-history --symbol BTCUSDT --limit 20
python -m alphascope.cli train-multi-agent-models --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli backtest-multi-agent --symbol BTCUSDT --interval 1h --limit 300
```

### 11.6 Soak test multiagente em testnet

```bash
python -m alphascope.cli verify-exchange-credentials --mode testnet
python -m alphascope.cli schedule-live-multi-agent --symbols BTCUSDT,ETHUSDT --interval 1h --cycle-seconds 300 --duration-seconds 3600
python -m alphascope.cli multi-agent-runtime-status --json
```

### 11.7 Checklist da manhã para operação bruta live

```bash
python -m alphascope.cli doctor --json
python -m alphascope.cli verify-exchange-credentials --mode live
python -m alphascope.cli sync-account
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
python -m alphascope.cli test-telegram-alert
python -m alphascope.cli runtime-status
```

Comandos finais recomendados:

```bash
.\scripts\iniciar_alphascope_manha.ps1
.\scripts\iniciar_alphascope_manha.ps1 -StartDaemon
.\scripts\iniciar_alphascope_manha.ps1 -ProductionReal
.\scripts\iniciar_alphascope_manha.ps1 -ProductionReal -StartDaemon
```

Comando final explícito para produção real:

```bash
.\scripts\iniciar_alphascope_manha.ps1 -ProductionReal
```

Comando final explícito para produção real com daemon contínuo:

```bash
.\scripts\iniciar_alphascope_manha.ps1 -ProductionReal -StartDaemon
```

Veja também: `docs/guides/CHECKLIST_MANHA_OPERACAO_BRUTA.md`.

---

## 12. Comandos mais sensíveis

Use com cuidado especial:
- `start-live-trading`
- `run-live-multi-agent`
- `schedule-live-multi-agent`
- `sync-account`
- `emergency-close`
- `verify-exchange-credentials --mode live`
- `run-telegram-bot`
- `run-platform-api`
- `run-dashboard`

---

## 13. Recomendação prática para sua máquina

Como você disse que vai executar manualmente na sua própria máquina, a ordem mais segura para uso diário é:

1. `doctor`
2. `backup-db`
3. `verify-exchange-credentials --mode paper` ou `--mode testnet`
4. `run-pipeline` ou `start-daemon`
5. `runtime-status`
6. `show-trader-mode`

Se quiser operar com máxima segurança, mantenha o projeto em `paper` até validar tudo que você quiser no seu fluxo.
