# Telegram Commands

O listener Telegram transforma o bot em um centro de controle do AlphaScope. Ele consulta `getUpdates`, responde no mesmo chat configurado e roda em paralelo com `run-continuous`.

## Como ativar

No `.env`:

```env
TELEGRAM_ENABLED=true
ENABLE_TELEGRAM_ALERTS=true
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_CHAT_ID=seu_chat_id
REQUEST_TIMEOUT=5
REQUEST_RETRIES=3
```

Depois execute:

```bash
python -m alphascope.cli run-continuous --symbols BTCUSDT,ETHUSDT,SOLUSDT
```

## Comandos

### Operacionais

- `/start`
- `/help`
- `/ping`
- `/status`
- `/positions`
- `/ranking`
- `/profit`
- `/portfolio`
- `/apis`
- `/restart`

Exemplo:

```text
/status
```

Resposta típica:

```text
AlphaScope Status
APP_ENV: production
Mode: paper
Open trades: 1
Open positions: 1
Monitored coins: 3
Last ranking: BTCUSDT score=0.9100
Last cycle: 2026-04-11T10:00:00+00:00
Telegram: enabled
APIs: 5/6 enabled
```

### Alertas

- `/stopalerts`
- `/startalerts`

`/stopalerts` desabilita temporariamente os envios de alerta do pipeline sem derrubar o listener de comandos.

### Modo

- `/mode`
- `/setmode paper`
- `/setmode simulation`
- `/setmode live confirm`

`simulation` mapeia para o modo seguro testnet do runtime atual.

### Universo de moedas

- `/symbols`
- `/addsymbol BTCUSDT`
- `/removesymbol DOGEUSDT`

As alteracoes atualizam o runtime e persistem em `SYMBOLS` no `.env`.

### Risco

- `/maxtrades`
- `/setmaxtrades 3`
- `/risk`
- `/setrisk conservative`
- `/setrisk moderate`
- `/setrisk aggressive confirm`

Exemplo:

```text
/risk
```

Resposta típica:

```text
Risk Settings
MAX_POSITION_SIZE_PCT: 2.00%
MAX_ACCOUNT_EXPOSURE_PCT: 10.00%
MAX_DAILY_LOSS_PCT: 2.00%
STOP_LOSS_PCT: 1.50%
TAKE_PROFIT_PCT: 3.00%
TRAILING_STOP_PCT: 1.00%
```

### Trades manuais

- `/buy DOGEUSDT`
- `/sell DOGEUSDT`
- `/sellall confirm`

Validacoes aplicadas:

- simbolo precisa ser valido e monitorado
- compra respeita `MAX_OPEN_TRADES`
- `/sellall` exige confirmacao

### Administrativos

- `/restart`

Reinicia o estado interno do listener, limpando cache de `offset`, confirmacoes pendentes e ids processados.

## Observacoes

- O listener responde apenas ao `TELEGRAM_CHAT_ID` configurado.
- Mensagens longas sao quebradas automaticamente antes do envio.
- Falhas de API do Telegram usam retry com timeout e nao derrubam o AlphaScope.
- Mudancas de modo, risco, max trades e simbolos sao aplicadas em runtime e gravadas no `.env`.
