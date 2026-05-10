# AlphaScope Auditoria de Dependências

## 1. Dependências detectadas no código

A análise dos imports em `src/alphascope/` e `tests/` identifica as seguintes bibliotecas externas:

### Núcleo da V1
- `pandas`
  - Base de manipulação tabular usada em ingestão, features, ranking, backtest, paper trading, storage e testes.
- `numpy`
  - Usada em cálculos numéricos, indicadores técnicos, métricas e módulos quantitativos.
- `requests`
  - Cliente HTTP usado principalmente para ingestão de dados e integrações externas.
- `sqlalchemy`
  - Camada ORM e acesso ao banco local.
- `pydantic`
  - Usada em schemas e validação de dados/configurações em partes do projeto.
- `rich`
  - Interface visual da CLI/TUI com tabelas, painéis e mensagens formatadas.
- `pytest`
  - Framework de testes.

### API e serviços
- `fastapi`
  - API HTTP do projeto.
- `uvicorn`
  - Recomendado para servir a API FastAPI, embora normalmente apareça mais em execução do que em imports.

### Dashboard e visualização
- `streamlit`
  - Dashboard interativo.
- `plotly`
  - Gráficos e visualizações para dashboard/análise.

### Machine Learning e modelagem
- `scikit-learn`
  - Modelos, pipelines, métricas, preprocessamento e utilidades de ML.
- `joblib`
  - Persistência de artefatos de modelo.
- `transformers`
  - NLP/sentimento/tópicos em módulos específicos.

### Otimização e automação
- `optuna`
  - Otimização de hiperparâmetros.
- `schedule`
  - Agendamento simples de tarefas.

### Monitoramento e integrações
- `psutil`
  - Métricas de sistema/monitoramento.
- `ccxt`
  - Integração com exchanges em módulos mais avançados.

## 2. Dependências já listadas

### Em `requirements.txt`
- `pandas`
- `numpy`
- `requests`
- `sqlalchemy`
- `pydantic`
- `rich`
- `pytest`

### Em `requirements-full.txt`
- tudo de `requirements.txt`
- `fastapi`
- `uvicorn`
- `scikit-learn`
- `joblib`
- `streamlit`
- `plotly`
- `transformers`
- `schedule`
- `psutil`
- `optuna`
- `ccxt`

## 3. Dependências faltantes

Com os arquivos atuais `requirements.txt` e `requirements-full.txt`, não há faltas relevantes para o repositório auditado.

### Situação prática
- Para a V1 principal, `requirements.txt` cobre o núcleo operacional.
- Para o workspace completo, `requirements-full.txt` cobre as bibliotecas externas detectadas.

### Observação
- `uvicorn` não apareceu como import explícito no código analisado, mas é apropriado no ambiente completo por ser o servidor natural da API FastAPI.
- `alphascope_rust` apareceu em imports, mas não deve entrar em `requirements` como dependência PyPI sem confirmar o processo de build local. Parece componente interno/extensão do projeto.

## 4. Dependências declaradas mas não usadas

### Em `requirements.txt`
Não há dependências claramente ociosas. Todas têm uso no núcleo da V1 ou nos testes.

### Em `requirements-full.txt`
A única dependência que pode ser classificada como “de suporte operacional” e não como import direto é:
- `uvicorn`
  - Não foi detectada em imports, mas faz sentido como dependência de execução da API.

Ou seja, não há excesso problemático. O arquivo completo está coerente com o escopo do repositório.

## 5. Dependências recomendadas

Estas não são obrigatórias para o estado atual, mas melhorariam bastante a qualidade do projeto.

### Configuração e ambiente
- `python-dotenv`
  - Simplifica o carregamento de `.env` e reduz código manual de configuração.
- `pydantic-settings`
  - Boa opção se quiser evoluir a camada de settings com validação mais robusta.

### Qualidade de código
- `ruff`
  - Linter/formatter rápido e moderno.
- `mypy`
  - Verificação estática de tipos.
- `pytest-cov`
  - Cobertura de testes.
- `types-requests`
  - Tipagem adicional para `requests`.

### CLI e UX
- `plotext`
  - Gráficos diretamente no terminal; útil para equity curve e métricas sem dashboard.
- `textual`
  - Se quiser evoluir a CLI para uma TUI mais rica no futuro.

### API e integração
- `httpx`
  - Cliente HTTP moderno para testes e integrações.
- `orjson`
  - Serialização JSON mais rápida para API, se desempenho virar prioridade.

## 6. Requirements final recomendado

### `requirements.txt` recomendado para a V1
```txt
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
rich>=13.0.0
pytest>=8.0.0
```

### `requirements-full.txt` recomendado para o repositório completo
```txt
-r requirements.txt
fastapi>=0.110.0
uvicorn>=0.27.0
scikit-learn>=1.4.0
joblib>=1.3.0
streamlit>=1.30.0
plotly>=5.18.0
transformers>=4.37.0
schedule>=1.2.0
psutil>=5.9.0
optuna>=3.5.0
ccxt>=4.2.0
```

## 7. Conclusão

A estrutura de dependências do AlphaScope está coerente após a separação entre:
- ambiente mínimo da V1 em `requirements.txt`
- ambiente completo do repositório em `requirements-full.txt`

Isso é uma boa prática porque:
- mantém a V1 leve
- evita instalar stack de API/dashboard/ML quando não necessário
- preserva a capacidade de rodar o repositório completo
