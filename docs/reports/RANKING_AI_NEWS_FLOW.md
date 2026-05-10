# AlphaScope Ranking AI News Flow

## Visao Geral

O ranking do AlphaScope agora suporta tres camadas de score:

- score heuristico baseado em features tecnicas
- score de IA de mercado via modelo supervisionado
- score de noticias agregado por ativo

Essas camadas podem ser usadas em tres modos:

- `heuristic`
- `ml`
- `hybrid`

No modo `hybrid`, o score final pode combinar heuristica, ML e noticias.

## Componentes Envolvidos

### Ranking tecnico

Arquivos principais:

- `src/alphascope/ranking/scorer.py`
- `src/alphascope/ranking/ranker.py`

Componentes tecnicos usados no score:

- `momentum_component`
- `volume_component`
- `trend_component`
- `rsi_component`

### IA de mercado

Arquivos principais:

- `src/alphascope/datasets/market_dataset_builder.py`
- `src/alphascope/ml/train_market_model.py`
- `src/alphascope/ml/evaluate_market_model.py`
- `src/alphascope/ml/inference.py`

Saida principal:

- `ml_probability`

### Noticias

Arquivos principais:

- `src/alphascope/datasets/news_dataset_builder.py`
- `src/alphascope/nlp/inference.py`
- `src/alphascope/core/pipeline.py`

Saidas principais:

- `sentiment_score`
- `impact_score`
- `related_asset`
- `news_score`

## Como o Score de Noticias e Calculado

O arquivo processado de noticias fica em:

- `data/processed/scored_news_latest.csv`

O pipeline:

1. carrega noticias pontuadas
2. filtra pela janela `RANKING_NEWS_LOOKBACK_HOURS`
3. agrupa por `related_asset`
4. calcula:
   - media de `sentiment_score`
   - media de `impact_score`
   - quantidade de noticias
   - timestamp da noticia mais recente
5. gera:

```text
news_score = 0.5 + ((avg_sentiment_score - 0.5) * impact_norm)
```

Onde:

- `impact_norm` e o `impact_score` limitado ao intervalo `[0, 1]`

## Modos de Ranking

### heuristic

Usa apenas o score tecnico.

### ml

Usa apenas:

- `ml_probability`

### hybrid

Combina:

- `heuristic_score * RANKING_HEURISTIC_WEIGHT`
- `ml_probability * RANKING_ML_WEIGHT`
- `news_score * RANKING_NEWS_WEIGHT`

O resultado final e normalizado pela soma dos pesos ativos.

## Configuracoes Relevantes

No `.env`:

```env
RANKING_MODE=hybrid
RANKING_ML_WEIGHT=0.6
RANKING_HEURISTIC_WEIGHT=0.2
RANKING_NEWS_WEIGHT=0.2
RANKING_NEWS_LOOKBACK_HOURS=72
```

Outras configuracoes importantes:

```env
NLP_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
NLP_TOPIC_MODEL_NAME=facebook/bart-large-mnli
```

## Fluxo Operacional Recomendado

### 1. Ingerir mercado

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

### 2. Gerar features

```bash
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### 3. Treinar modelo de mercado

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### 4. Ingerir e pontuar noticias

```bash
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
python -m alphascope.cli score-news --input-path data/news/gdelt_news_latest.csv
```

Ou usando dataset consolidado:

```bash
python -m alphascope.cli build-news-dataset --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50 --include-hf
python -m alphascope.cli score-news --input-path data/news/news_training_dataset.csv
```

### 5. Inspecionar sinais de noticias

```bash
python -m alphascope.cli show-news-signals --symbols BTCUSDT,ETHUSDT,SOLUSDT --limit 20
```

### 6. Gerar ranking

```bash
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### 7. Explicar ranking

```bash
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

## Comandos Relacionados

### Mercado

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT --interval 1h
```

### Noticias

```bash
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
python -m alphascope.cli build-news-dataset --include-hf
python -m alphascope.cli train-news-model --input-path data/news/news_training_dataset.csv --label-column label
python -m alphascope.cli score-news --input-path data/news/news_training_dataset.csv
python -m alphascope.cli show-news-signals --limit 20
```

### Ranking

```bash
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

## Arquivos de Saida Importantes

- `data/processed/market_training_dataset_1h.csv`
- `models/market/best_market_model.joblib`
- `models/market/best_market_model.json`
- `data/news/gdelt_news_latest.csv`
- `data/news/news_training_dataset.csv`
- `models/nlp/news_sentiment_model.joblib`
- `models/nlp/news_sentiment_model.json`
- `data/processed/scored_news_latest.csv`

## O que o explain-ranking mostra

O comando `explain-ranking` exibe por ativo:

- score final
- rank
- score heuristico
- probabilidade do modelo de mercado
- score de noticias
- contribuicao ponderada de cada camada
- componentes tecnicos internos

Isso permite auditar exatamente por que um ativo ficou acima ou abaixo de outro no ranking final.

## Estado Validado

Validado no workspace com:

- `pytest` -> `19 passed`
- `python -m compileall src/alphascope`
- `python -m alphascope.cli --help`
- `python -m alphascope.cli show-news-signals --help`
- `python -m alphascope.cli explain-ranking --help`
