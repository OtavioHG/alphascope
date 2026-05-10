# Changelog

## 2026-03-22

### AlphaScope V1 base

- estruturacao da V1 em modulos claros para configuracao, core, ingestao, storage, features, ranking, backtest, execution e utils
- implementacao de CLI funcional com `argparse`
- persistencia local com SQLite e SQLAlchemy
- ingestao de candles da Binance com retry e timeout
- pipeline de features tecnicas sem leakage
- ranking de ativos por score simples
- motor de backtest long-only com metricas principais
- paper trading com snapshots e historico de trades
- testes basicos com `pytest`

### Melhoria da interface CLI

- criacao de camada visual em terminal com Rich
- tabelas formatadas para ingestao, features, ranking, trades e universe
- paineis para metricas e snapshots
- mensagens de sucesso, aviso e erro mais legiveis
- adicao do comando `show-data`

### Auditoria e organizacao de dependencias

- revisao dos imports do projeto
- separacao entre dependencias minimas da V1 e dependencias do workspace completo
- criacao de `requirements-full.txt`
- criacao de `DEPENDENCY_AUDIT.md`

### Documentacao adicional

- criacao de `START_PROJECT.md`
- criacao de `LANGUAGES_OVERVIEW.md`
- consolidacao da entrega em documentos `.txt`
- ampliacao do `README.md`

### Camada multi-source de dados externos

- criacao do pacote `external_data`
- suporte a Binance como fonte principal de trading e liquidez
- suporte a CoinGecko Demo API para market cap, rank e metadata
- suporte a CoinMarketCap Free API para quotes e validacao complementar
- normalizacao de simbolos e snapshots em formato unico
- agregacao central com prioridade de fonte principal
- fallback entre provedores
- persistencia local do universo consolidado em `data/market_universe/`
- novos comandos de CLI:
  - `fetch-market-universe`
  - `show-universe`
  - `compare-sources`

### Testes da camada external_data

- testes para normalizacao de simbolos
- testes para snapshot Binance
- testes para snapshot CoinGecko
- testes para snapshot CoinMarketCap
- testes de agregacao com prioridade e fallback
- testes de comparacao entre fontes
- testes de `healthcheck`

### Estado validado

- suite de testes passando
- CLI validada com os novos comandos
- compatibilidade preservada com o pipeline atual
