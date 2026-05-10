# 01_PROJECT_MAP - AlphaScope Audit

## 1. Árvore Resumida do Projeto
```text
AlphaScope/
├── src/alphascope/         # Código-fonte principal (Python)
│   ├── api/                # API FastAPI (rotas e servidor)
│   ├── automation/         # Daemon, Scheduler, Heartbeat
│   ├── backtest/           # Motor de backtest e métricas
│   ├── config/             # Configurações e constantes
│   ├── core/               # Logger, pipeline central e exceções
│   ├── dashboard/          # Streamlit dashboard e componentes
│   ├── data_management/    # Catálogo de dados e linhagem
│   ├── data_sources/       # Clientes de APIs externas
│   ├── datasets/           # Builder de datasets para ML e NLP
│   ├── discovery/          # Detecção de anomalias e regimes
│   ├── domain/             # Esquemas Pydantic e tipos comuns
│   ├── events/             # Barramento de eventos (EventBus)
│   ├── evolution/          # Ciclo de vida e retreino de estratégias
│   ├── execution/          # Paper Trading e simulação de execução
│   ├── external_data/      # Agregador multi-fonte de mercado
│   ├── feature_store/      # Registro e persistência de features
│   ├── features/           # Pipeline de indicadores técnicos
│   ├── governance/         # Logs de decisão e políticas
│   ├── infrastructure/     # Postgres, Redis e Repositórios
│   ├── ingestion/          # Ingestores de candles e notícias
│   ├── meta_learning/      # Seleção de features e meta-modelos
│   ├── ml/                 # Treino, avaliação e inferência de mercado
│   ├── models/             # Treinadores e preditores genéricos
│   ├── monitoring/         # Runtime status, métricas e tracing
│   ├── news_sources/       # GDELT, Hugging Face, Kaggle
│   ├── nlp/                # Sentimento e classificação de notícias
│   ├── optimization/       # Optuna e tuning de hiperparâmetros
│   ├── portfolio/          # Motor de portfólio e gestão de risco
│   ├── ranking/            # Scorer e Ranker de ativos
│   ├── research/           # Pipeline de pesquisa e hipóteses
│   ├── simulation/         # Simulador Live e execução controlada
│   ├── storage/            # SQLite, ORM e migrações
│   ├── universe/           # Builder de universo de ativos
│   └── utils/              # Funções auxiliares (IO, tempo)
├── tests/                  # Suite de testes automatizados (49+ arquivos)
├── data/                   # Armazenamento persistente (SQLite, Parquet, CSV)
├── docs/                   # Documentação, guias e relatórios
├── frontend/               # Next.js (Scaffold inicial)
├── services/go/            # Microsserviços em Go (Scaffold)
├── deployment/             # Docker e infra de deploy
├── .env                    # Variáveis de ambiente reais
├── pyproject.toml          # Definições do projeto e entrypoints
└── requirements-full.txt   # Dependências completas
```

## 2. Funções Críticas por Módulo
- **`src/alphascope/cli.py`**: Entrypoint central que despacha todos os comandos.
- **`src/alphascope/core/pipeline.py`**: Orquestra o fluxo Ingestão -> Features -> Ranking -> Backtest/Trade.
- **`src/alphascope/automation/daemon_runner.py`**: Mantém o sistema vivo em ciclos repetitivos.
- **`src/alphascope/ranking/scorer.py`**: Implementa a lógica do ranking híbrido (Heurística + ML + News).
- **`src/alphascope/execution/paper_trader.py`**: Simula a carteira com trades baseados nos sinais gerados.
- **`src/alphascope/storage/repositories.py`**: Interface unificada de acesso aos dados.

## 3. Entrypoints Principais
- **CLI:** `alphascope` (registrado via `pyproject.toml`).
- **API:** `python -m alphascope.api.api_server`.
- **Dashboard:** `streamlit run src/alphascope/dashboard/app.py`.

## 4. Dependências Críticas
- **Pandas/NumPy:** Processamento de dados.
- **SQLAlchemy:** Persistência.
- **Scikit-learn/Joblib:** Machine Learning.
- **Transformers:** NLP.
- **FastAPI/Streamlit:** Interfaces.
- **Optuna:** Otimização.
