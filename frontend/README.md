# AlphaScope Frontend

Esta pasta contém a interface web moderna do AlphaScope baseada em:
- Next.js
- React
- TypeScript

Papel recomendado do frontend:
- control plane web
- observabilidade operacional
- visualização de ranking, risco, portfólio e saúde da plataforma
- consumo da API Python oficial do projeto

Status atual:
- scaffold funcional para evolução
- ainda não substitui oficialmente o dashboard Streamlit
- já possui utilitário de integração com `/healthz`
- preparado para checagem com `typecheck` e `build`

Comandos úteis:
```bash
cd frontend
npm install
npm run typecheck
npm run build
npm run dev
```

Variáveis recomendadas:
```bash
NEXT_PUBLIC_ALPHASCOPE_API_BASE_URL=http://127.0.0.1:8010
```
