# 05_AI_STACK - AlphaScope Audit

## 1. Features Técnicas
Implementadas em `features/technical.py` e `features/feature_pipeline.py`.
- **Indicadores:** RSI, Médias Móveis (curta/longa), Volatilidade, Momentum, Volume Relativo.
- **Processamento:** Normalização de features para modelos de ML via `feature_pipeline.py`.

## 2. Processamento de Linguagem Natural (NLP)
O sistema transforma notícias em sinais quantitativos.
- **Módulos:** `nlp/sentiment.py`, `nlp/topics.py`, `nlp/inference.py`.
- **Modelos:** Utiliza Transformers (Hugging Face) para:
    - Sentimento (Positive/Negative/Neutral).
    - Classificação de tópicos (Zero-Shot).
    - Extração de ativo citado.
- **Scoring:** Notícias são pontuadas e integradas ao ranking global (`nlp/inference.py`).

## 3. Machine Learning de Mercado
- **Modelos Encontrados:** Logistic Regression, Random Forest, Gradient Boosting.
- **Treinamento:** Pipeline centralizado em `ml/train_market_model.py`.
- **Avaliação:** Métricas de performance (Acurácia, F1-Score, Matriz de Confusão) em `ml/evaluate_market_model.py`.
- **Inferência:** Probabilidades de alta/baixa integradas ao ranking híbrido.

## 4. Ranking de Ativos
O motor de ranking em `ranking/ranker.py` e `ranking/scorer.py` consolida os sinais.
- **Modos de Ranking:**
    - `heuristic`: Baseado em pesos manuais nos indicadores técnicos.
    - `ml`: Baseado puramente na probabilidade predita pelos modelos de ML.
    - `hybrid`: Combinação ponderada de Heurística + ML.
    - `hybrid_with_news`: Adiciona score de notícias (NLP) ao ranking híbrido.

## 5. Backtest e Otimização
- **Backtest Engine:** Simula a estratégia historicamente (`backtest/engine.py`).
- **Otimização:** Tuning de hiperparâmetros da estratégia usando **Optuna** (`optimization/strategy_optimizer.py`).
- **Validação:** Módulo de `walk_forward.py` para testes de robustez temporal.

## 6. Governança e Evolução
- **Evolution Engine:** Classes em `evolution/` para gerenciamento do ciclo de vida das estratégias.
- **Degradation Detection:** O módulo `degradation_detector.py` monitora a performance dos modelos em produção para disparar alertas de retreino.
- **Research Sandbox:** Ambiente para testar novas hipóteses de sinais (`sandbox/research_sandbox.py`).
