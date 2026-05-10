# 07_GAPS_RISKS_AND_TECH_DEBT - AlphaScope Audit

## 1. Inconsistências e Gaps
- **Go Scaffolds:** Os diretórios em `services/go/` contêm scaffolds mínimos de healthcheck e HTTP, mas não possuem a lógica operacional real implementada para substituir os módulos Python equivalentes.
- **PostgreSQL vs. SQLite:** Existe duplicidade de modelos (`infrastructure/db/models.py` vs. `storage/models/production.py`) e repositórios. Embora o Postgres seja suportado, o SQLite é a via de fato. Isso pode gerar inconsistências em migrações de esquema.
- **Execução Real:** O módulo `execution/live_execution.py` existe estruturalmente, mas a integração com ordens reais de exchange via CCXT (mencionado em dependências) não é o fluxo principal testado pela CLI, que foca pesadamente em Paper Trading simulado.

## 2. Dívidas Técnicas
- **Persistência Volátil:** Grande parte do estado de runtime (`data/runtime/`) e de pesquisa (`data/processed/`) é persistida em arquivos JSON/JSONL/CSV. Para escala de produção, isso deveria migrar para um Redis (para runtime) ou um Feature Store mais robusto (como Hopsworks ou Feast).
- **Testes de Integração Operacional:** Os testes atuais são extensos para unidades e pipelines isolados, mas faltam testes de estresse para o Daemon rodando por longos períodos em ambiente instável (falhas de API/Internet).

## 3. Riscos Operacionais
- **Dependência de APIs Gratuitas:** O uso de APIs como GDELT e camadas gratuitas de CoinGecko pode gerar limitação de taxa (*Rate Limiting*) que o sistema trata com retries, mas pode degradar a performance do ranking híbrido.
- **Heartbeat Stale:** O sistema de monitoramento detecta se o processo morreu através do heartbeat, mas a recuperação automática (*Self-Healing*) ainda é básica.

## 4. Priorização de Correções
1.  **Sincronização de Esquemas:** Unificar os modelos de banco de dados para evitar divergência entre as versões local e de produção.
2.  **Robustez do Daemon:** Implementar lógica de reinicialização automática para o processo Daemon em caso de falha crítica (não apenas logar o erro).
3.  **Cleanup de Legados:** Remover ou marcar claramente os diretórios `data/processed/test_phase*` que parecem ser resíduos de fases de desenvolvimento anteriores.
