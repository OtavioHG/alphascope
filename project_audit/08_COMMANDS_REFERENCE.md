# 08_COMMANDS_REFERENCE - AlphaScope Audit

## 1. Comandos Reais da CLI
O ponto de entrada é `python -m alphascope.cli` (ou o atalho `alphascope` se instalado).

### Grupo 1: Pipeline de Mercado
| Comando | Parâmetros Principais | Função |
| :--- | :--- | :--- |
| `ingest-market` | `--symbols`, `--interval`, `--limit` | Carga de candles (Binance). |
| `build-features` | `--symbols`, `--interval` | Cálculo de indicadores técnicos. |
| `rank-assets` | `--symbols`, `--interval`, `--mode` | Geração do ranking (heuristic, ml, hybrid). |
| `explain-ranking` | `--symbols`, `--interval` | Explicação dos scores gerados. |
| `backtest` | `--symbol`, `--interval` | Execução de backtest simples. |
| `run-pipeline` | `--symbols`, `--interval`, `--limit` | Fluxo único fim-a-fim. |

### Grupo 2: Operação e Runtime
| Comando | Parâmetros Principais | Função |
| :--- | :--- | :--- |
| `start-daemon` | `--symbols`, `--cycle-seconds` | Inicia o daemon local (foreground). |
| `stop-daemon` | (nenhum) | Solicita o desligamento seguro do daemon. |
| `runtime-status` | (nenhum) | Painel de monitoramento consolidado. |
| `run-continuous` | `--cycle-seconds`, `--duration` | Execução cíclica por tempo determinado. |
| `run-live-simulated` | `--symbols`, `--mode` | Loop completo em tempo real simulado. |
| `schedule-jobs` | `--cycle-seconds`, `--news-seconds` | Agenda tarefas recorrentes. |

### Grupo 3: IA e Dados Alternativos
| Comando | Parâmetros Principais | Função |
| :--- | :--- | :--- |
| `ingest-news` | `--query`, `--days`, `--limit` | Carga de notícias (GDELT). |
| `score-news` | `--input-path` | Processamento NLP de notícias. |
| `train-market-model` | `--symbols`, `--interval` | Treino de modelos supervisionados. |
| `predict-market` | `--symbols`, `--interval` | Inferência com modelos salvos. |
| `optimize-strategy` | `--symbol`, `--trials` | Otimização via Optuna. |
| `fetch-fear-greed` | `--limit` | Carga do índice Fear & Greed. |

## 2. Exemplos de Uso Recomendados
### Fluxo de Preparação:
```bash
alphascope ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 1000
alphascope build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
alphascope build-training-dataset --symbols BTCUSDT,ETHUSDT --interval 1h
alphascope train-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
```

### Fluxo de Produção Simulada:
```bash
alphascope start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h
# Em outro terminal:
alphascope runtime-status
```

## 3. Comandos que podem falhar sem chaves API
- `fetch-market-universe` (Pode avisar sobre Rate Limit se `COINGECKO_API_KEY` estiver vazia).
- `ingest-news` (Depende da disponibilidade do endpoint GDELT).
- `test-telegram-alert` (Falha se `TELEGRAM_BOT_TOKEN` e `CHAT_ID` não estiverem no `.env`).

## 4. Ordem Recomendada de Execução
1. `ingest-market` (Dados básicos).
2. `build-features` (Indicadores).
3. `rank-assets` (Sinais).
4. `backtest` (Validação).
5. `start-daemon` (Operação).
