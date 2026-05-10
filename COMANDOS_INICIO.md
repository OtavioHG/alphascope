# Comandos AlphaScope

## 1. Entrar no projeto e ativar o ambiente

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
```

## 2. Instalar ou atualizar dependencias

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 3. Validar o ambiente

```powershell
python -m alphascope.cli doctor
python -m alphascope.cli show-trader-mode
```

## 4. Rodar os testes

```powershell
pytest -q
```

## 5. Subir a API / backend

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli run-platform-api --host 127.0.0.1 --port 8010
```

## 6. Subir o frontend

```powershell
cd D:\AlphaScope\frontend
npm install
npm run dev
```

## 7. Rodar pipeline de forma segura

```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli run-pipeline --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli paper-trade --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli runtime-status
```

## 8. Ver ranking e dados salvos

```powershell
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli show-data --type ranking --interval 1h --limit 20
python -m alphascope.cli show-data --type snapshot --limit 20
```

## 9. Ingestao e features manualmente

```powershell
python -m alphascope.cli ingest-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --limit 500
python -m alphascope.cli build-features --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli rank-assets --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

## 10. Backtest

```powershell
python -m alphascope.cli backtest --symbol BTCUSDT --interval 1h
```

## 11. Runtime continuo

```powershell
python -m alphascope.cli run-continuous --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 60 --timeframe 1h --limit 500
```

## 12. Comandos de runtime

```powershell
python -m alphascope.cli runtime-status
python -m alphascope.cli show-jobs
python -m alphascope.cli status-daemon
```

## 13. Cuidado com live trading

O projeto atualmente pode estar em modo live dependendo do `.env`.

Antes de usar qualquer comando de operacao real, confira:

```powershell
python -m alphascope.cli show-trader-mode
```

Evite rodar este comando sem revisar o `.env`:

```powershell
python -m alphascope.cli start-live-trading --interval 1h --limit 20
```

