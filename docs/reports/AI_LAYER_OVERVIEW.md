# AlphaScope Camada de IA

Este documento consolida a implementacao da camada de IA adicionada ao AlphaScope.

## Visao geral

A camada de IA foi adicionada sem quebrar a arquitetura atual da V1 e cobre tres blocos principais:

- IA de mercado
- IA de noticias
- otimizacao de estrategia

Ela foi integrada ao projeto existente de forma modular, reutilizando:

- storage local
- features tecnicas
- pipeline atual
- ranking
- CLI

## 1. IA de mercado

### Objetivo

Treinar modelos supervisionados para prever probabilidade de movimento relevante de preco e integrar esse score ao ranking.

### Componentes implementados

- `src/alphascope/ml/dataset_builder.py`
- `src/alphascope/ml/targets.py`
- `src/alphascope/ml/train_market_model.py`
- `src/alphascope/ml/evaluate_market_model.py`
- `src/alphascope/ml/model_registry.py`
- `src/alphascope/ml/inference.py`

### Features usadas

- `return_pct`
- `ma_short`
- `ma_long`
- `rsi`
- `volatility`
- `avg_volume`
- `relative_volume`
- `momentum`
- `trend_strength`

### Targets implementados

- `future_return_target`
- `up_move_target`
- `binary_breakout_target`

### Modelos implementados

- `LogisticRegression`
- `RandomForestClassifier`
- `GradientBoostingClassifier`

### Regras de treino

- split temporal
- sem embaralhamento
- sem leakage
- persistencia com `joblib`
- metadata salva em JSON

### Metricas

- accuracy
- precision
- recall
- f1
- roc_auc

### Integracao com ranking

O ranking agora suporta:

- `RANKING_MODE=heuristic`
- `RANKING_MODE=ml`
- `RANKING_MODE=hybrid`

No modo `hybrid`, o score final combina:

- score heuristico
- `ml_probability`

## 2. IA de noticias

### Objetivo

Pontuar noticias com sentimento, topico, ativo relacionado e impacto.

### Componentes implementados

- `src/alphascope/nlp/sentiment.py`
- `src/alphascope/nlp/topics.py`
- `src/alphascope/nlp/news_dataset_builder.py`
- `src/alphascope/nlp/train_sentiment_model.py`
- `src/alphascope/nlp/inference.py`

### Fontes suportadas

- GDELT
- datasets exportados localmente do Hugging Face
- datasets exportados localmente do Kaggle

### Fase 1 implementada

- sentimento com transformers
- topic classification com zero-shot
- extracao simples de ativo citado
- calculo de `impact_score`

### Saidas geradas

- `sentiment_label`
- `sentiment_score`
- `topic_label`
- `related_asset`
- `impact_score`

### Fase 2 preparada

Foi adicionada base para treino supervisionado leve de sentimento com:

- `TfidfVectorizer`
- `LogisticRegression`

Isso serve como etapa preparatoria para evolucao futura de fine-tuning mais especifico.

## 3. Otimizacao de estrategia

### Objetivo

Encontrar melhores parametros da estrategia usando backtest como funcao objetivo.

### Componentes implementados

- `src/alphascope/optimization/objective.py`
- `src/alphascope/optimization/tuner.py`

### Parametros otimizados

- `short_window`
- `long_window`
- `rsi_window`
- `volatility_window`
- `volume_window`
- `momentum_window`
- `buy_threshold`
- `sell_threshold`
- `fee_rate`

### Criterio da objective

A objective considera:

- retorno acumulado
- profit factor
- win rate
- drawdown

### Persistencia

Os resultados sao salvos em:

- `data/optuna/best_params_<symbol>_<interval>.json`
- `data/optuna/study_trials_<symbol>_<interval>.csv`

## 4. Comandos de CLI adicionados

### Mercado

```bash
python -m alphascope.cli build-training-dataset --symbols BTCUSDT,ETHUSDT --interval 1h --horizon-bars 6 --threshold-pct 0.01
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Noticias

```bash
python -m alphascope.cli ingest-news --query "crypto OR bitcoin OR ethereum" --days 1 --limit 50
python -m alphascope.cli score-news --input-path data/news/gdelt_news_latest.csv
```

### Otimizacao

```bash
python -m alphascope.cli optimize-strategy --symbol BTCUSDT --interval 1h --trials 20
```

## 5. Configuracoes adicionadas

As seguintes chaves foram adicionadas em `.env` e `.env.example`:

- `RANKING_MODE`
- `RANKING_ML_WEIGHT`
- `RANKING_HEURISTIC_WEIGHT`
- `MARKET_TARGET_NAME`
- `TARGET_HORIZON_BARS`
- `TARGET_THRESHOLD_PCT`
- `TRAINING_TRAIN_FRACTION`
- `NLP_MODEL_NAME`
- `NLP_TOPIC_MODEL_NAME`
- `OPTUNA_TRIALS`

## 6. Estrutura de arquivos gerados

### Modelos

- `models/market/best_market_model.joblib`
- `models/market/best_market_model.json`
- `models/nlp/news_sentiment_model.joblib`
- `models/nlp/news_sentiment_model.json`

### Dados processados

- `data/processed/market_training_dataset_<interval>.csv`
- `data/processed/scored_news_latest.csv`

### Dados de noticias

- `data/news/gdelt_news_latest.csv`

### Otimizacao

- `data/optuna/*.json`
- `data/optuna/*.csv`

## 7. Dependencias relevantes

Para usar toda a camada de IA, instale:

```bash
pip install -r requirements-full.txt
pip install -e .
```

Dependencias principais dessa camada:

- `scikit-learn`
- `joblib`
- `transformers`
- `optuna`

## 8. Validacao realizada

Estado atual validado:

- `python -m compileall src\\alphascope`
- `python -m alphascope.cli --help`
- `pytest`

Resultado atual:

- `13 passed`

## 9. Resumo final

A camada de IA do AlphaScope agora consegue:

- construir dataset supervisionado de mercado
- treinar e comparar modelos
- salvar e carregar o melhor modelo
- gerar probabilidade de alta por ativo
- integrar score de ML ao ranking
- ingerir noticias
- classificar sentimento e topico
- estimar impacto de noticia
- otimizar parametros de estrategia com Optuna

Tudo isso foi integrado ao projeto existente sem quebrar:

- ingestao
- storage
- features
- ranking atual
- backtest
- paper trading
- CLI
