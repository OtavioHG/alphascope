# AlphaScope Visão Geral das Linguagens

No projeto AlphaScope, cada linguagem e formato cobre uma parte diferente do sistema.

## Python

É a linguagem principal do projeto.

Faz quase tudo do core:
- CLI
- ingestão da Binance
- storage com SQLAlchemy
- cálculo de features
- ranking
- backtest
- paper trading
- API com FastAPI
- dashboard em partes Python
- automação
- testes com pytest

Em resumo: Python é o motor do AlphaScope.

## TypeScript

Aparece em `frontend/`.

Está sendo usado para a interface web moderna:
- `next.config.ts`
- `tsconfig.json`
- provável app em Next.js/React dentro de `frontend/app`

Em resumo: TypeScript cuida do frontend web.

## SQL

Aparece em `sql/`.

Serve para:
- schema
- views
- consultas analíticas
- queries de features

Em resumo: SQL organiza e consulta dados analíticos fora da camada ORM.

## Rust

Aparece em `src/alphascope/rust/` com `.rs`.

Provavelmente foi incluído para:
- bindings nativos
- aceleração de partes computacionais
- experimentação de performance

Em resumo: Rust é um módulo de performance e integração nativa, não o core atual.

## Go

Aparece em `services/go/`.

Indica serviços auxiliares separados, possivelmente para:
- microsserviços
- workers
- serviços de alta concorrência
- componentes futuros de infraestrutura

Em resumo: Go parece ser suporte de serviços externos, não a base principal hoje.

## R

Aparece em `research/R/`.

Serve para pesquisa quantitativa e estatística:
- análises exploratórias
- validação de modelos
- experimentos acadêmicos

Em resumo: R está na área de research.

## Julia

Aparece em `research/julia/`.

Provavelmente usada para:
- pesquisa quantitativa
- simulações numéricas
- prototipagem de modelos matemáticos

Em resumo: Julia está no bloco de pesquisa e experimentação.

## Shell

Aparece em `scripts/*.sh`.

Serve para automação operacional:
- backup
- start de serviços
- setup de ambiente em Linux e macOS

## PowerShell

Aparece em `scripts/*.ps1`.

Serve para automação no Windows:
- setup de ambiente
- comandos operacionais locais

## TOML

Aparece em `pyproject.toml` e também no frontend.

Serve para configuração de projeto:
- empacotamento Python
- pytest
- build
- metadados

## Markdown

Aparece em `README.md`, docs e auditorias.

Serve para documentação:
- uso do projeto
- arquitetura
- dependências
- instruções operacionais

## TXT

Aparece em `docs/`.

Serve para relatórios e entregas consolidadas:
- índices
- relatórios técnicos
- snapshots textuais da evolução do projeto

## YAML

Aparece em arquivos de deployment e monitoring.

Serve para configuração de infraestrutura:
- deploy
- monitoramento
- pipelines
- serviços

## ENV

Aparece em `.env.example`.

Serve para configuração de ambiente:
- paths
- parâmetros
- segredos e configs ajustáveis

## Resumo prático

Hoje, na prática:

- Python: núcleo real do AlphaScope
- TypeScript: frontend web
- SQL: camada analítica
- Rust: performance e experimentos
- Go: serviços auxiliares
- R e Julia: pesquisa quantitativa
- Shell e PowerShell: automação operacional
- TOML, YAML e ENV: configuração
- Markdown e TXT: documentação
