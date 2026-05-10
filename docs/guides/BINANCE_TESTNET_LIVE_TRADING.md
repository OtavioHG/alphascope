# AlphaScope Live Trading Guide

## Objetivo

Esta camada adiciona `Binance Spot` com `testnet` por padrao, mantendo `paper trading` como caminho de rollback rapido.

## Variaveis principais

```env
BINANCE_API_KEY=
BINANCE_API_SECRET=

LIVE_TRADING_ENABLED=false
LIVE_TRADING_MODE=testnet
LIVE_MARKET_TYPE=spot
LIVE_KILL_SWITCH_ENABLED=true
LIVE_EMERGENCY_STOP=false

MAX_OPEN_TRADES=3
MAX_POSITION_SIZE_PCT=0.02
MAX_DAILY_LOSS_PCT=0.03
MAX_ACCOUNT_EXPOSURE_PCT=0.20
MAX_CONSECUTIVE_LOSSES=3

STOP_LOSS_PCT=0.02
TAKE_PROFIT_PCT=0.04
TRAILING_STOP_PCT=0.01

MIN_CONFIDENCE_SCORE=0.45
MIN_NOTIONAL_USDT=10
ENABLE_TELEGRAM_ALERTS=true
```

## Ativacao da Binance Spot Testnet

1. Crie conta em `https://testnet.binance.vision/`.
2. Gere `API Key` e `Secret`.
3. Preencha `BINANCE_API_KEY` e `BINANCE_API_SECRET`.
4. Mantenha:

```env
LIVE_TRADING_ENABLED=false
LIVE_TRADING_MODE=testnet
LIVE_MARKET_TYPE=spot
```

5. Rode sincronizacao de conta antes de enviar sinais:

```powershell
python -m alphascope.cli sync-account
```

## Fluxo seguro recomendado

```powershell
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli start-live-trading --interval 1h --limit 10
python -m alphascope.cli show-data --type open-positions
python -m alphascope.cli show-data --type account
python -m alphascope.cli show-data --type live-trades
```

## Emergency close

```powershell
python -m alphascope.cli emergency-close --interval 1h
```

## Rollback para paper trading

Voltar para paper trading exige apenas:

```env
LIVE_TRADING_ENABLED=false
LIVE_TRADING_MODE=testnet
LIVE_EMERGENCY_STOP=false
```

Entao execute:

```powershell
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

## Logs gerados

- `logs/live_trading.log`
- `logs/risk_manager.log`
- `logs/order_manager.log`
- `logs/account_manager.log`

Exemplo:

```text
2026-04-03 10:30:01 | INFO | live_trading | symbol=BTCUSDT score=0.812 saldo=1000.0 quantidade=0.2 preço=100.0 pnl=- risco=0.02 motivo=trade_opened
2026-04-03 10:30:01 | INFO | order_manager | symbol=BTCUSDT score=0.812 saldo=1000.0 quantidade=0.2 preço=100.0 pnl=- risco=0.02 motivo=submitted order_id=12345
2026-04-03 10:31:12 | WARNING | risk_manager | symbol=ETHUSDT score=0.410 saldo=- quantidade=- preço=2400.0 pnl=- risco={"signal_score": 0.41, "price": 2400.0, "quantity": null} motivo=signal_score_below_minimum
```

## JSON esperado

`start-live-trading` internamente gera objetos como:

```json
{
  "symbol": "BTCUSDT",
  "status": "opened",
  "score": 0.81,
  "quantity": 0.2,
  "entry_price": 100.0,
  "stop_loss_price": 98.0,
  "take_profit_price": 104.0,
  "trailing_stop_price": 99.0,
  "order_id": 12345,
  "mode": "testnet"
}
```

## Observacoes operacionais

- `LIVE_TRADING_ENABLED=false` continua sendo o padrao.
- `LIVE_TRADING_MODE=testnet` continua sendo o padrao.
- Todas as ordens passam por `RiskManager`.
- Todas as execucoes sao persistidas em SQLite.
- `paper trading` continua disponivel sem migracao de dados.
