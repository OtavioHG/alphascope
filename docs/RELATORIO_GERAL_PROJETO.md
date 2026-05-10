# Relatório Geral do Projeto AlphaScope

## 1. Visão Geral
O AlphaScope é uma plataforma quantitativa modular para análise de mercado cripto, geração de sinais, ranking de ativos e execução de operações simuladas. Ele funciona como uma infraestrutura completa que transforma dados brutos (preços, volumes, indicadores e notícias) em decisões operacionais baseadas em dados.

O projeto vai além de um simples bot de trading, estruturando-se como um ecossistema de dados e inteligência de mercado.

## 2. Funcionamento Atual (Arquitetura e Fluxo)
O sistema opera através de uma CLI (Command Line Interface) centralizada que orquestra diversas camadas:

- **Ingestão e Dados Externos:** Consolida dados da Binance, CoinGecko, CoinMarketCap, CryptoCompare e GDELT.
- **Processamento e Features:** Transforma candles brutos em indicadores técnicos (RSI, Médias Móveis, Volatilidade, Momentum) garantindo a integridade dos dados (sem look-ahead bias).
- **Inteligência e Ranking:** Classifica os ativos em três modos principais:
    - **Heurístico:** Baseado em regras fixas e pesos manuais.
    - **Machine Learning (ML):** Utiliza modelos supervisionados (Random Forest, Gradient Boosting) para prever probabilidade de alta.
    - **Híbrido:** Combina indicadores técnicos, predições de IA e score de notícias (NLP).
- **Simulação e Execução:** Realiza backtests (histórico) e paper trading (tempo real simulado) com controle de risco, taxas e limites de posição.
- **Monitoramento e Automação:** Possui um Daemon e Scheduler para operação contínua 24/7, com alertas via Telegram e monitoramento de saúde do sistema.

## 3. Funcionamento Ideal (Visão de Futuro)
O objetivo final é uma plataforma totalmente autônoma e resiliente onde:
- A coleta de dados seja ininterrupta e auto-recuperável.
- Modelos de IA sejam retreinados periodicamente de forma automática (AutoML).
- O monitoramento seja feito via dashboards web modernos (Next.js) e alertas inteligentes.
- Serviços críticos de baixa latência sejam movidos para microsserviços em Go para maior performance.

## 4. Tecnologias Utilizadas e Justificativas
| Tecnologia | Onde é usada? | Por que foi escolhida? |
| :--- | :--- | :--- |
| **Python 3.11+** | Núcleo do sistema. | Linguagem padrão para ciência de dados e rapidez no desenvolvimento. |
| **Pandas / NumPy** | Séries temporais. | Eficiência no cálculo de indicadores e matrizes de dados. |
| **SQLite (SQLAlchemy)**| Persistência local. | Simplicidade, não exige servidor externo e ideal para prototipagem. |
| **Scikit-Learn** | Machine Learning. | Biblioteca robusta para modelos tabulares (Random Forest, etc). |
| **Transformers** | Notícias (NLP). | Extração de sentimento e impacto de textos de forma avançada. |
| **FastAPI** | API de backend. | Alta performance e facilidade de integração com interfaces web. |
| **Streamlit** | Dashboard interno. | Criação rápida de painéis de visualização de dados. |
| **Go (Golang)** | Microsserviços. | Preparação para escalabilidade e processos de alta performance. |

## 5. Fluxo de Operação Recomendado
Para operar o AlphaScope, o fluxo padrão é:
1. **Ingestão:** Coleta de dados de mercado e notícias.
2. **Features:** Geração de indicadores técnicos.
3. **Inteligência:** Treinamento ou carregamento de modelos de IA.
4. **Ranking:** Geração de scores e sinais para os ativos.
5. **Simulação:** Execução simulada (Backtest ou Paper Trading).
6. **Monitoramento:** Acompanhamento do status operacional e performance.

---
*Este documento serve como guia de referência rápida para o entendimento arquitetural e funcional do projeto.*
