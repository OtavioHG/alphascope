# AlphaScope Como Iniciar o Projeto

Este documento mostra como iniciar o AlphaScope em dois modos:

- modo V1 enxuto
- modo completo do workspace, com API e dashboard

## 1. Pré-requisitos

- Python 3.11+
- `pip`
- Windows PowerShell ou terminal equivalente

## 2. Criar ambiente virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3. Instalar dependências

### Modo V1

Instala apenas o necessário para o núcleo do AlphaScope:

```bash
pip install -r requirements.txt
pip install -e .
```

### Modo completo

Instala dependências da V1 mais API, dashboard, ML e módulos expandidos:

```bash
pip install -r requirements-full.txt
pip install -e .
```

## 4. Configurar ambiente

Crie o arquivo `.env` a partir do exemplo:

```bash
copy .env.example .env
```

Se quiser, ajuste depois:
- símbolos monitorados
- caminho do banco SQLite
- janelas dos indicadores
- parâmetros de backtest e paper trading

## 5. Validar instalação

### Ver ajuda da CLI

```bash
python -m alphascope.cli --help
```

### Rodar testes

```bash
pytest
```

## 6. Iniciar a V1 pela CLI

### Ingestão de mercado

```bash
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

### Gerar features

```bash
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Gerar ranking

```bash
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Rodar backtest

```bash
python -m alphascope.cli backtest --symbol BTCUSDT --interval 1h
```

### Rodar paper trading

```bash
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Rodar pipeline completo

```bash
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

## 7. Visualizar dados já salvos

### Candles

```bash
python -m alphascope.cli show-data --type candles --symbol BTCUSDT --interval 1h --limit 20
```

### Features

```bash
python -m alphascope.cli show-data --type features --symbol BTCUSDT --interval 1h --limit 20
```

### Ranking

```bash
python -m alphascope.cli show-data --type ranking --interval 1h
```

### Snapshot da carteira

```bash
python -m alphascope.cli show-data --type snapshot
```

## 8. Iniciar a API

Para o workspace completo, a API usa FastAPI.

Com as dependências completas instaladas, inicie com:

```bash
uvicorn alphascope.api.api_server:app --reload
```

Se necessário, defina o path de import explicitamente:

```bash
$env:PYTHONPATH=\"src\"
uvicorn alphascope.api.api_server:app --reload
```

Observação:
- a API faz parte do workspace completo
- ela não é necessária para a execução básica da V1 por CLI

## 9. Iniciar o dashboard

O workspace também contém dashboard e frontend.

### Dashboard Python

Se o dashboard baseado em Python estiver sendo usado:

```bash
streamlit run src/alphascope/dashboard/app.py
```

### Frontend web

Existe também uma pasta `frontend/` com stack TypeScript.

Para iniciar:

```bash
cd frontend
npm install
npm run dev
```

Observação:
- o frontend é separado da V1 da CLI
- para usá-lo, você precisa ter Node.js instalado

## 10. Banco e arquivos gerados

Por padrão, o projeto cria e usa:

- banco SQLite em `data/alphascope.db`
- logs em `logs/`

As tabelas principais da V1 são:

- `market_candles`
- `technical_features`
- `asset_rankings`
- `paper_trades`
- `portfolio_snapshots`

## 11. Fluxo recomendado

Para começar rápido:

1. criar e ativar ambiente virtual
2. instalar `requirements.txt`
3. copiar `.env.example` para `.env`
4. rodar `python -m alphascope.cli --help`
5. rodar `ingest-market`
6. rodar `build-features`
7. rodar `rank-assets`
8. rodar `backtest`
9. rodar `paper-trade`

Se quiser tudo em sequência:

```bash
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

## 12. Resumo rápido

### Início mínimo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
python -m alphascope.cli --help
```

### Pipeline V1

```bash
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
```

### API completa

```bash
pip install -r requirements-full.txt
uvicorn alphascope.api.api_server:app --reload
```

### Dashboard completo

```bash
streamlit run src/alphascope/dashboard/app.py
```
