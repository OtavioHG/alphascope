# Testes do AlphaScope

Esta pasta contem a suite de testes do projeto.

## Cobertura atual

- ingestao de mercado
- calculo de features
- ranking de ativos
- backtest
- camada `external_data`

## Camada `external_data`

Os testes dessa camada validam:

- normalizacao de simbolos
- parsing de pares Binance
- snapshots normalizados de Binance
- snapshots normalizados de CoinGecko
- snapshots normalizados de CoinMarketCap
- agregacao com fonte principal e fallback
- comparacao entre fontes
- healthcheck dos provedores

## Estrategia

- os testes usam dados mockados
- nao dependem de chamadas reais para APIs externas
- evitam efeitos colaterais permanentes no banco principal
- persistencia temporaria e validada localmente no workspace

## Execucao

```bash
pytest
```
