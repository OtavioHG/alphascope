# AlphaScope Operations Setup Complete

## Visao Geral

Este documento consolida a configuracao operacional do AlphaScope para uso completo com:

- dados de mercado
- IA de mercado
- IA de noticias
- ranking hibrido
- datasets grandes
- Parquet
- Optuna
- integracao com Binance, CoinGecko, CoinMarketCap, GDELT, Hugging Face e Kaggle

## 1. Instalacao

### Ambiente minimo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Ambiente completo

Use este ambiente para:

- Parquet
- datasets grandes
- machine learning
- transformers
- Optuna
- Hugging Face datasets

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-full.txt
pip install -e .
```

## 2. Arquivos de Configuracao

Copie:

```bash
copy .env.example .env
```

Campos principais do `.env`:

```env
APP_NAME=AlphaScope
SQLITE_PATH=data/alphascope.db

KAGGLE_DATA_DIR=data/external/kaggle
HF_DATASETS_DIR=data/external/huggingface
LARGE_DATA_FORMAT=parquet
MARKET_DATASET_PATH=data/processed/market_training_dataset.parquet
NEWS_DATASET_PATH=data/news/news_training_dataset.parquet

BINANCE_BASE_URL=https://api.binance.com
COINGECKO_BASE_URL=https://api.coingecko.com
COINMARKETCAP_BASE_URL=https://pro-api.coinmarketcap.com
GDELT_BASE_URL=https://api.gdeltproject.org

ENABLE_BINANCE=true
ENABLE_COINGECKO=true
ENABLE_COINMARKETCAP=false
COINGECKO_API_KEY=
COINMARKETCAP_API_KEY=

PRIMARY_MARKET_SOURCE=binance
FALLBACK_SOURCES=coingecko,coinmarketcap

RANKING_MODE=hybrid
RANKING_ML_WEIGHT=0.5
RANKING_HEURISTIC_WEIGHT=0.3
RANKING_NEWS_WEIGHT=0.2
RANKING_NEWS_LOOKBACK_HOURS=72

NLP_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
NLP_TOPIC_MODEL_NAME=facebook/bart-large-mnli
HUGGINGFACE_SENTIMENT_DATASET=financial_phrasebank

TARGET_HORIZON_BARS=6
TARGET_THRESHOLD_PCT=0.01
OPTUNA_TRIALS=20
```

## 3. Diretórios Criados Automaticamente

Na inicializacao do projeto, o AlphaScope garante:

- `data/`
- `data/raw/`
- `data/raw/market/`
- `data/raw/news/`
- `data/external/`
- `data/external/kaggle/`
- `data/external/huggingface/`
- `data/processed/`
- `data/news/`
- `data/optuna/`
- `models/`
- `models/market/`
- `models/nlp/`
- `logs/`

## 4. Onde Colocar Datasets Externos

### Mercado

Coloque datasets grandes em:

- `data/external/kaggle/`
- `data/external/huggingface/`

Formatos aceitos:

- `.csv`
- `.parquet`

Colunas minimas esperadas:

- `timestamp`
- `symbol`
- `open`
- `high`
- `low`
- `close`
- `volume`

Aliases comuns tambem sao normalizados:

- `date` -> `timestamp`
- `ticker` -> `symbol`
- `pair` -> `symbol`
- `base_volume` -> `volume`

### Noticias

Coloque datasets externos em:

- `data/external/kaggle/`
- `data/external/huggingface/`

Formatos aceitos:

- `.csv`
- `.jsonl`
- `.parquet`

Colunas minimas esperadas:

- `title`
- `text` ou `description`
- `timestamp`
- `source`

## 5. Financial PhraseBank

Voce pode usar de duas formas:

### Carregamento direto via Hugging Face

Com o ambiente completo instalado:

```bash
python -m alphascope.cli build-news-dataset --include-hf
```

### Export local

Se voce tiver exportado o dataset localmente:

```bash
python -m alphascope.cli build-news-dataset --hf-export-path data/external/huggingface/financial_phrasebank.parquet
```

## 6. Kaggle Datasets

Fluxo recomendado:

1. baixe o dataset
2. coloque em `data/external/kaggle/`
3. liste os arquivos disponiveis:

```bash
python -m alphascope.cli list-external-datasets --type all
```

4. importe e normalize:

### Mercado

```bash
python -m alphascope.cli import-market-dataset --input-path data/external/kaggle/market_history.csv
```

### Noticias

```bash
python -m alphascope.cli import-news-dataset --input-path data/external/kaggle/news_dataset.parquet
```

## 7. Ordem de Execucao Recomendada

### Etapa A. Mercado base

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Etapa B. Mercado com datasets grandes externos

```bash
python -m alphascope.cli import-market-dataset --input-path data/external/kaggle/market_history.csv
python -m alphascope.cli build-market-dataset --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --external-dataset-paths data/external/market_history.parquet
```

### Etapa C. IA de mercado

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Etapa D. Noticias

#### GDELT em tempo quase real

```bash
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
```

#### Dataset consolidado

```bash
python -m alphascope.cli build-news-dataset --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50 --include-hf
```

#### Importacao de base externa

```bash
python -m alphascope.cli import-news-dataset --input-path data/external/kaggle/news_dataset.parquet
```

#### Treino supervisionado leve

```bash
python -m alphascope.cli train-news-model --input-path data/news/news_training_dataset.csv --label-column label
```

#### Pontuacao

```bash
python -m alphascope.cli score-news --input-path data/news/news_training_dataset.csv
```

### Etapa E. Ranking com noticias

```bash
python -m alphascope.cli show-news-signals --symbols BTCUSDT,ETHUSDT,SOLUSDT --limit 20
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

### Etapa F. Backtest, paper trading e otimizacao

```bash
python -m alphascope.cli backtest --symbol BTCUSDT --interval 1h
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli optimize-strategy --symbol BTCUSDT --interval 1h --trials 20
```

## 8. Ranking Hibrido na Pratica

O ranking suporta:

- `heuristic`
- `ml`
- `hybrid`
- `hybrid_with_news`

### Recomendacao pratica

```env
RANKING_MODE=hybrid
RANKING_ML_WEIGHT=0.5
RANKING_HEURISTIC_WEIGHT=0.3
RANKING_NEWS_WEIGHT=0.2
RANKING_NEWS_LOOKBACK_HOURS=72
```

Se quiser forcar noticias como parte obrigatoria:

```env
RANKING_MODE=hybrid_with_news
```

## 9. CoinGecko e CoinMarketCap

### CoinGecko

Usado para:

- market cap
- ranking global
- metadata
- supply

### CoinMarketCap

Usado para:

- validacao complementar
- rank
- quotes
- market cap

Para ativar:

```env
ENABLE_COINMARKETCAP=true
COINMARKETCAP_API_KEY=sua_chave_aqui
```

Sem API key, o projeto falha cedo com mensagem clara se `ENABLE_COINMARKETCAP=true`.

Se `ENABLE_COINMARKETCAP=false`, ele e ignorado sem quebrar o pipeline.

## 10. Parquet

O projeto suporta:

- leitura de CSV por chunks
- conversao de CSV para Parquet
- exportacao de datasets em Parquet
- fallback para CSV

Comandos práticos:

```bash
python -m alphascope.cli import-market-dataset --input-path data/external/kaggle/market_history.csv
python -m alphascope.cli import-news-dataset --input-path data/external/kaggle/news_dataset.csv
```

Esses comandos validam schema antes de seguir.

## 11. Arquivos de Saida Relevantes

- `data/processed/market_training_dataset.parquet`
- `data/processed/market_training_dataset.csv`
- `data/news/news_training_dataset.parquet`
- `data/news/news_training_dataset.csv`
- `data/processed/scored_news_latest.csv`
- `models/market/best_market_model.joblib`
- `models/market/best_market_model.json`
- `models/nlp/news_sentiment_model.joblib`
- `models/nlp/news_sentiment_model.json`
- `data/optuna/*.json`
- `data/optuna/*.csv`

## 12. Checks e Falhas Amigaveis

O projeto agora valida:

- `RANKING_MODE` invalido
- `LARGE_DATA_FORMAT` invalido
- pesos de ranking negativos
- `TARGET_HORIZON_BARS <= 0`
- `TARGET_THRESHOLD_PCT < 0`
- CoinMarketCap habilitado sem API key
- schemas invalidos de datasets externos de mercado
- schemas invalidos de datasets externos de noticias

## 13. Comandos Disponiveis

Com a CLI atual:

```bash
python -m alphascope.cli --help
```

Comandos principais:

- `ingest-market`
- `build-features`
- `build-training-dataset`
- `build-market-dataset`
- `import-market-dataset`
- `train-market-model`
- `evaluate-market-model`
- `predict-market`
- `ingest-news`
- `build-news-dataset`
- `import-news-dataset`
- `train-news-model`
- `score-news`
- `show-news-signals`
- `rank-assets`
- `explain-ranking`
- `optimize-strategy`
- `paper-trade`
- `run-pipeline`

## 14. Estado Validado

Validado no workspace com:

- `python -m compileall src/alphascope`
- `pytest`
- `python -m alphascope.cli --help`

Estado atual:

- `21 passed`
- `2 skipped`

Os `skipped` sao testes de Parquet que dependem de `pyarrow` instalado no ambiente local.

Para ativar esses testes e o suporte completo a Parquet:

```bash
pip install -r requirements-full.txt
```
