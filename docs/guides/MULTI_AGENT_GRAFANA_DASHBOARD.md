# Multi-Agent Grafana and Monitoring Guide

Objetivo
- fornecer um painel operacional para o runtime multiagente em Prometheus/Grafana e dashboard web

Fontes de observabilidade
- HTTP API: /metrics
- healthcheck geral: /healthz
- healthcheck multiagente: /healthz/multi-agent
- dashboard Streamlit: página "Multi-Agent Monitor"
- logs: logs/metrics.jsonl, logs/alphascope.log, data/runtime/multi_agent_*.json

Principais métricas multiagente
- multi_agent_final_score{symbol,timeframe,decision}
- multi_agent_execution_action{symbol,timeframe,action}
- multi_agent_agent_confidence{symbol,timeframe,agent,signal}
- multi_agent_agent_score{symbol,timeframe,agent}
- multi_agent_scheduler_jobs{backend}
- multi_agent_heartbeat_up{backend}

Painéis sugeridos no Grafana
1. Supervisor Decision Score
- visual: time series
- query: multi_agent_final_score
- breakdown por symbol e decision

2. Agent Confidence by Agent
- visual: time series ou bar chart
- query: multi_agent_agent_confidence
- group by: agent

3. Agent Score Heatmap
- visual: state timeline ou heatmap
- query: multi_agent_agent_score
- labels: agent, symbol

4. Execution Actions
- visual: stat + table
- query: multi_agent_execution_action
- labels: action

5. Multi-Agent Heartbeat
- visual: stat
- query: multi_agent_heartbeat_up
- alerta quando = 0

6. Scheduler Job Count
- visual: stat
- query: multi_agent_scheduler_jobs

Alertas recomendados
- heartbeat_down: multi_agent_heartbeat_up == 0 por 2 intervalos
- scheduler_missing: multi_agent_scheduler_jobs == 0 em horário de operação
- low_confidence_market: avg by(agent) (multi_agent_agent_confidence{agent="market_intelligence"}) < 0.45
- repeated_hold_bias: contagem excessiva de decisão HOLD com score em faixa estreita
- execution_block_spike: aumento de execution_action com action="block_trade"

Painel web interno
A página "Multi-Agent Monitor" do dashboard mostra:
- última decisão
- último score
- backend de cache
- quantidade de jobs do scheduler
- runtime status bruto
- eventos recentes de auditoria multiagente
- métricas Prometheus recentes do namespace multi_agent_
- heartbeat multiagente

Checklist de integração Prometheus
- expor /metrics via run-platform-api
- configurar scrape no Prometheus para o serviço AlphaScope API
- validar presença das séries multi_agent_*
- criar dashboard Grafana com os seis painéis sugeridos
- configurar alertas para heartbeat e scheduler
