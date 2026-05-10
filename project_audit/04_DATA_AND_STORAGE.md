# 04_DATA_AND_STORAGE - AlphaScope Audit

## 1. Fontes de Dados
O AlphaScope integra múltiplas APIs para consolidar uma visão completa do mercado:
- **Binance:** OHLCV (candles), Tickers e Volume.
- **CoinGecko:** Market Cap, Ranking Global e Metadados de Ativos.
- **CoinMarketCap:** Complemento de cotações, rankings e capitalização.
- **CryptoCompare:** Dados históricos e snapshots multi-exchange.
- **Fear & Greed:** Sentimento agregado do mercado de cripto.
- **GDELT:** Notícias globais brutas para processamento NLP.

## 2. Ingestão e Formatos
- **Mercado:** Ingestão de candles via `ingestion/market_ingestor.py` persistindo diretamente em SQLite.
- **Universo:** Consolidação multi-fonte em `external_data/aggregator.py`.
- **Pesquisa:** Gera arquivos Parquet e CSV em `data/processed/` para treinamento de modelos, visando performance.

## 3. Banco de Dados e Tabelas
O sistema utiliza SQLite como banco de dados principal por padrão.

### Principais Tabelas (SQLite):
- **`market_candles`**: Dados OHLCV crus da Binance.
- **`technical_features`**: Indicadores técnicos calculados para cada candle.
- **`asset_rankings`**: Histórico de scores de ativos por ciclo de tempo.
- **`paper_trades`**: Log de ordens simuladas executadas pelo Paper Trader.
- **`portfolio_snapshots`**: Estado da carteira simulada em pontos específicos no tempo.

## 4. Estrutura em `data/`
- **`data/alphascope.db`**: Banco de dados principal.
- **`data/raw/`**: Armazenamento de arquivos brutos das APIs (GDELT, CryptoCompare, Fear & Greed).
- **`data/processed/`**: Datasets versionados, features, rankings e modelos persistidos em JSONL, CSV ou Parquet.
- **`data/runtime/`**: Estado operacional volátil (PID, Heartbeat, Daemon Status).

## 5. Linhagem e Versionamento
- **Módulo `data_management/`**: Implementa um catálogo de dados e linhagem de dados básica para rastrear a origem e transformação dos ativos.
- **Versionamento:** O módulo `dataset_versioning.py` gerencia versões de datasets de treino para garantir que experimentos de ML possam ser replicados.

## 6. Camada de Produção (Implementado vs. Potencial)
- O módulo `infrastructure/postgres_client.py` indica prontidão para PostgreSQL, mas a lógica de migração e repositório (`storage/models/production.py`) aponta para uma transição parcial onde o SQLite ainda é a fonte da verdade para a CLI.
