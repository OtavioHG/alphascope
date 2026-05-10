# AlphaScope Guia Completo

## 1. Visao Geral

O AlphaScope e uma plataforma quantitativa para mercado cripto que combina:

- ingestao de dados de mercado
- consolidacao de multiplas APIs
- persistencia local
- geracao de features tecnicas
- IA de mercado
- IA de noticias
- ranking hibrido
- backtest
- paper trading
- otimizacao com Optuna
- operacao por CLI

O projeto foi estruturado para funcionar de forma incremental. Voce pode usar apenas a parte de mercado, ou adicionar gradualmente noticias, IA, datasets externos e fontes complementares.

## 2. Como o sistema funciona

O fluxo principal do AlphaScope e:

1. coletar dados de mercado
2. salvar localmente em SQLite e arquivos auxiliares
3. gerar features tecnicas
4. enriquecer com dados externos
5. gerar score por ativo
6. aplicar IA de mercado e noticias
7. executar ranking
8. rodar backtest ou paper trading

### Camadas principais

- `src/alphascope/data_sources/`: clientes de APIs de mercado e sentimento
- `src/alphascope/news_sources/`: clientes e loaders de noticias e datasets
- `src/alphascope/datasets/`: builders, validadores e utilitarios de Parquet
- `src/alphascope/features/`: features tecnicas
- `src/alphascope/ml/`: treino, avaliacao e inferencia da IA de mercado
- `src/alphascope/nlp/`: sentimento e topicos de noticias
- `src/alphascope/ranking/`: scoring e ranking hibrido
- `src/alphascope/backtest/`: simulacao historica
- `src/alphascope/execution/`: paper trading
- `src/alphascope/optimization/`: tuning com Optuna
- `src/alphascope/cli.py`: interface operacional principal

## 3. Fontes de dados suportadas

### Mercado

- Binance
  - fonte principal para candles, volume e ticker
- CryptoCompare
  - historico complementar, snapshot, market cap e supply
- CoinGecko
  - market cap, rank global e metadata
- CoinMarketCap
  - validacao complementar de quotes, market cap e rank

### Noticias e sentimento

- GDELT
  - noticias e eventos quase em tempo real
- Hugging Face datasets
  - exemplo: `financial_phrasebank`
- Kaggle datasets
  - noticias financeiras e bases externas grandes
- Fear & Greed Index
  - sentimento global do mercado cripto

## 4. Como instalar

### Ambiente minimo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Ambiente completo

```bash
pip install -r requirements-full.txt
pip install -e .
```

O ambiente completo inclui:

- `scikit-learn`
- `joblib`
- `transformers`
- `optuna`
- `datasets`
- `pyarrow`

`pyarrow` e importante para exportacao e leitura em Parquet.

## 5. Configuracao do .env

O arquivo `.env` controla tudo:

- paths locais
- chaves de APIs
- modos de ranking
- janelas tecnicas
- alvo de treinamento
- parametros de backtest e paper trading

### Exemplo de configuracao funcional

```env
APP_NAME=AlphaScope
APP_ENV=development
LOG_LEVEL=INFO

DATA_DIR=data
LOG_DIR=logs
SQLITE_PATH=data/alphascope.db

KAGGLE_DATA_DIR=data/external/kaggle
HF_DATASETS_DIR=data/external/huggingface
LARGE_DATA_FORMAT=parquet
MARKET_DATASET_PATH=data/processed/market_training_dataset.parquet
NEWS_DATASET_PATH=data/news/news_training_dataset.parquet

BINANCE_BASE_URL=https://api.binance.com
CRYPTOCOMPARE_BASE_URL=https://min-api.cryptocompare.com
COINGECKO_BASE_URL=https://api.coingecko.com
COINMARKETCAP_BASE_URL=https://pro-api.coinmarketcap.com
GDELT_BASE_URL=https://api.gdeltproject.org
FEAR_GREED_API=https://api.alternative.me/fng/

COINGECKO_API_KEY=
COINMARKETCAP_API_KEY=

ENABLE_BINANCE=true
ENABLE_CRYPTOCOMPARE=true
ENABLE_COINGECKO=true
ENABLE_COINMARKETCAP=false
ENABLE_FEAR_GREED=true

PRIMARY_MARKET_SOURCE=binance
FALLBACK_SOURCES=coingecko,coinmarketcap

RANKING_MODE=hybrid
RANKING_ML_WEIGHT=0.60
RANKING_HEURISTIC_WEIGHT=0.25
RANKING_NEWS_WEIGHT=0.15
RANKING_NEWS_LOOKBACK_HOURS=72
```

### O que e obrigatorio e opcional

- obrigatorio para operar o core:
  - Binance
- opcional, mas recomendado:
  - CoinGecko
  - CryptoCompare
  - Fear & Greed
- opcional com chave:
  - CoinMarketCap

## 6. Estrutura de dados local

O projeto cria automaticamente os diretorios necessarios.

### Diretórios principais

- `data/raw/market/`
- `data/raw/market/cryptocompare/`
- `data/raw/market/fear_greed/`
- `data/raw/news/`
- `data/external/kaggle/`
- `data/external/huggingface/`
- `data/processed/`
- `data/news/`
- `data/optuna/`
- `models/market/`
- `models/nlp/`
- `logs/`

### O que vai para cada lugar

- `SQLite`: candles, features, ranking, paper trades, snapshots
- `data/raw/`: dados coletados das APIs
- `data/processed/`: datasets prontos para treino e uso analitico
- `models/`: artefatos treinados
- `logs/`: logs de execucao

## 7. Pipeline de mercado

### Etapa 1. Ingestao

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

Isso baixa candles da Binance e grava no banco local.

### Etapa 2. Features

```bash
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Features geradas:

- `return_pct`
- `ma_short`
- `ma_long`
- `rsi`
- `volatility`
- `avg_volume`
- `relative_volume`
- `momentum`
- `trend_strength`

### Etapa 3. Enriquecimento externo

O dataset de mercado pode ser enriquecido com:

- CoinGecko: `market_cap`, `market_rank`
- CoinMarketCap: validacao complementar
- CryptoCompare: `cryptocompare_market_cap`, `cryptocompare_supply`
- Fear & Greed: `fear_greed_value`, `fear_greed_label`
- correlacao com BTC: `btc_correlation_24`

### Etapa 4. Dataset final

```bash
python -m alphascope.cli build-market-dataset --symbols BTCUSDT --interval 1h
```

O resultado vai para:

- [market_training_dataset.parquet](D:/AlphaScope/data/processed/market_training_dataset.parquet)

## 8. IA de mercado

### Objetivo

Prever probabilidade de movimento positivo futuro e melhorar o ranking de ativos.

### Targets

O projeto suporta:

- `future_return_target`
- `up_move_target`
- `binary_breakout_target`

### Treino

```bash
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Modelos treinados:

- `LogisticRegression`
- `RandomForestClassifier`
- `GradientBoostingClassifier`

### Avaliacao

```bash
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Metricas:

- `accuracy`
- `precision`
- `recall`
- `f1`
- `roc_auc`

### Inferencia

```bash
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

Saida principal:

- `ml_probability`

## 9. IA de noticias

### Fontes

- GDELT
- Hugging Face
- Kaggle

### Ingestao

```bash
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
```

### Dataset consolidado

```bash
python -m alphascope.cli build-news-dataset --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50 --include-hf
```

### Treino supervisionado

```bash
python -m alphascope.cli train-news-model --input-path data/news/news_training_dataset.csv --label-column label
```

### Scoring

```bash
python -m alphascope.cli score-news --input-path data/news/gdelt_news_latest.csv
```

Saidas:

- `sentiment_label`
- `sentiment_score`
- `topic_label`
- `related_asset`
- `impact_score`

## 10. Ranking hibrido

### Modos disponiveis

- `heuristic`
- `ml`
- `hybrid`
- `hybrid_with_news`

### Formula geral

O score final pode combinar:

- score heuristico
- probabilidade da IA de mercado
- score agregado de noticias

Exemplo:

```text
score_final =
heuristic_score * heuristic_weight +
ml_probability * ml_weight +
news_score * news_weight
```

### Ajuste com Fear & Greed

O ranking tambem pode aplicar um ajuste contrarian:

- `Extreme Fear`: leve incentivo a compra
- `Extreme Greed`: leve reducao do score

### Explicacao do ranking

```bash
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

### Inspecao de noticias agregadas

```bash
python -m alphascope.cli show-news-signals --symbols BTCUSDT,ETHUSDT --limit 20
```

## 11. Backtest e paper trading

### Backtest

```bash
python -m alphascope.cli backtest --symbol BTCUSDT --interval 1h
```

### Paper trading

```bash
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

## 12. Otimizacao com Optuna

### Objetivo

Encontrar configuracoes melhores para estrategia e parametros tecnicos.

### Comando

```bash
python -m alphascope.cli optimize-strategy --symbol BTCUSDT --interval 1h --trials 20
```

### Parametros otimizaveis

- `short_window`
- `long_window`
- `rsi_window`
- `volatility_window`
- `volume_window`
- `momentum_window`
- `buy_threshold`
- `sell_threshold`

## 13. Datasets externos grandes

O AlphaScope suporta dados externos em:

- CSV
- Parquet

Locais recomendados:

- `data/external/kaggle/`
- `data/external/huggingface/`

### Importacao de mercado

```bash
python -m alphascope.cli import-market-dataset --input-path data/external/kaggle/market_history.csv
```

### Importacao de noticias

```bash
python -m alphascope.cli import-news-dataset --input-path data/external/kaggle/news_dataset.parquet
```

### Listagem

```bash
python -m alphascope.cli list-external-datasets --type all
```

## 14. Novas integracoes recentes

### CryptoCompare

```bash
python -m alphascope.cli fetch-cryptocompare-history --symbol BTC --interval 1h --limit 500
```

Arquivos gerados:

- `data/raw/market/cryptocompare/btc_1h.parquet`
- `data/raw/market/cryptocompare/btc_1h.csv`

### Fear & Greed

```bash
python -m alphascope.cli fetch-fear-greed --limit 30
```

Arquivos gerados:

- `data/raw/market/fear_greed/fear_greed_latest.parquet`
- `data/raw/market/fear_greed/fear_greed_latest.csv`

## 15. Fluxo recomendado de uso

### Fluxo basico operacional

1. configurar `.env`
2. instalar `requirements-full.txt`
3. rodar `ingest-market`
4. rodar `build-features`
5. rodar `build-market-dataset`
6. rodar `train-market-model`
7. rodar `ingest-news`
8. rodar `score-news`
9. rodar `rank-assets`
10. rodar `backtest` ou `paper-trade`

### Fluxo completo com enriquecimento externo

1. `fetch-cryptocompare-history`
2. `fetch-fear-greed`
3. `fetch-market-universe`
4. `build-market-dataset`
5. `train-market-model`
6. `build-news-dataset`
7. `train-news-model`
8. `score-news`
9. `explain-ranking`
10. `optimize-strategy`

## 16. Erros comuns e como resolver

### Parquet nao grava

Causa:
- `pyarrow` nao instalado

Solucao:

```bash
python -m pip install pyarrow
```

### CoinMarketCap nao entra no fluxo

Causa:
- `ENABLE_COINMARKETCAP=false`
- ou `COINMARKETCAP_API_KEY` vazia

### Noticias nao afetam ranking

Causa:
- `RANKING_NEWS_WEIGHT=0`
- ou `score-news` ainda nao rodou

### Dataset builder falha em merge temporal

Situacao anterior:
- havia incompatibilidade de `timestamp`

Estado atual:
- corrigido com padronizacao para `datetime64[ns]`

## 17. Validacao final recomendada

Depois da configuracao, valide com:

```bash
python -m alphascope.cli --help
pytest
python -m alphascope.cli fetch-cryptocompare-history --symbol BTC --interval 1h --limit 5
python -m alphascope.cli fetch-fear-greed --limit 5
python -m alphascope.cli build-market-dataset --symbols BTCUSDT --interval 1h
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

## 18. Documentos complementares

Os relatorios detalhados agora estao organizados em `docs/`.

Principais arquivos:

- [AI_LAYER_OVERVIEW.md](D:/AlphaScope/docs/reports/AI_LAYER_OVERVIEW.md)
- [CHANGELOG.md](D:/AlphaScope/docs/reports/CHANGELOG.md)
- [CRYPTOCOMPARE_FEAR_GREED_REPORT.md](D:/AlphaScope/docs/reports/CRYPTOCOMPARE_FEAR_GREED_REPORT.md)
- [DEPENDENCY_AUDIT.md](D:/AlphaScope/docs/reports/DEPENDENCY_AUDIT.md)
- [LANGUAGES_OVERVIEW.md](D:/AlphaScope/docs/reports/LANGUAGES_OVERVIEW.md)
- [OPERATIONS_SETUP_COMPLETE.md](D:/AlphaScope/docs/guides/OPERATIONS_SETUP_COMPLETE.md)
- [RANKING_AI_NEWS_FLOW.md](D:/AlphaScope/docs/reports/RANKING_AI_NEWS_FLOW.md)
- [START_PROJECT.md](D:/AlphaScope/docs/guides/START_PROJECT.md)

## 19. Conclusao

O AlphaScope esta estruturado para operar como uma stack quantitativa modular:

- coleta dados
- enriquece o contexto de mercado
- gera features
- treina modelos
- pontua ativos
- combina heuristica, IA e noticias
- testa estrategias
- simula execucao

O modo de uso recomendado e incremental, mas o sistema ja esta preparado para um fluxo mais completo com:

- multiplas APIs
- datasets grandes
- Parquet
- IA supervisionada
- NLP
- ranking hibrido
- validacao operacional real
