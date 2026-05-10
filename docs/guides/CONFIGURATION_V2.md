# Configuração V2

- Ambientes: `config/env/*.env`
- Estratégias: `config/strategies/*.json`
- Risco: `config/risk/*.json`
- Telegram: `config/telegram/*.json`

## Seleção de perfil

```bash
set RISK_PROFILE=aggressive
python -m alphascope.cli platform-status
```

## Variáveis críticas

- `DATABASE_URL`
- `REDIS_URL`
- `LIVE_TRADING_MODE`
- `LIVE_TRADING_ENABLED`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `RISK_PROFILE`
