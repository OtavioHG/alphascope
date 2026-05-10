# Multi-Agent Controlled Rollout Plan

Objetivo
- liberar o AlphaScope multiagente para produção com risco controlado
- definir critérios explícitos de avanço, contenção e rollback

## Fase 0 — Pré-go-live técnico
Objetivo:
- confirmar integridade do sistema antes de qualquer execução recorrente

Checklist de entrada
- testes multiagente aprovados
- testes de runtime aprovados
- `/healthz`, `/healthz/multi-agent` e `/metrics` respondendo
- Telegram multiagente funcional
- backtest multiagente concluído
- treino local validado ou fallback aceito

Critério para sair da fase
- zero falhas bloqueantes

## Fase 1 — Soak test em paper/testnet
Duração sugerida
- mínimo 1 hora contínua
- ideal 1 ciclo operacional completo do timeframe principal

Escopo
- 1 a 2 símbolos líquidos, ex.: BTCUSDT e ETHUSDT
- scheduler multiagente ativo
- monitoramento contínuo por logs, API e Telegram

Comandos base
```powershell
python -m alphascope.cli schedule-live-multi-agent --symbols BTCUSDT,ETHUSDT --interval 1h --cycle-seconds 300 --duration-seconds 3600
python -m alphascope.cli multi-agent-runtime-status --json
```

Critérios de aprovação
- heartbeat estável
- scheduler com jobs válidos
- sem exceções críticas recorrentes
- persistência completa em audit/trade_consensus/agent_decisions
- `/metrics` com séries multi_agent_*
- Telegram multiagente estável

Rollback da fase
- parar scheduler
- revisar logs
- corrigir causa raiz
- repetir fase 1

## Fase 2 — Live controlado com capital mínimo
Objetivo
- primeira validação com capital real mínimo aceitável

Escopo sugerido
- apenas BTCUSDT
- volume mínimo operacional
- `MAX_OPEN_TRADES=1`
- threshold de confiança conservador

Comando base
```powershell
python -m alphascope.cli run-live-multi-agent --symbol BTCUSDT --interval 1h
```

Critérios de aprovação
- ordem roteada corretamente
- sync-account consistente
- auditoria íntegra
- Telegram de decisão e estado operacional corretos
- sem inconsistência entre posição local e exchange

Critérios de rollback imediato
- falha de execução na exchange
- divergência entre posição persistida e conta real
- erro recorrente em sync-account
- perda anormal ou bloqueios repetidos sem causa compreendida

Ações de rollback
```powershell
python -m alphascope.cli emergency-close --symbol BTCUSDT --interval 1h
python -m alphascope.cli sync-account
python -m alphascope.cli reset-live-state
```

## Fase 3 — Expansão limitada de símbolos
Objetivo
- aumentar cobertura mantendo exposição reduzida

Escopo sugerido
- BTCUSDT + ETHUSDT
- depois adicionar no máximo 1 símbolo por janela de observação

Critérios para expandir
- nenhuma falha crítica na fase anterior
- observabilidade íntegra
- drawdown controlado
- consenso multiagente estável

Critérios para congelar expansão
- aumento de bloqueios de exchange
- queda relevante da qualidade do consenso
- falhas em métricas/heartbeat/Telegram

## Fase 4 — Operação live supervisionada
Objetivo
- entrar em regime estável com acompanhamento operacional regular

Rotina mínima diária
- verificar `/healthz/multi-agent`
- verificar `/metrics`
- verificar `multi_agent_runtime_status.json`
- revisar últimas decisões via `/ma_last` e `show-consensus-history`
- revisar logs críticos

## Critérios de rollback global
Executar rollback operacional se qualquer item abaixo ocorrer:
- healthcheck multiagente degradado de forma persistente
- métricas multi_agent_* desaparecem
- scheduler/heartbeat deixam de atualizar
- Telegram operacional falha durante janela ativa
- erro de exchange recorrente não explicado
- account sync inconsistente
- auditoria incompleta ou persistência corrompida

## Procedimento de rollback global
1. parar novas entradas
2. fechar exposições abertas se necessário
3. sincronizar conta
4. resetar estado live persistido
5. revisar logs, métricas e auditoria
6. retornar para fase anterior

Comandos principais
```powershell
python -m alphascope.cli emergency-close --interval 1h
python -m alphascope.cli sync-account
python -m alphascope.cli reset-live-state
python -m alphascope.cli runtime-status
```

## Recomendação final
- avanço sempre faseado
- nunca escalar símbolos e capital ao mesmo tempo
- qualquer anomalia operacional relevante deve devolver o rollout para a fase anterior
