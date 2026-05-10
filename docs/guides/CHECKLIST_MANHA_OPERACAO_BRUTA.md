# Checklist da manhã para operação bruta do AlphaScope

Este guia reúne a sequência que você pode rodar antes de sair para trabalhar, já considerando operação real, monitoramento e Telegram.

Use sempre no PowerShell dentro de `D:\AlphaScope` com o venv ativo.

## 1. Preparação inicial

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
```

## 2. Validação rápida obrigatória

```powershell
python -m alphascope.cli doctor --json
python -m alphascope.cli show-trader-mode
python -m alphascope.cli verify-exchange-credentials --mode live
python -m alphascope.cli sync-account
```

Objetivo desta etapa:
- confirmar que o ambiente está íntegro
- confirmar que o modo de operação está correto
- validar credenciais live da Binance
- sincronizar saldo/conta antes de qualquer ciclo operacional

## 3. Aquecer dados de mercado

```powershell
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli explain-ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 20
```

## 4. Validar o multiagente antes da operação

```powershell
python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
python -m alphascope.cli multi-agent-runtime-status --json
```

## 5. Validar Telegram antes de deixar a máquina rodando

Confirme no `.env`:

```env
TELEGRAM_ENABLED=true
ENABLE_TELEGRAM_ALERTS=true
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Depois rode:

```powershell
python -m alphascope.cli test-telegram-alert
```

## 6. Conferência final antes de ligar tudo

```powershell
python -m alphascope.cli runtime-status
python -m alphascope.cli show-data --type account --limit 20
python -m alphascope.cli show-data --type open-positions --limit 20
```

## 7. Script PowerShell pronto para a manhã

Eu deixei um script pronto em:

`D:\AlphaScope\scripts\iniciar_alphascope_manha.ps1`

Ele consegue:
- rodar a checklist completa
- abrir API, dashboard e Telegram em novas janelas
- opcionalmente subir o daemon
- opcionalmente iniciar a produção real

### 7.1 Rodar só a checklist e subir os serviços auxiliares

```powershell
.\scripts\iniciar_alphascope_manha.ps1
```

### 7.2 Rodar checklist + subir daemon contínuo

```powershell
.\scripts\iniciar_alphascope_manha.ps1 -StartDaemon
```

### 7.3 Comando final para produção real

Este é o comando final para rodar em produção real com checklist, API, dashboard, Telegram e entrada live:

```powershell
.\scripts\iniciar_alphascope_manha.ps1 -ProductionReal
```

### 7.4 Comando final mais bruto ainda: produção real + daemon contínuo

```powershell
.\scripts\iniciar_alphascope_manha.ps1 -ProductionReal -StartDaemon
```

### 7.5 Comando único já preparado para seus 10 pares

Esse script já sobe tudo em produção real com daemon e usa:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- XRPUSDT
- LINKUSDT
- BNBUSDT
- ADAUSDT
- DOGEUSDT
- AVAXUSDT
- TRXUSDT

```powershell
.\scripts\iniciar_alphascope_real_10_pares.ps1
```

Se quiser pular o preflight e forçar a subida direta:

```powershell
.\scripts\iniciar_alphascope_real_10_pares.ps1 -SkipPreflight
```

## 8. Comando alternativo para deixar o motor operacional contínuo no ar

Se quiser deixar o runtime contínuo rodando em outra janela antes da execução live, use este comando separado:

```powershell
Start-Process powershell -ArgumentList '-NoExit','-Command','cd D:\AlphaScope; .\venv\Scripts\Activate.ps1; python -m alphascope.cli start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500'
```

Depois acompanhe com:

```powershell
python -m alphascope.cli status-daemon
python -m alphascope.cli runtime-status
python -m alphascope.cli show-data --type live-trades --limit 20
python -m alphascope.cli multi-agent-runtime-status --json
```

## 9. Rollback imediato se algo ficar estranho

```powershell
python -m alphascope.cli emergency-close --interval 1h
python -m alphascope.cli stop-daemon
python -m alphascope.cli reset-live-state
```

## 10. Sequência resumida para todo começo de manhã

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli doctor --json
python -m alphascope.cli verify-exchange-credentials --mode live
python -m alphascope.cli sync-account
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli run-multi-agent --symbol BTCUSDT --interval 1h
python -m alphascope.cli test-telegram-alert
python -m alphascope.cli runtime-status
```

## 11. Observação prática

O comando final da seção 7 inicia operação real. Só rode depois que a checklist acima estiver limpa e sem erros.
