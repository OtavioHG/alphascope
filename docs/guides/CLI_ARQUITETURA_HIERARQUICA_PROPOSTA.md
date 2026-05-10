# Auditoria da CLI atual do AlphaScope e arquitetura hierárquica proposta

## Escopo auditado

Arquivos analisados:
- `src/alphascope/cli.py`
- `src/alphascope/cli_market.py`
- `src/alphascope/cli_runtime.py`
- `src/alphascope/cli_data.py`
- `src/alphascope/cli_platform.py`
- `src/alphascope/cli_multi_agent.py`
- `src/alphascope/cli_registry.py`
- `docs/guides/COMANDOS_CLI_CATEGORIZADOS.md`
- `pyproject.toml`

## Diagnóstico da CLI atual

A CLI atual é funcional, mas estruturalmente plana.

Ponto de entrada:
- `pyproject.toml:31-32`
- `src/alphascope/cli.py:21-31`

Hoje o parser principal registra todos os comandos diretamente no primeiro nível:
- mercado/pipeline
- runtime/operação
- dados/ml/news
- plataforma
- multiagente

Isso gera uma CLI com 50+ comandos de topo, sem namespaces hierárquicos.

### Problemas identificados

1. Superfície de comandos plana demais
   - todos os comandos ficam no mesmo nível em `cli.py:24-29`
   - descoberta e ajuda ficam piores conforme a CLI cresce

2. Acoplamento por nome literal
   - `cli.py:84-93` usa whitelist textual em `_command_needs_database`
   - `cli.py:96-168` usa vários conjuntos literais para decidir serviços
   - qualquer novo comando exige alterar múltiplas listas manuais

3. Roteamento central ainda pouco declarativo
   - `cli_registry.py` só fornece dispatch simples
   - não existe metadado único por comando contendo:
     - nome legado
     - namespace novo
     - dependências
     - aliases
     - nível de risco
     - se requer banco/repositorio/pipeline

4. Categorias lógicas existem, mas não existem na UX da CLI
   - os módulos já estão separados (`cli_market.py`, `cli_runtime.py`, etc.)
   - porém a interface pública continua flat

5. Documentação mais organizada que o parser
   - `docs/guides/COMANDOS_CLI_CATEGORIZADOS.md` já agrupa por domínio
   - a CLI real não reflete essa hierarquia

6. Compatibilidade retroativa implícita, não formalizada
   - hoje só existe o formato legado `alphascope <verbo-hifenizado>`
   - não há camada oficial de aliases para uma futura CLI namespaceada

## Inventário atual por domínio

### Mercado e pipeline (`cli_market.py`)
- `ingest-market`
- `build-features`
- `rank-assets`
- `explain-ranking`
- `backtest`
- `paper-trade`
- `run-pipeline`
- `run-loop`
- `show-data`
- `build-universe`
- `fetch-market-universe`
- `show-universe`
- `run-auto-universe`
- `compare-sources`
- `fetch-cryptocompare-history`
- `fetch-fear-greed`

Handlers: `cli_market.py:454-471`

### Dados, ML e notícias (`cli_data.py`)
- `build-training-dataset`
- `build-market-dataset`
- `import-market-dataset`
- `train-market-model`
- `evaluate-market-model`
- `predict-market`
- `ingest-news`
- `build-news-dataset`
- `import-news-dataset`
- `train-news-model`
- `list-external-datasets`
- `show-news-signals`
- `score-news`
- `optimize-strategy`
- `train-production-ai`

Handlers: `cli_data.py:328-344`

### Runtime e operação (`cli_runtime.py`)
- `run-continuous`
- `schedule-jobs`
- `show-jobs`
- `start-daemon`
- `stop-daemon`
- `status-daemon`
- `runtime-status`
- `doctor`
- `check-env`
- `backup-db`
- `verify-exchange-credentials`
- `run-live-simulated`
- `test-telegram-alert`
- `send-runtime-alert`
- `send-portfolio-alert`
- `show-trader-mode`
- `reset-live-state`
- `start-live-trading`
- `sync-account`
- `emergency-close`

Handlers: `cli_runtime.py:531-552`

### Plataforma (`cli_platform.py`)
- `control-center`
- `platform-status`
- `run-platform-api`
- `run-telegram-bot`
- `run-dashboard`

Handlers: `cli_platform.py:93-99`

### Multiagente (`cli_multi_agent.py`)
- `run-multi-agent`
- `run-debate`
- `show-agent-output`
- `show-consensus-history`
- `run-supervisor`
- `show-agent-performance`
- `compare-agent-decisions`
- `run-live-multi-agent`
- `schedule-live-multi-agent`
- `multi-agent-runtime-status`
- `train-multi-agent-models`
- `backtest-multi-agent`

Handlers: `cli_multi_agent.py:245-258`

## Arquitetura hierárquica proposta

Objetivo:
- manter 100% dos comandos legados funcionando
- introduzir uma CLI hierárquica e autoexplicativa
- consolidar metadados de dependência e alias em um registry único

### Forma pública nova

```bash
alphascope market ingest
alphascope market features build
alphascope market rank
alphascope market rank explain
alphascope market backtest
alphascope market paper-trade
alphascope market pipeline run
alphascope market pipeline loop
alphascope market universe build
alphascope market universe fetch
alphascope market universe show
alphascope market universe run-auto
alphascope market sources compare
alphascope market sources fetch-cryptocompare-history
alphascope market sentiment fetch-fear-greed
alphascope data show
alphascope data dataset build-training
alphascope data dataset build-market
alphascope data dataset import-market
alphascope data dataset import-news
alphascope data dataset list-external
alphascope ml market train
alphascope ml market evaluate
alphascope ml market predict
alphascope ml market train-production-ai
alphascope ml strategy optimize
alphascope news ingest
alphascope news dataset build
alphascope news model train
alphascope news score
alphascope news signals show
alphascope runtime continuous run
alphascope runtime jobs schedule
alphascope runtime jobs show
alphascope runtime daemon start
alphascope runtime daemon stop
alphascope runtime daemon status
alphascope runtime status
alphascope runtime doctor
alphascope runtime check-env
alphascope runtime live-simulated run
alphascope runtime trader show-mode
alphascope runtime live start
alphascope runtime live sync-account
alphascope runtime live emergency-close
alphascope runtime state reset-live
alphascope alerts telegram test
alphascope alerts runtime send
alphascope alerts portfolio send
alphascope maintenance db backup
alphascope maintenance exchange verify-credentials
alphascope platform control-center
alphascope platform status
alphascope platform api run
alphascope platform bot telegram run
alphascope platform dashboard run
alphascope agents run
alphascope agents debate run
alphascope agents output show
alphascope agents consensus show-history
alphascope agents supervisor run
alphascope agents performance show
alphascope agents decisions compare
alphascope agents live run
alphascope agents live schedule
alphascope agents runtime status
alphascope agents models train
alphascope agents backtest
```

## Árvore de comandos proposta

```text
alphascope
├── market
│   ├── ingest
│   ├── features
│   │   └── build
│   ├── rank
│   │   ├── run
│   │   └── explain
│   ├── backtest
│   ├── paper-trade
│   ├── pipeline
│   │   ├── run
│   │   └── loop
│   ├── universe
│   │   ├── build
│   │   ├── fetch
│   │   ├── show
│   │   └── run-auto
│   ├── sources
│   │   ├── compare
│   │   └── fetch-cryptocompare-history
│   └── sentiment
│       └── fetch-fear-greed
├── data
│   ├── show
│   └── dataset
│       ├── build-training
│       ├── build-market
│       ├── import-market
│       ├── import-news
│       └── list-external
├── ml
│   ├── market
│   │   ├── train
│   │   ├── evaluate
│   │   ├── predict
│   │   └── train-production-ai
│   └── strategy
│       └── optimize
├── news
│   ├── ingest
│   ├── dataset
│   │   └── build
│   ├── model
│   │   └── train
│   ├── score
│   └── signals
│       └── show
├── runtime
│   ├── continuous
│   │   └── run
│   ├── jobs
│   │   ├── schedule
│   │   └── show
│   ├── daemon
│   │   ├── start
│   │   ├── stop
│   │   └── status
│   ├── live-simulated
│   │   └── run
│   ├── trader
│   │   └── show-mode
│   ├── live
│   │   ├── start
│   │   ├── sync-account
│   │   └── emergency-close
│   ├── state
│   │   └── reset-live
│   ├── doctor
│   ├── check-env
│   └── status
├── alerts
│   ├── telegram
│   │   └── test
│   ├── runtime
│   │   └── send
│   └── portfolio
│       └── send
├── maintenance
│   ├── db
│   │   └── backup
│   └── exchange
│       └── verify-credentials
├── platform
│   ├── control-center
│   ├── status
│   ├── api
│   │   └── run
│   ├── bot
│   │   └── telegram
│   │       └── run
│   └── dashboard
│       └── run
└── agents
    ├── run
    ├── debate
    │   └── run
    ├── output
    │   └── show
    ├── consensus
    │   └── show-history
    ├── supervisor
    │   └── run
    ├── performance
    │   └── show
    ├── decisions
    │   └── compare
    ├── live
    │   ├── run
    │   └── schedule
    ├── runtime
    │   └── status
    ├── models
    │   └── train
    └── backtest
```

## Mapa de compatibilidade retroativa

Cada comando legado continua funcionando como alias do comando novo.

Exemplos:
- `ingest-market` -> `market ingest`
- `build-features` -> `market features build`
- `rank-assets` -> `market rank run`
- `explain-ranking` -> `market rank explain`
- `run-pipeline` -> `market pipeline run`
- `run-loop` -> `market pipeline loop`
- `build-universe` -> `market universe build`
- `fetch-market-universe` -> `market universe fetch`
- `run-auto-universe` -> `market universe run-auto`
- `build-training-dataset` -> `data dataset build-training`
- `build-market-dataset` -> `data dataset build-market`
- `train-market-model` -> `ml market train`
- `evaluate-market-model` -> `ml market evaluate`
- `predict-market` -> `ml market predict`
- `train-production-ai` -> `ml market train-production-ai`
- `ingest-news` -> `news ingest`
- `build-news-dataset` -> `news dataset build`
- `train-news-model` -> `news model train`
- `show-news-signals` -> `news signals show`
- `run-continuous` -> `runtime continuous run`
- `schedule-jobs` -> `runtime jobs schedule`
- `show-jobs` -> `runtime jobs show`
- `start-daemon` -> `runtime daemon start`
- `stop-daemon` -> `runtime daemon stop`
- `status-daemon` -> `runtime daemon status`
- `runtime-status` -> `runtime status`
- `backup-db` -> `maintenance db backup`
- `verify-exchange-credentials` -> `maintenance exchange verify-credentials`
- `run-live-simulated` -> `runtime live-simulated run`
- `test-telegram-alert` -> `alerts telegram test`
- `send-runtime-alert` -> `alerts runtime send`
- `send-portfolio-alert` -> `alerts portfolio send`
- `show-trader-mode` -> `runtime trader show-mode`
- `reset-live-state` -> `runtime state reset-live`
- `start-live-trading` -> `runtime live start`
- `sync-account` -> `runtime live sync-account`
- `emergency-close` -> `runtime live emergency-close`
- `run-platform-api` -> `platform api run`
- `run-telegram-bot` -> `platform bot telegram run`
- `run-dashboard` -> `platform dashboard run`
- `run-multi-agent` -> `agents run`
- `run-debate` -> `agents debate run`
- `show-agent-output` -> `agents output show`
- `show-consensus-history` -> `agents consensus show-history`
- `run-supervisor` -> `agents supervisor run`
- `show-agent-performance` -> `agents performance show`
- `compare-agent-decisions` -> `agents decisions compare`
- `run-live-multi-agent` -> `agents live run`
- `schedule-live-multi-agent` -> `agents live schedule`
- `multi-agent-runtime-status` -> `agents runtime status`
- `train-multi-agent-models` -> `agents models train`
- `backtest-multi-agent` -> `agents backtest`

## Mudanças exatas de código recomendadas

### 1. `src/alphascope/cli_registry.py`

Expandir o registry para virar a fonte única de verdade.

Hoje:
- `CommandSpec` só contém `name`, `help`, `configure`
- não modela aliases, caminho hierárquico nem dependências

Adicionar uma estrutura como:

```python
@dataclass(frozen=True)
class CommandMeta:
    legacy_name: str
    path: tuple[str, ...]          # ex: ("market", "pipeline", "run")
    help: str
    handler: Callable[..., None]
    configure: Callable[[argparse.ArgumentParser], None] | None = None
    aliases: tuple[tuple[str, ...], ...] = ()
    needs_database: bool = True
    needs_repository: bool = True
    needs_pipeline: bool = False
    needs_aggregator: bool = False
    needs_universe_builder: bool = False
    category: str = "general"
    risk_level: str = "normal"
```

Também adicionar helpers:
- `register_command_tree(...)`
- `register_legacy_aliases(...)`
- `resolve_command_meta(args)`
- `build_service_plan(command_meta)`

### 2. `src/alphascope/cli.py`

Refatorar de parser flat para parser em árvore.

Pontos a mudar:
- `build_parser()` em `cli.py:21-31`
- `main()` em `cli.py:34-72`
- `_command_needs_database()` em `cli.py:84-93`
- `_build_services()` em `cli.py:96-168`

Substituir a estratégia atual por:
1. construir parser raiz
2. registrar grupos de primeiro nível (`market`, `data`, `ml`, `news`, `runtime`, `alerts`, `maintenance`, `platform`, `agents`)
3. registrar subárvore por domínio
4. registrar aliases legados invisíveis ou marcados como deprecated
5. resolver metadados do comando a partir do registry
6. instanciar serviços com base em flags declarativas do comando, não em sets literais

Importante: o campo `dest="command_path"` ou equivalente deve armazenar o caminho hierárquico inteiro, e um `resolved_command` final deve apontar para o comando canônico.

### 3. `src/alphascope/cli_market.py`

Refatorar `add_market_subparsers()` (`cli_market.py:26-122`) para registrar subcomandos hierárquicos.

Quebras recomendadas:
- `register_market_commands(root_subparsers)`
- `register_market_pipeline_commands(...)`
- `register_market_universe_commands(...)`
- `register_market_sources_commands(...)`
- `register_market_sentiment_commands(...)`

Preservar handlers já existentes (`cli_market.py:144-470`) e só alterar a camada de registro.

### 4. `src/alphascope/cli_data.py`

Refatorar `add_data_ml_subparsers()` (`cli_data.py:20-97`) porque hoje mistura:
- datasets de mercado
- datasets de notícia
- ML de mercado
- notícias
- otimização

Separar em registradores:
- `register_data_commands(...)`
- `register_ml_commands(...)`
- `register_news_commands(...)`

Os handlers atuais podem continuar, mas o mapeamento deve ser dividido por domínio.

### 5. `src/alphascope/cli_runtime.py`

Refatorar `add_runtime_subparsers()` (`cli_runtime.py:46-130`) para criar subárvores:
- `runtime continuous run`
- `runtime jobs schedule/show`
- `runtime daemon start/stop/status`
- `runtime live start/sync-account/emergency-close`
- `runtime trader show-mode`
- `runtime state reset-live`
- `runtime live-simulated run`

Mover comandos transversais para namespaces próprios:
- alertas -> novo domínio `alerts`
- backup/verificação de exchange -> novo domínio `maintenance`

Os handlers em `cli_runtime.py:138-551` seguem reutilizáveis.

### 6. `src/alphascope/cli_platform.py`

Refatorar `add_platform_subparsers()` (`cli_platform.py:20-33`) para:
- `platform control-center`
- `platform status`
- `platform api run`
- `platform bot telegram run`
- `platform dashboard run`

Sem necessidade de alterar handlers, só o registro.

### 7. `src/alphascope/cli_multi_agent.py`

Refatorar `add_multi_agent_subparsers()` (`cli_multi_agent.py:31-72`) para grupos claros:
- `agents run`
- `agents debate run`
- `agents output show`
- `agents consensus show-history`
- `agents supervisor run`
- `agents performance show`
- `agents decisions compare`
- `agents live run`
- `agents live schedule`
- `agents runtime status`
- `agents models train`
- `agents backtest`

### 8. `docs/guides/COMANDOS_CLI_CATEGORIZADOS.md`

Atualizar documentação para mostrar:
1. nova forma canônica hierárquica
2. comando legado equivalente em cada seção
3. nota explícita de compatibilidade retroativa
4. sessão “comandos legados ainda aceitos”

Arquivo alvo:
- `docs/guides/COMANDOS_CLI_CATEGORIZADOS.md:1-712`

## Estratégia de migração segura

### Fase 1 — Infra declarativa
- expandir `cli_registry.py`
- introduzir `CommandMeta`
- manter parser flat funcionando
- começar a registrar metadados completos

### Fase 2 — Parser híbrido
- adicionar parser hierárquico novo
- manter aliases legados apontando para os mesmos handlers
- help principal passa a mostrar preferencialmente a árvore nova

### Fase 3 — Deprecação suave
- comandos legados continuam aceitos
- imprimir aviso opcional do tipo:
  - `Comando legado detectado. Prefira: alphascope market ingest`
- sem quebra de scripts existentes

### Fase 4 — Consolidação de serviços
- remover sets literais de `cli.py`
- serviços passam a ser instanciados por metadados declarativos do comando

## Recomendações de implementação

1. Não reescrever handlers agora
   - a maior parte do valor está no registry e no parser
   - handlers atuais já estão razoavelmente separados

2. Separar claramente “domínio funcional” de “infra operacional”
   - `runtime` para execução contínua e estado operacional
   - `alerts` para envio de alertas
   - `maintenance` para backup e validações seguras

3. Usar comando canônico interno único
   - qualquer alias legado deve resolver para um `resolved_command` canônico
   - isso simplifica logs, métricas, auditoria e testes

4. Tornar dependências declarativas
   - eliminar lógica por listas textuais em `cli.py`
   - isso reduz regressões ao adicionar novos comandos

5. Adicionar testes de compatibilidade
   - parsing do comando novo
   - parsing do comando legado
   - ambos resolvendo para o mesmo handler e mesmo plano de serviços

## Conclusão

A CLI atual já possui uma boa separação interna por módulos, mas expõe uma UX pública plana e escalável apenas até certo ponto. A melhor evolução é migrar para uma arquitetura hierárquica namespaceada, mantendo 100% de compatibilidade retroativa via aliases legados resolvidos por um registry declarativo central.

A principal refatoração deve ocorrer em:
- `src/alphascope/cli.py`
- `src/alphascope/cli_registry.py`

Os demais módulos precisam principalmente trocar a camada de registro de parser, preservando handlers e argumentos atuais.
