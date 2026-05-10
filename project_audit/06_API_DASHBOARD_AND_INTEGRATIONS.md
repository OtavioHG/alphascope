# 06_API_DASHBOARD_AND_INTEGRATIONS - AlphaScope Audit

## 1. FastAPI (Backend API)
- **Localização:** `api/api_server.py`.
- **Status:** Implementado (Funcional para endpoints de leitura e saúde).
- **Rotas:**
    - `GET /health`: Healthcheck.
    - `GET /metrics`: Métricas de runtime.
    - `GET /ranking/latest`: Ranking mais recente gerado.
    - `GET /portfolio/status`: Status atual da carteira simulada.
    - `GET /trades/recent`: Lista de trades simulados recentes.
    - `POST /pipeline/run`: Disparo manual do pipeline (via API).
- **Segurança:** Módulo `security/` implementa autenticação via API Key e Rate Limiting.

## 2. Streamlit (Dashboard de Monitoramento)
- **Localização:** `src/alphascope/dashboard/app.py`.
- **Status:** Implementado (Interface principal de visualização).
- **Páginas:**
    - `Overview`: Resumo de ativos, sinais e saúde.
    - `Market Analysis`: Visualização de candles e indicadores.
    - `Asset Ranking`: Detalhamento do ranking híbrido.
    - `News Sentiment`: Dashboard de análise de sentimento e impacto.
    - `Trading Monitor`: Performance do paper trading (Equity Curve, PnL).
    - `System Monitor`: Status do Daemon, Scheduler e Heartbeat.

## 3. Integrações Externas
- **Binance:** OHLCV e execução via `data_sources/binance_client.py`.
- **CoinGecko/CoinMarketCap:** Metadados de mercado e rankings.
- **CryptoCompare:** Dados históricos complementares.
- **GDELT:** API de notícias globais.
- **Telegram:** Notificações de runtime via `alerts/telegram_notifier.py`.
- **Discord:** Suporte a Webhooks implementado em `alerts/discord.py`.

## 4. Frontend Next.js
- **Status:** Parcial (Apenas scaffold inicial em `frontend/`).
- **Observação:** Atualmente não é a forma recomendada de interagir com o projeto, servindo como base para evolução futura.

## 5. Serviços em Go
- **Status:** Parcial (Scaffolds em `services/go/`).
- **Módulos:** `ingestion_service`, `exchange_service`, `scheduler_worker`.
- **Observação:** No estágio atual, o núcleo funcional do projeto é 100% Python.
