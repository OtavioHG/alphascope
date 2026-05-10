# Fase 3 — Telegram modular + Frontend API-driven

Esta fase consolida duas frentes:

1. Telegram organizado por router + handlers
2. frontend Next.js evoluindo para control plane consumindo a API oficial

## 1. Telegram

Arquitetura nova:
- `src/alphascope/alerts/telegram_command_listener.py`
- `src/alphascope/alerts/telegram_router.py`
- `src/alphascope/alerts/telegram_handlers.py`

Objetivo:
- separar parsing e roteamento dos handlers
- manter compatibilidade com a interface pública do listener
- facilitar evolução futura por domínio

Comando de subida:
```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli platform telegram run
```

## 2. Frontend

Páginas entregues:
- `/`
- `/ranking`
- `/risk`
- `/audit`

Dependência principal:
- API oficial em `run-platform-api`

Subida da API:
```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m alphascope.cli platform api run --host 127.0.0.1 --port 8010
```

Subida do frontend:
```powershell
cd D:\AlphaScope\frontend
npm install
npm run check
npm run dev
```

Variável recomendada:
```bash
NEXT_PUBLIC_ALPHASCOPE_API_BASE_URL=http://127.0.0.1:8010
```

## 3. Validação

Python:
```powershell
cd D:\AlphaScope
.\venv\Scripts\Activate.ps1
python -m pytest -q
```

Frontend:
```powershell
cd D:\AlphaScope\frontend
npm run check
```
