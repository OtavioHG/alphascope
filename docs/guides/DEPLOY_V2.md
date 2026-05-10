# Deploy V2

## VPS

1. Instale Docker e Docker Compose.
2. Configure `config/env/production.env`.
3. Ajuste `DATABASE_URL`, `REDIS_URL`, credenciais Binance e Telegram.
4. Execute `docker compose up -d --build`.
5. Exponha `8010`, `8501`, `9090` e `3000` conforme a necessidade.

## Produção

- Use PostgreSQL gerenciado quando possível.
- Restrinja o endpoint `/audit` e controles remotos por autenticação.
- Faça backup recorrente de banco e `data/runtime/`.
