# AlphaScope Platform V2

## Estrutura proposta

```text
AlphaScope/
  config/
    env/
    risk/
    strategies/
    telegram/
  deployment/
    docker/
    monitoring/
  docs/
    architecture/
    guides/
  frontend/
    app/
  src/alphascope/
    api/
    alerts/
    automation/
    dashboard/
    execution/
    monitoring/
    platform/
    storage/
    textual_app.py
    control_center_cli.py
    telegram_bot.py
  tests/
    integration/
    unit/
```

## Arquitetura

- `platform/` concentra regras novas de entrada, saída, risco, execução e configuração centralizada.
- `storage/` permanece como camada de persistência, agora com `audit_events` e `ranking_cycles`.
- `api/platform_api.py` expõe o backend FastAPI v2 para painel web, observabilidade e automação remota.
- `control_center_cli.py` entrega a CLI/TUI operacional com Typer, Rich e Textual.
- `telegram_bot.py` oferece controle remoto, consulta de status e trilha de auditoria para ações manuais.
- `frontend/app/page.tsx` é o ponto inicial do painel React/Next.js.

## Fluxo principal

1. Ingestão e features alimentam ranking e sinais.
2. `AdvancedSignalEngine` calcula score técnico, tendência, volume, volatilidade, momentum e regime.
3. `AdvancedRiskEngine` autoriza ou bloqueia alocação conforme perfil, drawdown e exposição.
4. `ExecutionSafetyGuard` normaliza quantidade/preço e bloqueia ordens duplicadas, abaixo do mínimo ou em cooldown.
5. `ExitDecisionEngine` produz trailing stop, parcial, break-even e fechamentos por degradação.
6. `AuditService` registra alterações feitas por CLI, Telegram e API.

## Ordem recomendada de implementação

1. Configuração centralizada e storage de auditoria.
2. Núcleo quant de entrada/saída/risco.
3. Integração com execução real e sincronização de ordens.
4. CLI/TUI e automação remota via Telegram.
5. API FastAPI e painel web.
6. Observabilidade, deploy e hardening operacional.

## Próximos incrementos

- Migrar ranking legado para usar os novos scores no pipeline principal.
- Substituir `Streamlit` por frontend React totalmente conectado à API v2.
- Trocar fallback in-memory de Redis/Postgres por clients reais em toda a stack.
- Adicionar Alembic com migrations versionadas para PostgreSQL e SQLite.
