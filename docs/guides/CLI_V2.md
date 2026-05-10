# CLI V2

## Comandos principais

### Control Center

```bash
alphascope-cc dashboard
alphascope-cc status
alphascope-cc tui
alphascope-cc entry-check --symbol BTCUSDT --close 70000 --rsi 58 --macd-histogram 0.4 --ma-fast 70200 --ma-slow 69000 --trend-strength 0.8 --relative-volume 1.6 --volatility 0.03 --momentum 0.5 --breakout-strength 0.012
```

### Mercado e ranking

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT --interval 1h
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT --interval 1h --limit 20
python -m alphascope.cli build-universe --top 100 --quote USDT --min-volume 10000000
python -m alphascope.cli fetch-market-universe --primary-source binance --fallback-sources coingecko,coinmarketcap --limit 100
python -m alphascope.cli show-universe --kind auto --limit 20
```

### Trading, execução e runtime

```bash
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli run-continuous --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500
python -m alphascope.cli runtime-status
python -m alphascope.cli show-jobs
python -m alphascope.cli start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h
python -m alphascope.cli stop-daemon
python -m alphascope.cli run-live-simulated --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 60 --timeframe 1h
python -m alphascope.cli start-live-trading --interval 1h
python -m alphascope.cli sync-account
python -m alphascope.cli emergency-close --interval 1h
python -m alphascope.cli reset-live-state
```

### Dados, ML e pesquisa

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli build-market-dataset --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
python -m alphascope.cli build-news-dataset --query "crypto OR bitcoin OR ethereum" --days 7 --limit 200 --include-hf
python -m alphascope.cli train-news-model
python -m alphascope.cli score-news
python -m alphascope.cli optimize-strategy --symbol BTCUSDT --interval 1h --trials 20
```

### API, painel e Telegram

```bash
python -m alphascope.cli control-center
python -m alphascope.cli platform-status
python -m alphascope.cli run-platform-api --host 0.0.0.0 --port 8010
python -m alphascope.cli run-dashboard
python -m alphascope.cli run-api
python -m alphascope.cli run-telegram-bot
python -m alphascope.cli test-telegram-alert
python -m alphascope.cli send-runtime-alert
python -m alphascope.cli send-portfolio-alert --label "Resumo manual"
```

### Inspeção e troubleshooting

```bash
python -m alphascope.cli show-data --type ranking --interval 1h --limit 20
python -m alphascope.cli show-data --type open-positions --limit 20
python -m alphascope.cli show-data --type live-trades --limit 20
python -m alphascope.cli show-trader-mode
python -m alphascope.cli list-external-datasets --type all
python -m alphascope.cli show-news-signals --limit 20
```

## Compatibilidade

Os comandos legados de ingestão, runtime, paper trading, ML e dashboard continuam disponíveis via `python -m alphascope.cli`.
