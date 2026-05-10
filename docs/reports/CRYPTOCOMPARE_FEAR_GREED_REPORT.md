# Relatorio Completo das Mudancas Recentes

## Objetivo da entrega
Foi adicionada ao AlphaScope uma nova camada de dados de mercado e sentimento com duas fontes extras:

- `CryptoCompare`
- `Fear & Greed Index`

A implementacao foi feita de forma compativel com a arquitetura atual, sem quebrar o pipeline existente.

## O que foi implementado

### 1. Novo client CryptoCompare
Arquivo: [cryptocompare_client.py](D:/AlphaScope/src/alphascope/data_sources/cryptocompare_client.py)

Foi criado um client dedicado para a API publica do CryptoCompare com suporte a:
- historico horario via `histohour`
- historico diario via `histoday`
- snapshot de mercado multi-asset via `pricemultifull`

Capacidades implementadas:
- retries automaticos
- timeout configuravel
- tratamento de erro amigavel
- logging
- normalizacao do retorno para o schema interno do AlphaScope

Campos produzidos:
- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `symbol`
- `interval`
- `source`

No snapshot:
- `price`
- `volume_24h`
- `market_cap`
- `supply`

### 2. Novo client Fear & Greed
Arquivo: [fear_greed_client.py](D:/AlphaScope/src/alphascope/data_sources/fear_greed_client.py)

Foi criado um client para a API publica da Alternative.me com suporte ao endpoint `/fng/`.

Capacidades implementadas:
- coleta de serie historica recente
- retries automaticos
- timeout configuravel
- parsing e normalizacao do payload

Campos produzidos:
- `timestamp`
- `fear_greed_value`
- `fear_greed_label`

### 3. Export dos novos clients
Arquivo: [__init__.py](D:/AlphaScope/src/alphascope/data_sources/__init__.py)

Os novos clients passaram a fazer parte da camada oficial de `data_sources`:
- `CryptoCompareMarketDataClient`
- `FearGreedIndexClient`

### 4. Integracao com o dataset de mercado
Arquivo: [market_dataset_builder.py](D:/AlphaScope/src/alphascope/datasets/market_dataset_builder.py)

O `MarketDatasetBuilder` foi expandido para usar as novas fontes.

#### CryptoCompare
Agora o builder:
- tenta carregar historico complementar por simbolo
- salva os arquivos brutos em `data/raw/market/cryptocompare/`
- incorpora metadata de snapshot no dataset final

Novas colunas adicionadas:
- `cryptocompare_market_cap`
- `cryptocompare_supply`

#### Fear & Greed
Agora o builder:
- carrega a serie do indice
- salva os arquivos brutos em `data/raw/market/fear_greed/`
- faz merge temporal com o dataset por `timestamp` usando o valor mais recente disponivel ate aquele ponto

Novas colunas adicionadas:
- `fear_greed_value`
- `fear_greed_label`

#### Resultado
As novas colunas passam a ficar disponiveis para:
- feature engineering
- treino da IA de mercado
- analises futuras de regime de mercado

### 5. Ajuste do ranking com sentimento global
Arquivo: [scorer.py](D:/AlphaScope/src/alphascope/ranking/scorer.py)

Foi criada a funcao:
- `adjust_score_with_market_sentiment()`

Comportamento implementado:
- `Extreme Fear`: aumenta levemente o score, favorecendo compras
- `Fear`: pequeno ajuste positivo
- `Greed`: pequeno ajuste negativo
- `Extreme Greed`: reducao maior do score

Esse ajuste e contrarian e e aplicado apos a composicao principal do score.

Nova coluna produzida:
- `market_sentiment_adjustment`

### 6. Configuracao do projeto
Arquivo: [settings.py](D:/AlphaScope/src/alphascope/config/settings.py)

Foram adicionadas novas variaveis e diretorios automaticos.

Novas URLs e flags:
- `CRYPTOCOMPARE_BASE_URL`
- `ENABLE_CRYPTOCOMPARE`
- `FEAR_GREED_API`
- `ENABLE_FEAR_GREED`

Novas propriedades:
- `cryptocompare_api_enabled`
- `fear_greed_api_enabled`
- `cryptocompare_raw_dir`
- `fear_greed_raw_dir`

Tambem foi incluido no status operacional das APIs:
- `cryptocompare`
- `fear_greed`

### 7. Novos comandos CLI
Arquivo: [cli.py](D:/AlphaScope/src/alphascope/cli.py)

Foram adicionados dois comandos novos:

#### `fetch-cryptocompare-history`
Exemplo:
```bash
python -m alphascope.cli fetch-cryptocompare-history --symbol BTC --interval 1h --limit 500
```

Funcao:
- coleta OHLCV do CryptoCompare
- exporta em Parquet/CSV
- salva em `data/raw/market/cryptocompare/`

#### `fetch-fear-greed`
Exemplo:
```bash
python -m alphascope.cli fetch-fear-greed --limit 30
```

Funcao:
- coleta o indice Fear & Greed
- exporta em Parquet/CSV
- salva em `data/raw/market/fear_greed/`

### 8. Ajuste de export para Parquet com fallback
Arquivo: [parquet_utils.py](D:/AlphaScope/src/alphascope/datasets/parquet_utils.py)

Foi adicionado fallback seguro:
- se `pyarrow` nao estiver disponivel, a exportacao cai automaticamente para CSV

Isso evita quebra operacional em ambientes parciais.

### 9. Atualizacao de ambiente
Arquivos:
- [.env.example](D:/AlphaScope/.env.example)
- [.env](D:/AlphaScope/.env)

Foram adicionadas:
```env
CRYPTOCOMPARE_BASE_URL=https://min-api.cryptocompare.com
ENABLE_CRYPTOCOMPARE=true
FEAR_GREED_API=https://api.alternative.me/fng/
ENABLE_FEAR_GREED=true
```

### 10. Atualizacao da documentacao
Arquivo: [README.md](D:/AlphaScope/README.md)

Foram documentados:
- o que e o CryptoCompare
- o que e o Fear & Greed
- como habilitar no `.env`
- onde os arquivos brutos sao salvos
- como usar os novos comandos CLI
- como essas fontes entram no dataset e no ranking

### 11. Testes adicionados
Arquivo: [test_market_sentiment_sources.py](D:/AlphaScope/tests/test_market_sentiment_sources.py)

Cobertura nova:
- normalizacao do client CryptoCompare
- normalizacao do client Fear & Greed
- integracao no `MarketDatasetBuilder`
- ajuste do ranking com sentimento global

## Impacto funcional no projeto

Com essas mudancas, o AlphaScope agora consegue:
- puxar historico complementar do CryptoCompare
- enriquecer o dataset de treino com market cap e supply adicionais
- incorporar o Fear & Greed como feature de mercado
- ajustar o ranking com base no sentimento macro do mercado
- persistir dados brutos dessas fontes em estrutura organizada
- operar tudo via CLI

## Validacao executada
Foram executados com sucesso:
- `python -m compileall src\alphascope`
- `pytest`
- `python -m alphascope.cli --help`

Resultado dos testes:
- `25 passed`
- `2 skipped`

Os `skipped` continuam sendo os testes de Parquet quando `pyarrow` nao esta instalado no ambiente.

## Validacao pratica final em ambiente real

Depois da implementacao, foi feita uma validacao funcional com chamadas reais de API.

### 1. CryptoCompare
Comando executado:

```bash
python -m alphascope.cli fetch-cryptocompare-history --symbol BTC --interval 1h --limit 5
```

Resultado observado:
- historico coletado com sucesso
- arquivos gerados em:
  - [btc_1h.parquet](D:/AlphaScope/data/raw/market/cryptocompare/btc_1h.parquet)
  - [btc_1h.csv](D:/AlphaScope/data/raw/market/cryptocompare/btc_1h.csv)

### 2. Fear & Greed
Comando executado:

```bash
python -m alphascope.cli fetch-fear-greed --limit 5
```

Resultado observado:
- serie coletada com sucesso
- arquivos gerados em:
  - [fear_greed_latest.parquet](D:/AlphaScope/data/raw/market/fear_greed/fear_greed_latest.parquet)
  - [fear_greed_latest.csv](D:/AlphaScope/data/raw/market/fear_greed/fear_greed_latest.csv)

### 3. Build do dataset de mercado com as novas features
Comando executado:

```bash
python -m alphascope.cli build-market-dataset --symbols BTCUSDT --interval 1h
```

Resultado observado:
- dataset final gerado com sucesso em:
  - [market_training_dataset.parquet](D:/AlphaScope/data/processed/market_training_dataset.parquet)
- total de linhas geradas: `480`

Colunas confirmadas no dataset final:
- `fear_greed_value`
- `fear_greed_label`
- `cryptocompare_market_cap`
- `cryptocompare_supply`

Amostra validada:
- `symbol`: `BTCUSDT`
- `fear_greed_value`: `14`
- `fear_greed_label`: `Extreme Fear`
- `cryptocompare_market_cap`: `1.373561e+12`
- `cryptocompare_supply`: `20003043.0`

## Correcao adicional realizada

Durante a validacao pratica foi identificado um bug real no `MarketDatasetBuilder`.

### Problema
Os merges temporais entre:
- features tecnicas
- candles
- Fear & Greed

estavam falhando por incompatibilidade de tipo/resolucao em `timestamp`.

### Correcao aplicada
Foi adicionada padronizacao explicita de timestamps para:
- `datetime64[ns]`

antes dos merges e do `merge_asof`.

### Resultado da correcao
Depois do ajuste:
- o `build-market-dataset` passou a funcionar corretamente
- as novas features foram incorporadas ao dataset final
- o pipeline de enriquecimento ficou operacional de ponta a ponta

## Resumo final
As mudancas desta etapa adicionaram duas novas fontes estrategicas ao AlphaScope:
- `CryptoCompare` para historico e enriquecimento de dados de mercado
- `Fear & Greed` para sinal macro de sentimento

Essas integracoes ja estao conectadas ao:
- dataset builder
- ranking
- CLI
- documentacao
- testes

E agora tambem foram validadas com:
- chamadas reais de API
- persistencia em Parquet
- geracao real do dataset final enriquecido
