# Relatorio Completo do Projeto AlphaScope

## 1. Visao Geral

O AlphaScope e uma plataforma quantitativa modular para analise de mercado cripto, descoberta de sinais, ranking de ativos, simulacao operacional e suporte a modelos de IA. O projeto foi estruturado para funcionar como uma linha completa de processamento de dados: coletar informacoes de mercado e noticias, transformar esses dados em features, gerar rankings e sinais, testar estrategias e executar operacao simulada com monitoramento.

Na pratica, o projeto hoje esta em um estado hibrido:

- existe um nucleo Python funcional para ingestao, features, ranking, backtest, paper trading, API e runtime operacional;
- existe uma camada ampliada de ML, NLP, automacao, eventos, dashboards e governance;
- existem modulos ainda em formato de scaffold, principalmente no frontend Next.js e nos servicos em Go.

Ou seja, o AlphaScope nao e apenas um script de trading. Ele ja esta organizado como uma plataforma, com varias camadas separadas por responsabilidade.

## 2. Objetivo do Projeto

O objetivo principal do AlphaScope e transformar dados brutos de mercado em decisao operacional estruturada.

O fluxo esperado do sistema e:

1. coletar candles, volumes, market cap, sentimento e noticias;
2. persistir os dados em armazenamento local e estruturas auxiliares;
3. calcular indicadores tecnicos e features derivadas;
4. montar datasets de treino e inferencia;
5. gerar previsoes com heuristicas e/ou modelos de machine learning;
6. ranquear ativos com maior probabilidade de oportunidade;
7. validar a logica com backtest;
8. executar paper trading ou simulacao operacional;
9. expor status por CLI, API, dashboard e alertas.

Esse desenho faz sentido porque separa o problema em etapas independentes e testaveis.

## 3. Arquitetura Geral

O repositorio esta dividido em blocos principais:

- `src/alphascope/`: nucleo do sistema em Python;
- `tests/`: suite de testes automatizados;
- `frontend/`: frontend em Next.js, hoje ainda inicial;
- `services/go/`: servicos auxiliares em Go, hoje como scaffold;
- `deployment/`: Docker, compose e monitoramento;
- `docs/`: guias, relatorios e historico do projeto;
- `data/`: dados brutos, processados, runtime e snapshots;
- `models/`: artefatos de modelos treinados;
- `research/`: material experimental em R e Julia.

O centro operacional do projeto e a CLI Python, que orquestra quase todas as funcoes.

## 4. Como o Projeto Funciona Hoje

### 4.1 Entrada principal

O ponto de entrada principal e [`src/alphascope/cli.py`](D:\AlphaScope\src\alphascope\cli.py), registrado no `pyproject.toml` como comando `alphascope`.

Ao iniciar, a CLI:

- configura logging;
- carrega configuracoes do `.env`;
- inicializa o banco SQLite;
- cria os objetos principais de pipeline, repositorio e agregadores;
- despacha o comando para uma das tres areas:
  - mercado e pipeline;
  - runtime operacional;
  - dados, ML e NLP.

Isso foi escolhido porque a CLI permite operar o sistema inteiro de forma simples, sem depender inicialmente de frontend.

### 4.2 Configuracao

O arquivo [`src/alphascope/config/settings.py`](D:\AlphaScope\src\alphascope\config\settings.py) centraliza configuracoes do sistema.

Ele define:

- caminhos de dados, logs e modelos;
- URLs de APIs;
- limites de requisicao;
- simbolos e intervalos padrao;
- parametros de features tecnicas;
- limiares de ranking;
- configuracoes de paper trading;
- ciclos de automacao e runtime;
- chaves e toggles de integracao.

Isso e usado para evitar valores espalhados no codigo e permitir que o comportamento mude por ambiente sem editar modulos internos.

### 4.3 Persistencia

O armazenamento principal atual e SQLite, inicializado em [`src/alphascope/storage/database.py`](D:\AlphaScope\src\alphascope\storage\database.py).

A camada [`src/alphascope/storage/repositories.py`](D:\AlphaScope\src\alphascope\storage\repositories.py) salva e le:

- candles de mercado;
- features tecnicas;
- rankings;
- trades simulados;
- snapshots de portfolio.

SQLite foi usado porque:

- e simples de configurar;
- nao exige servidor externo;
- atende bem prototipagem local;
- facilita testes e desenvolvimento rapido.

Ao mesmo tempo, o projeto ja tem uma camada mais avancada em `infrastructure/` e `storage/models/production.py`, sinalizando preparacao para evoluir para um modelo mais robusto.

## 5. Fluxo Funcional Principal

### 5.1 Ingestao de mercado

O modulo [`src/alphascope/ingestion/market_ingestor.py`](D:\AlphaScope\src\alphascope\ingestion\market_ingestor.py) usa o cliente Binance para buscar candles OHLCV e persisti-los.

Esse passo existe porque qualquer estrategia quantitativa depende de historico confiavel de preco e volume.

### 5.2 Geracao de features

O modulo [`src/alphascope/features/feature_pipeline.py`](D:\AlphaScope\src\alphascope\features\feature_pipeline.py) transforma candles em indicadores tecnicos.

Os principais indicadores configurados incluem:

- medias moveis curta e longa;
- RSI;
- volatilidade;
- volume relativo;
- momentum.

Esses indicadores sao usados porque resumem tendencia, forca, exaustao e variacao do ativo em variaveis numericas mais adequadas para ranking e ML.

### 5.3 Ranking de ativos

O pipeline central em [`src/alphascope/core/pipeline.py`](D:\AlphaScope\src\alphascope\core\pipeline.py) monta uma cross-section com a ultima linha de features de cada ativo e passa isso para o rankeamento.

O ranking pode operar em modos:

- `heuristic`: usa score calculado com base nas features;
- `ml`: incorpora probabilidade de modelo;
- `hybrid` e `hybrid_with_news`: mistura score heuristico, ML e noticias.

Essa escolha e importante porque o projeto nao fica preso a uma abordagem unica. Ele pode operar apenas com regras, apenas com modelo ou com combinacao dos dois.

### 5.4 Backtest

O mesmo pipeline gera sinais a partir de thresholds de score e os envia para o motor de backtest.

O backtest existe para responder a pergunta mais importante da estrategia: a regra gera resultado historico coerente depois de custos?

### 5.5 Paper trading

O modulo [`src/alphascope/execution/paper_trader.py`](D:\AlphaScope\src\alphascope\execution\paper_trader.py) simula compra e venda com:

- capital inicial;
- taxa de corretagem;
- limite de posicoes;
- tamanho percentual de alocacao por trade.

Ele e usado para testar comportamento operacional sem risco financeiro real.

## 6. Pipeline Operacional Expandido

Existe uma segunda camada de automacao mais completa em [`src/alphascope/automation/pipeline.py`](D:\AlphaScope\src\alphascope\automation\pipeline.py).

Esse pipeline expandido executa:

- ingestao de mercado;
- ingestao de noticias;
- atualizacao de features;
- construcao de dataset;
- inferencia de modelos;
- ranking;
- execucao de paper trading;
- geracao de alertas;
- emissao de metricas;
- gravacao de estado de runtime.

Essa camada representa a versao mais proxima de um sistema sempre ligado.

Ela usa componentes adicionais como:

- `EventBus` para eventos internos;
- `MetricsCollector` para metricas;
- `JsonTracer` para rastreabilidade;
- `AlertNotifier` para alertas;
- `FeatureStore` para snapshots;
- repositorios de producao para predicoes e execucao.

## 7. Camada de Dados Externos

O projeto nao depende de uma unica API. Em [`src/alphascope/external_data/aggregator.py`](D:\AlphaScope\src\alphascope\external_data\aggregator.py), o sistema consolida fontes externas de mercado.

As fontes suportadas no estado atual incluem:

- Binance;
- CoinGecko;
- CoinMarketCap;
- CryptoCompare;
- Fear & Greed;
- GDELT para noticias.

Por que isso esta sendo usado:

- Binance: dados de candles e mercado operacional;
- CoinGecko: market cap, ranking e metadados amplos;
- CoinMarketCap: complemento de cota, rank e capitalizacao;
- CryptoCompare: historico e enriquecimento complementar;
- Fear & Greed: contexto de sentimento agregado do mercado;
- GDELT: noticias em volume para alimentar NLP.

A ideia tecnica por tras da agregacao e reduzir dependencia de uma unica fonte e aumentar completude dos snapshots.

## 8. Machine Learning de Mercado

O treino de modelo de mercado esta em [`src/alphascope/ml/train_market_model.py`](D:\AlphaScope\src\alphascope\ml\train_market_model.py).

Hoje o projeto treina e compara pelo menos tres modelos supervisionados:

- Logistic Regression;
- Random Forest;
- Gradient Boosting.

O pipeline:

- constroi dataset supervisionado;
- faz separacao temporal de treino e teste;
- treina varios candidatos;
- compara metricas;
- salva o melhor artefato com `joblib`;
- registra metadados em JSON.

Esses modelos foram escolhidos por motivos praticos:

- Logistic Regression: baseline simples e interpretavel;
- Random Forest: lida bem com nao linearidade e interacoes;
- Gradient Boosting: costuma capturar padroes tabulares com bom desempenho.

O projeto evita depender de um unico modelo sofisticado sem baseline. Isso e uma boa decisao de engenharia.

## 9. NLP e Noticias

O modulo [`src/alphascope/nlp/inference.py`](D:\AlphaScope\src\alphascope\nlp\inference.py) faz scoring de noticias.

Ele combina:

- classificacao de sentimento;
- classificacao de topico;
- extracao de ativo relacionado;
- calculo de impacto;
- opcionalmente um modelo supervisionado salvo para noticias.

As bibliotecas de NLP e transformers sao usadas porque noticia nao chega em formato numerico. O sistema precisa transformar texto em sinais aproveitaveis pelo ranking.

Isso permite que o ranking hibrido incorpore contexto que nao aparece apenas no preco.

## 10. Runtime, Daemon e Monitoramento

O projeto tem uma camada operacional dedicada em [`src/alphascope/cli_runtime.py`](D:\AlphaScope\src\alphascope\cli_runtime.py).

Ela oferece comandos para:

- rodar pipeline continuo;
- agendar jobs;
- iniciar e parar daemon;
- consultar status de runtime;
- executar simulacao live;
- enviar alertas;
- testar Telegram.

O agregador de estado em [`src/alphascope/monitoring/runtime_status.py`](D:\AlphaScope\src\alphascope\monitoring\runtime_status.py) junta:

- status do daemon;
- scheduler;
- heartbeat;
- pipeline continuo;
- simulacao live;
- metricas de runtime;
- ultimo ranking;
- ultimo snapshot de portfolio;
- estado de recuperacao.

Essa camada existe porque projeto quantitativo nao e apenas modelo. Ele precisa ser operavel, observavel e recuperavel.

## 11. API

A API FastAPI fica em [`src/alphascope/api/api_server.py`](D:\AlphaScope\src\alphascope\api\api_server.py).

Ela expoe rotas para:

- `POST /pipeline/run`
- `GET /health`
- `GET /metrics`
- ranking;
- portfolio;
- trades;
- sinais.

FastAPI foi usada porque:

- e rapida para prototipar APIs tipadas;
- integra bem com Pydantic;
- facilita expor servicos para dashboards e integracoes.

Existe tambem protecao por API key e limitacao de taxa em modulos de seguranca, o que mostra preocupacao com endurecimento minimo da superficie HTTP.

## 12. Dashboard e Interface

O projeto possui duas frentes de interface:

- dashboard em Streamlit;
- frontend em Next.js.

### 12.1 Dashboard Streamlit

O arquivo [`src/alphascope/dashboard/app.py`](D:\AlphaScope\src\alphascope\dashboard\app.py) ja implementa um dashboard funcional para:

- visao geral do sistema;
- ranking;
- monitoramento;
- trading;
- noticias;
- status operacional.

Streamlit foi escolhido porque reduz muito o custo de construir um painel interno rapidamente.

### 12.2 Frontend Next.js

O frontend em [`frontend/app/page.tsx`](D:\AlphaScope\frontend\app\page.tsx) ainda esta em estado inicial. Hoje ele exibe apenas uma pagina simples de scaffold.

Isso significa que a camada web moderna ainda nao representa a interface principal do projeto.

## 13. Servicos em Go

Em `services/go/` existem servicos separados para:

- `ingestion_service`;
- `exchange_service`;
- `scheduler_worker`.

No estado atual, esses servicos sao scaffolds pequenos, por exemplo o `ingestion_service` so expõe healthcheck HTTP.

Go esta sendo usado aqui por um motivo arquitetural plausivel:

- processos pequenos;
- baixa latencia;
- facil deploy de workers independentes;
- boa concorrencia para servicos de infraestrutura.

Mas hoje eles ainda nao sao o nucleo funcional do AlphaScope. O centro real continua sendo Python.

## 14. Testes e Qualidade

A pasta `tests/` possui 49 arquivos de teste Python no estado atual do repositorio.

A cobertura declarada inclui:

- ingestao;
- features;
- ranking;
- backtest;
- external data;
- runtime;
- automacao;
- live simulator;
- datasets;
- ML;
- NLP;
- fases evolutivas do projeto.

Isso e importante porque um sistema com muitos modulos so se mantem evolutivo se houver regressao automatizada.

## 15. Dependencias e Por Que Elas Foram Escolhidas

### 15.1 Base Python

Dependencias principais em `requirements.txt`:

- `pandas`: manipulacao tabular e timeseries;
- `numpy`: computacao numerica;
- `requests`: integracao HTTP com APIs;
- `sqlalchemy`: persistencia ORM;
- `pydantic`: validacao de schemas;
- `rich`: interface CLI formatada;
- `pytest`: testes automatizados.

### 15.2 Camada expandida

Dependencias adicionais em `requirements-full.txt`:

- `fastapi` e `uvicorn`: API HTTP;
- `scikit-learn`: ML supervisionado tabular;
- `joblib`: persistencia de modelos;
- `streamlit` e `plotly`: dashboard e visualizacao;
- `transformers`: NLP e modelos de linguagem;
- `schedule`: agendamento simples de jobs;
- `psutil`: metricas e estado de processo;
- `optuna`: otimizacao de parametros;
- `ccxt`: base futura para integracao com exchanges;
- `datasets`: carga e tratamento de datasets externos;
- `pyarrow`: processamento eficiente em Parquet.

### 15.3 Frontend

Em `frontend/package.json`, a stack atual e:

- Next.js 15;
- React 18;
- TypeScript 5.

Essa escolha indica intencao de evoluir para uma interface web mais moderna, separada do backend Python.

## 16. O Que Ja Funciona Bem

Pelo codigo do repositorio, as partes mais concretas e maduras sao:

- CLI centralizada e bem segmentada;
- ingestao de mercado;
- persistencia local;
- calculo de features;
- ranking;
- backtest;
- paper trading;
- construcao de datasets;
- treino e avaliacao de modelos de mercado;
- scoring de noticias;
- pipeline continuo;
- runtime status;
- dashboard Streamlit;
- API FastAPI;
- suite de testes relativamente ampla.

## 17. O Que Ainda Deve Evoluir

Alguns pontos ainda parecem em transicao ou parcialmente implementados:

- frontend Next.js ainda e scaffold;
- servicos em Go ainda sao basicos;
- coexistem modulos de armazenamento antigo e mais avancado, o que sugere fase de migracao;
- ha varias camadas de arquitetura futura como governance, marketplace, evolution, meta-learning e research continuo que parecem mais preparadas estruturalmente do que plenamente operacionais;
- parte da complexidade do projeto ja aponta para uma plataforma multi-servico, mas a operacao real ainda esta bastante concentrada em Python monolitico modular.

Isso nao e necessariamente ruim. Significa que o projeto foi desenhado para crescer, mas ainda esta consolidando algumas frentes.

## 18. Como o Projeto Deve Funcionar no Modelo Ideal

No desenho ideal, o AlphaScope deve operar assim:

1. buscar continuamente dados de mercado e noticias;
2. normalizar e salvar tudo de forma versionada;
3. recalcular features e datasets sem leakage;
4. atualizar modelos ou rodar inferencia com controle de qualidade;
5. gerar ranking consolidado com heuristica, ML e noticias;
6. validar regras com backtests e monitorar degradacao;
7. executar paper trading ou modo live-simulado;
8. expor sinais, metricas e estados por API, dashboard e alertas;
9. permitir futura separacao em servicos menores para escala e resiliencia.

Esse e exatamente o tipo de arquitetura que faz sentido para um laboratorio quantitativo que quer sair de prototipo e virar sistema operacional monitorado.

## 19. Conclusao

O AlphaScope e um projeto amplo, bem acima de um bot simples. Ele ja combina engenharia de dados, analise quantitativa, ML, NLP, automacao operacional, simulacao, observabilidade e interfaces de acesso.

O que esta sendo usado foi escolhido por motivos tecnicos claros:

- Python para velocidade de desenvolvimento e ecossistema de dados;
- pandas/numpy para series temporais e features;
- SQLAlchemy e SQLite para persistencia simples e local;
- scikit-learn para modelos tabulares robustos;
- transformers para extrair sinal de noticias;
- FastAPI para integracao programatica;
- Streamlit para painel interno rapido;
- Next.js para futura interface web mais completa;
- Go para possiveis workers leves e independentes;
- pytest para manter confianca evolutiva.

Em resumo: o AlphaScope hoje funciona como uma plataforma quantitativa modular com nucleo operacional real em Python, enquanto algumas camadas mais avancadas ainda estao amadurecendo para o estado plenamente produtivo.
