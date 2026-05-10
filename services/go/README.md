# AlphaScope Go Services

Esta pasta concentra serviços auxiliares em Go para infraestrutura concorrente e I/O intensivo.

Papel recomendado do Go no AlphaScope:
- workers de ingestão desacoplados
- adapters de exchange e conectores externos
- consumidores/produtores de eventos
- serviços curtos, resilientes e simples de subir em container

O que NÃO deve ficar aqui:
- lógica principal de estratégia
- regras centrais de ranking
- orquestração de trading já consolidada no core Python

Serviços atuais:
- `ingestion_service/` → scaffold para worker HTTP de ingestão
- `exchange_service/` → scaffold para adapter HTTP de exchange
- `scheduler_worker/` → scaffold para worker de heartbeat/scheduler

Contratos mínimos esperados para qualquer serviço Go promovido a produção:
- endpoint `/healthz`
- endpoint `/readyz`
- configuração por variáveis de ambiente
- logs estruturados
- shutdown gracioso
- documentação de integração com o core Python

Validação sugerida quando a toolchain Go estiver disponível:
```bash
cd services/go
go test ./...
go vet ./...
```
