# Modos Operacionais AlphaScope

Este guia resume como colocar o AlphaScope em cada modo de operação de forma segura e previsível.

## 1. Modo paper

Objetivo:
- validar pipeline, ranking, paper trader, API, dashboard e Telegram sem enviar ordens reais.

Configuração mínima no `.env`:

```env
LIVE_TRADING_ENABLED=false
LIVE_TRADING_MODE=paper
LIVE_ALLOW_LIVE_MODE=false
ENABLE_TELEGRAM_ALERTS=false
TELEGRAM_ENABLED=false
```

Comandos principais:

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli doctor
python -m alphascope.cli show-trader-mode
pytest -q
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli runtime-status
```

Quando usar:
- validação diária
- treinamento operacional
- testes antes de qualquer mudança em live

---

## 2. Modo testnet

Objetivo:
- validar integração de exchange em ambiente de teste.

Configuração mínima no `.env`:

```env
LIVE_TRADING_ENABLED=true
LIVE_TRADING_MODE=testnet
LIVE_ALLOW_LIVE_MODE=false
LIVE_ALLOWED_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT
BINANCE_API_KEY=seu_testnet_key
BINANCE_API_SECRET=seu_testnet_secret
```

Comandos principais:

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli doctor
python -m alphascope.cli show-trader-mode
python -m alphascope.cli verify-exchange-credentials --mode testnet
python -m alphascope.cli runtime-status
```

Observação:
- no runtime/Telegram existe o alias `simulation`, mas o valor persistido em `LIVE_TRADING_MODE` deve ser `testnet`.

---

## 3. Modo live real

Objetivo:
- operar com exchange real.

Configuração mínima no `.env`:

```env
LIVE_TRADING_ENABLED=true
LIVE_TRADING_MODE=live
LIVE_ALLOW_LIVE_MODE=true
LIVE_REQUIRE_EXPLICIT_CONFIRMATION=true
LIVE_ALLOWED_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT
BINANCE_API_KEY=sua_live_key
BINANCE_API_SECRET=sua_live_secret
ENABLE_TELEGRAM_ALERTS=true
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_CHAT_ID=seu_chat_id
```

Pré-check obrigatório:

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli doctor
python -m alphascope.cli show-trader-mode
python -m alphascope.cli verify-exchange-credentials --mode live
pytest -q
```

Regras operacionais:
- nunca promover direto de código novo para live sem passar em paper e testnet
- manter `LIVE_ALLOWED_SYMBOLS` coerente com os símbolos realmente operados
- validar Telegram antes de abrir sessão real
- revisar risco antes de ativar qualquer rotina contínua

---

## 4. Modo live simulated

Objetivo:
- testar ciclo de execução com comportamento parecido com live, sem ordem real.

Configuração relacionada:

```env
ENABLE_LIVE_SIMULATED=true
```

Comando:

```powershell
python -m alphascope.cli run-live-simulated
```

Uso recomendado:
- smoke test operacional
- depuração de runtime e monitoramento

---

## 5. Modo daemon / contínuo

Objetivo:
- manter scheduler, heartbeat e runtime monitorados continuamente.

Configuração típica:

```env
ENABLE_SCHEDULER=true
ENABLE_CONTINUOUS_PIPELINE=true
CYCLE_INTERVAL_SECONDS=300
HEARTBEAT_INTERVAL_SECONDS=30
MAX_CONSECUTIVE_ERRORS=5
RETRY_BACKOFF_SECONDS=10
```

Comandos:

```powershell
python -m alphascope.cli start-daemon
python -m alphascope.cli status-daemon
python -m alphascope.cli runtime-status
python -m alphascope.cli show-jobs
python -m alphascope.cli stop-daemon
```

---

## 6. API de plataforma

Comando oficial atual:

```powershell
python -m alphascope.cli run-platform-api --host 127.0.0.1 --port 8010
```

Endpoint esperado:
- `http://127.0.0.1:8010/healthz`

Observação:
- o entrypoint oficial é `platform_api`; evitar usar documentação antiga baseada em `api_server`.

---

## 7. Dashboard

Comando oficial atual:

```powershell
python -m alphascope.cli run-dashboard --host 127.0.0.1 --port 8501
```

Acesso esperado:
- `http://127.0.0.1:8501`

---

## 8. Telegram

Arquitetura atual:
- listener principal com router + handlers por domínio
- entrada operacional pelo comando canônico `platform telegram run`

Configuração mínima:

```env
ENABLE_TELEGRAM_ALERTS=true
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_CHAT_ID=seu_chat_id
TELEGRAM_POLL_SECONDS=1
```

Comando:

```powershell
python -m alphascope.cli run-telegram-bot
```

Teste rápido:

```powershell
python -m alphascope.cli run-telegram-bot --once
```

Comandos úteis no bot:
- `/start`
- `/help`
- `/status`
- `/ranking`
- `/positions`
- `/risk`
- `/mode`
- `/ma_status`
- `/ma_last`

---

## 9. Perfis recomendados

Sugestão de promoção operacional:
1. `paper`
2. `testnet`
3. `live_simulated`
4. `live`

Nunca pular diretamente para live quando houver:
- alteração de CLI
- alteração de Telegram
- alteração de regras de risco
- alteração de runtime multiagente

---

## 10. Checklist de segurança antes do live

- `doctor` sem erros críticos
- `show-trader-mode` confirmando live
- `verify-exchange-credentials --mode live` aprovado
- `pytest -q` passando
- Telegram validado
- `LIVE_ALLOWED_SYMBOLS` revisado
- risco revisado
- histórico recente de paper/testnet validado
