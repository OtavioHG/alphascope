# 09_FILES_FOR_AI_CONTEXT - AlphaScope Audit

## 1. Arquivos Recomendados para Contexto de IA
Se outra IA precisar entender o AlphaScope rapidamente, estes são os arquivos críticos na ordem recomendada de leitura:

### Fase 1: Visão Geral e Arquitetura
1.  `README.md`: Visão geral e comandos.
2.  `src/alphascope/cli.py`: Mapeamento de todos os subcomandos e entrypoints.
3.  `project_audit/02_ARCHITECTURE_REAL.md`: Diagramas e fluxos de dados reais.

### Fase 2: Configuração e Dependências
1.  `.env.example`: Configurações de chaves e constantes de ambiente.
2.  `pyproject.toml`: Dependências e scripts de entrada.
3.  `src/alphascope/config/settings.py`: Definições globais e paths.

### Fase 3: Core e Pipeline
1.  `src/alphascope/core/pipeline.py`: O orquestrador central do fluxo quantitativo.
2.  `src/alphascope/automation/daemon_runner.py`: O motor de execução operacional.
3.  `src/alphascope/ranking/scorer.py`: O coração da inteligência de ranking.

### Fase 4: Dados e Persistência
1.  `src/alphascope/storage/database.py`: Definição de modelos e persistência.
2.  `src/alphascope/storage/repositories.py`: Abstração de acesso aos dados.
3.  `src/alphascope/external_data/aggregator.py`: Consolidação multi-fonte.

### Fase 5: IA (ML e NLP)
1.  `src/alphascope/ml/train_market_model.py`: Pipeline de treinamento de mercado.
2.  `src/alphascope/nlp/inference.py`: Transformação de notícias em sinais.

### Fase 6: Operação e Monitoramento
1.  `src/alphascope/execution/paper_trader.py`: Simulação operacional e gestão de portfólio.
2.  `src/alphascope/monitoring/runtime_status.py`: Visão consolidada da saúde do sistema.

## 2. Motivo da Importância
- **`cli.py`**: Serve como o "mapa" de todas as intenções do sistema.
- **`pipeline.py`**: Define como os módulos se conectam (A -> B -> C).
- **`scorer.py`**: Define o que é considerado um "bom sinal" no sistema.
- **`repositories.py`**: Define a interface de comunicação com o estado (DB).
- **`daemon_runner.py`**: Define a estabilidade e o comportamento de longa duração.
