# Phase 3 Telegram + Frontend Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Modularizar o fluxo Telegram do AlphaScope e evoluir o frontend para um control plane mais API-driven.

**Architecture:** O listener Telegram continuará compatível com a interface atual, mas passará a usar router e handlers por domínio. O frontend Next.js ganhará páginas e componentes orientados à API oficial `platform_api`.

**Tech Stack:** Python, FastAPI, Next.js, React, TypeScript, pytest, npm.

---

### Task 1: Criar router e handlers do Telegram
**Objective:** Separar roteamento dos comandos Telegram por domínio sem quebrar a API pública do listener.

**Files:**
- Create: `src/alphascope/alerts/telegram_router.py`
- Create: `src/alphascope/alerts/telegram_handlers.py`
- Modify: `src/alphascope/alerts/telegram_command_listener.py`
- Test: `tests/test_telegram_command_listener.py`

**Verification:**
- `pytest -q tests/test_telegram_command_listener.py`
- comandos `/start`, `/help`, `/status`, `/ma_status`, `/buy`, `/sellall` continuam passando.

### Task 2: Melhorar o frontend com páginas API-driven
**Objective:** Transformar o scaffold atual em um control plane mínimo com páginas separadas e consumo da API.

**Files:**
- Create: `frontend/app/ranking/page.tsx`
- Create: `frontend/app/risk/page.tsx`
- Create: `frontend/app/audit/page.tsx`
- Create: `frontend/components/*.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/lib/alphascope-api.ts`
- Test: `frontend/package.json`

**Verification:**
- `npm run check`

### Task 3: Atualizar documentação da Fase 3
**Objective:** Registrar a nova arquitetura Telegram/frontend e a navegação documental.

**Files:**
- Modify: `docs/README.md`
- Create: `docs/guides/FASE3_TELEGRAM_FRONTEND.md`
- Modify: `docs/guides/MODOS_OPERACIONAIS_ALPHASCOPE.md`

**Verification:**
- revisão manual + links coerentes

### Task 4: Validação final
**Objective:** Garantir regressão zero nas mudanças.

**Files:**
- Test: `tests/`
- Test: `frontend/`

**Verification:**
- `python.exe -m pytest -q`
- `npm run check`
