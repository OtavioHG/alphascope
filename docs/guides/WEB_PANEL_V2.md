# Web Panel V2

- Backend: FastAPI em `src/alphascope/api/platform_api.py`
- Frontend: Next.js em `frontend/app/page.tsx`
- Dados principais: dashboard, ranking, histórico, risco, auditoria

## Evolução recomendada

1. Conectar o frontend aos endpoints `/dashboard`, `/ranking` e `/history`.
2. Adicionar autenticação multiusuário.
3. Criar telas administrativas para permissões e configuração remota.
4. Incluir charts reais de equity curve e drawdown.
