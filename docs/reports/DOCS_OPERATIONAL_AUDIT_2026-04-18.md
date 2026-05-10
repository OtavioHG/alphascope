# Auditoria da documentação operacional AlphaScope

Data: 2026-04-18
Escopo auditado:
- `README.md`
- `docs/guides/`
- `docs/reports/`
- materiais operacionais relacionados a runtime, Telegram, API, dashboard e modos de operação

## 1. Resumo executivo

A documentação operacional do AlphaScope já cobre boa parte dos fluxos críticos, mas está fragmentada entre guias V1, V2, relatórios de mudança e runbooks específicos. O repositório possui conteúdo suficiente para operar a plataforma, porém ainda não apresenta uma arquitetura documental profissional e estável.

Os principais problemas identificados foram:
- duplicação de conteúdo entre README, guias operacionais, V2 e relatórios
- coexistência de entrypoints atuais e legados sem sinalização uniforme
- mistura de documentação de produto, operação, arquitetura, rollout e histórico técnico
- links absolutos `D:/AlphaScope/...` em larga escala, o que reduz portabilidade
- dashboard/documentação web com mensagem mista: Streamlit funcional + frontend Next.js ainda scaffold
- documentação de Telegram distribuída entre três documentos com escopo sobreposto
- ausência de uma trilha documental clara por persona: operador, desenvolvedor, integrador e SRE

## 2. Mapa documental atual

### 2.1 Entradas principais
- `README.md`
  - funciona como hub geral
  - é muito amplo
  - mistura onboarding, APIs externas, comandos CLI, runtime, Telegram e arquitetura operacional

- `docs/REPORTS_INDEX.md`
  - índice de relatórios e alguns guias
  - hoje também funciona como pseudo-navegação principal
  - contém muitos links absolutos para `D:/AlphaScope/...`

### 2.2 Guias operacionais relevantes

Mais fortes para operação real:
- `docs/guides/MODOS_OPERACIONAIS_ALPHASCOPE.md`
- `docs/guides/OPERATIONAL_RUNTIME_GUIDE.md`
- `docs/guides/COMANDOS_CLI_CATEGORIZADOS.md`
- `docs/TELEGRAM_COMMANDS.md`
- `docs/guides/MULTI_AGENT_OPERATIONAL_RUNBOOK.md`
- `docs/guides/MULTI_AGENT_GRAFANA_DASHBOARD.md`

Guias amplos, mas parcialmente redundantes:
- `docs/guides/ALPHASCOPE_COMPLETE_GUIDE.md`
- `docs/guides/OPERATIONS_SETUP_COMPLETE.md`
- `docs/guides/START_PROJECT.md`

Guias V2 / control plane:
- `docs/guides/CLI_V2.md`
- `docs/guides/WEB_PANEL_V2.md`
- `docs/guides/TELEGRAM_V2.md`
- `docs/guides/USAGE_V2.md`
- `docs/guides/INSTALLATION_V2.md`
- `docs/guides/CONFIGURATION_V2.md`

### 2.3 Relatórios que influenciam operação
- `docs/reports/RELATORIO_REESTRUTURACAO_CLI_TELEGRAM_2026-04-17.md`
- `docs/reports/MULTI_AGENT_PRODUCTION_READINESS_REPORT.md`
- `docs/reports/MULTI_AGENT_ROLLOUT_PLAN.md`
- `docs/reports/DEPENDENCY_AUDIT.md`
- `docs/reports/CHANGELOG.md`

### 2.4 Material de implementação real encontrado no código

Entrypoints atuais e confirmados:
- API: `src/alphascope/api/platform_api.py`
- CLI de plataforma: `src/alphascope/cli_platform.py`
- runtime/status: `src/alphascope/cli_runtime.py`
- dashboard Streamlit: `src/alphascope/dashboard/app.py`
- bot Telegram: `src/alphascope/telegram_bot.py`

Superfície funcional atual confirmada:
- `run-platform-api`
- `run-dashboard`
- `run-telegram-bot`
- `runtime-status`
- `show-trader-mode`
- `verify-exchange-credentials`
- `platform-status`
- `control-center`

## 3. Achados críticos

### 3.1 Fragmentação documental
O conteúdo operacional está correto em vários pontos, mas espalhado demais. Exemplo de tópicos com sobreposição direta:
- modos de operação: README + `MODOS_OPERACIONAIS_ALPHASCOPE.md`
- runtime contínuo: README + `OPERATIONAL_RUNTIME_GUIDE.md` + `COMANDOS_CLI_CATEGORIZADOS.md`
- Telegram: `docs/TELEGRAM_COMMANDS.md` + `docs/guides/TELEGRAM_V2.md` + `MODOS_OPERACIONAIS_ALPHASCOPE.md`
- API/dashboard: README + `WEB_PANEL_V2.md` + `USAGE_V2.md` + `START_PROJECT.md`

Impacto:
- custo alto para descobrir a fonte de verdade
- maior risco de drift entre docs
- onboarding confuso para operação diária

### 3.2 Presença simultânea de fluxos atuais e legados
Há divergência explícita entre docs antigas e entrypoints atuais.

Exemplo relevante:
- documentação atual aponta para `run-platform-api` e `platform_api`
- `docs/guides/START_PROJECT.md` ainda instrui `uvicorn alphascope.api.api_server:app --reload`
- `docs/guides/CLI_V2.md` cita `python -m alphascope.cli run-api`, mas esse comando não foi encontrado no código

Impacto:
- alto risco de operador/dev usar comando obsoleto
- sensação de stack instável

### 3.3 Links absolutos Windows em excesso
Há grande volume de referências do tipo `D:/AlphaScope/...` e `D:\AlphaScope\...` em markdowns, inclusive no README e no índice de relatórios.

Impacto:
- quebra de portabilidade em GitHub, Linux, WSL, containers e docs site
- aparência pouco profissional para documentação de produto

### 3.4 Escopo do dashboard está mal posicionado
O código confirma dashboard Streamlit funcional e relativamente amplo. Ao mesmo tempo:
- `frontend/README.md` declara que o frontend Next.js é apenas scaffold
- `docs/guides/WEB_PANEL_V2.md` fala em evolução recomendada, não em operação atual
- outras docs mencionam “dashboard” sem diferenciar claramente Streamlit operacional vs frontend web futuro

Impacto:
- leitor pode supor que existem duas interfaces de mesmo status
- falta clareza sobre o que está pronto, suportado e roadmap

### 3.5 Telegram sem fonte única de verdade
Estado atual:
- `docs/TELEGRAM_COMMANDS.md` é o material mais operacional e completo
- `docs/guides/TELEGRAM_V2.md` é muito resumido
- `MODOS_OPERACIONAIS_ALPHASCOPE.md` reapresenta parte do setup

Impacto:
- duplicação de comandos
- risco de inconsistência futura em permissões, confirmações e comandos sensíveis

### 3.6 Multi-agent está melhor documentado que o core em alguns aspectos
Os materiais multiagente possuem runbook, checklist, rollout e dashboard/observabilidade bem orientados. Em vários pontos, estão mais próximos de um padrão profissional do que a documentação “core” unificada.

Impacto:
- qualidade desigual entre áreas
- oportunidade clara de usar multi-agent como modelo estrutural da docs operacional principal

## 4. Lacunas críticas

1. Falta uma página “fonte de verdade” para operação de produção
- deveria unificar modos, pré-checks, promoção de ambiente, rollback e incidentes

2. Falta uma página oficial de “superfícies de acesso”
- CLI
- Telegram
- API
- dashboard Streamlit
- control center/TUI
- frontend futuro

3. Falta separação formal entre “atual”, “experimental” e “legado”
- hoje isso está implícito e distribuído

4. Falta documentação profissional de API como referência
- endpoints existem no código e parcialmente em `USAGE_V2.md`
- não há referência consolidada com autenticação, payloads, respostas, erros e exemplos de consumo

5. Falta documentação de runtime orientada a SRE/ops
- arquivos de estado existem
- métricas existem
- healthchecks existem
- mas não há um manual curto de operação, falhas, SLIs/SLOs e troubleshooting padrão

6. Falta política documental de links e naming
- excesso de caminhos absolutos
- excesso de nomes como `*_V2`, `COMPLETE`, `SETUP_COMPLETE`, `START_PROJECT`
- naming atual não ajuda a inferir prioridade nem status do documento

## 5. Estrutura profissional proposta

Sugestão: reorganizar a docs por domínio e por público, mantendo relatórios históricos em área separada.

```text
docs/
  README.md
  getting-started/
    quickstart.md
    installation.md
    configuration.md
    first-pipeline.md

  operations/
    overview.md
    operating-modes.md
    runtime.md
    runbooks/
      daily-operations.md
      go-live-checklist.md
      rollback-and-containment.md
      incident-response.md
    observability/
      healthchecks.md
      metrics-and-alerts.md
      dashboards.md
    multi-agent/
      runbook.md
      readiness.md
      grafana.md

  interfaces/
    cli.md
    telegram.md
    api.md
    dashboard-streamlit.md
    control-center.md
    frontend-nextjs.md

  reference/
    commands.md
    environment-variables.md
    runtime-files.md
    api-endpoints.md
    telegram-commands.md

  architecture/
    system-overview.md
    control-plane.md
    multi-agent.md

  reports/
    README.md
    audits/
    readiness/
    changelogs/
    legacy/
```

## 6. Mapeamento recomendado do conteúdo atual para a nova estrutura

### Manter e promover para documentação canônica
- `docs/guides/MODOS_OPERACIONAIS_ALPHASCOPE.md`
  - destino sugerido: `docs/operations/operating-modes.md`

- `docs/guides/OPERATIONAL_RUNTIME_GUIDE.md`
  - destino sugerido: `docs/operations/runtime.md`

- `docs/TELEGRAM_COMMANDS.md`
  - destino sugerido: `docs/interfaces/telegram.md`
  - extrair tabela resumida para `docs/reference/telegram-commands.md`

- `docs/guides/MULTI_AGENT_OPERATIONAL_RUNBOOK.md`
  - destino sugerido: `docs/operations/multi-agent/runbook.md`

- `docs/guides/MULTI_AGENT_GRAFANA_DASHBOARD.md`
  - destino sugerido: `docs/operations/observability/dashboards.md` ou `docs/operations/multi-agent/grafana.md`

### Consolidar e reduzir
- `README.md`
  - reduzir para visão geral + quickstart + links para docs canônicas

- `docs/guides/ALPHASCOPE_COMPLETE_GUIDE.md`
- `docs/guides/OPERATIONS_SETUP_COMPLETE.md`
- `docs/guides/START_PROJECT.md`
  - consolidar em:
    - installation
    - configuration
    - quickstart
  - remover redundância operacional

### Reposicionar como docs de roadmap/experimental
- `docs/guides/WEB_PANEL_V2.md`
  - destino sugerido: `docs/interfaces/frontend-nextjs.md`
  - marcar explicitamente como roadmap/scaffold

- `docs/guides/CLI_V2.md`
- `docs/guides/USAGE_V2.md`
- `docs/guides/INSTALLATION_V2.md`
- `docs/guides/CONFIGURATION_V2.md`
  - reaproveitar trechos válidos
  - depois arquivar ou fundir no corpo principal

### Manter em reports/histórico
- `docs/reports/RELATORIO_REESTRUTURACAO_CLI_TELEGRAM_2026-04-17.md`
- `docs/reports/MULTI_AGENT_PRODUCTION_READINESS_REPORT.md`
- `docs/reports/MULTI_AGENT_ROLLOUT_PLAN.md`
- `docs/reports/CHANGELOG.md`

## 7. Estrutura mínima recomendada por documento-chave

### `operations/operating-modes.md`
Deve conter:
- objetivo de cada modo: paper, testnet, live, live-simulated, daemon
- variáveis mínimas por modo
- comandos oficiais por modo
- critérios de promoção entre modos
- bloqueios de go-live
- rollback mínimo

### `interfaces/telegram.md`
Deve conter:
- arquitetura do bot
- pré-requisitos e env
- start/stop/teste
- comandos por categoria: leitura, risco, execução, admin, multi-agent
- comandos sensíveis e confirmação
- limitações e trilha de auditoria

### `interfaces/api.md`
Deve conter:
- como iniciar a API oficial
- endpoints suportados
- payloads e respostas
- códigos de erro
- autenticação atual e futura
- endpoints de observabilidade
- exemplos curl

### `interfaces/dashboard-streamlit.md`
Deve conter:
- escopo suportado hoje
- como iniciar
- páginas disponíveis
- dependências opcionais
- ações acionáveis existentes na sidebar
- limitações

### `operations/runtime.md`
Deve conter:
- componentes do runtime
- ciclos
- arquivos em `data/runtime/`
- daemon, scheduler, heartbeat
- healthchecks e métricas
- troubleshooting

## 8. Prioridades de execução

### Prioridade 1 — higiene crítica
- substituir links absolutos por links relativos
- marcar docs legadas/experimentais
- remover referências a `api_server` como padrão operacional
- corrigir referência a `run-api` em `CLI_V2.md`

### Prioridade 2 — fonte de verdade
- transformar `MODOS_OPERACIONAIS_ALPHASCOPE.md`, `OPERATIONAL_RUNTIME_GUIDE.md` e `TELEGRAM_COMMANDS.md` em núcleo canônico
- reduzir README para hub enxuto
- criar índice principal de docs por persona e domínio

### Prioridade 3 — profissionalização completa
- criar docs de API de referência
- separar claramente dashboard Streamlit vs frontend Next.js
- mover relatórios e legados para camadas históricas
- formalizar status documental: current / experimental / legacy

## 9. Recomendação final

A base documental do AlphaScope já é rica o suficiente para virar um conjunto profissional sem reescrever tudo. O melhor caminho não é produzir mais documentos, e sim:
- consolidar os existentes
- eleger fontes oficiais por tema
- arquivar o que é histórico
- diferenciar claramente o que está pronto, o que é opcional e o que ainda é scaffold

O maior ganho imediato virá de três movimentos:
1. limpar links e referências legadas
2. centralizar operação em `operations/`
3. centralizar superfícies de uso em `interfaces/`
