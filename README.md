# 🚀 AlphaScope: Modular Quantitative Trading Intelligence

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Trading](https://img.shields.io/badge/trading-crypto-orange.svg)

**AlphaScope** é uma plataforma quantitativa modular desenvolvida para o mercado de criptomoedas. O sistema automatiza todo o ciclo de vida do trading: desde a ingestão massiva de dados (Binance, GDELT, Fear & Greed) até a execução de Paper Trading monitorada por modelos de Machine Learning e NLP.

---

## 🎯 O Propósito
O objetivo principal do AlphaScope é democratizar o **Trading Quantitativo Profissional**. 
- **Trading sem Emoção:** Decisões baseadas em dados e scoring híbrido.
- **Automação 24/7:** Um motor de runtime (Daemon) que mantém o sistema operando ininterruptamente.
- **Inteligência de Mercado:** Processamento de notícias em tempo real para capturar o sentimento do mercado antes que ele se reflita nos preços.

---

## 🏗️ Arquitetura do Sistema
O AlphaScope segue uma arquitetura de **Pipeline em Camadas (Layered Pipeline)**:

```mermaid
graph TD
    subgraph "Camada de Dados (Data Layer)"
        A1[Binance OHLCV] --> B[(SQLite/Postgres)]
        A2[GDELT News] --> B
        A3[Fear & Greed Index] --> B
    end

    subgraph "Cérebro IA (AI Layer)"
        B --> C[Feature Engineering]
        C --> D[NLP Sentiment Analysis]
        C --> E[ML Model Predictors]
        D & E --> F[Hybrid Asset Ranking]
    end

    subgraph "Execução e Runtime (Operation Layer)"
        F --> G[Signal Dispatcher]
        G --> H[Paper Trader / Live Simulator]
        H --> I[Risk Manager]
    end

    subgraph "Observabilidade (Monitoring)"
        I --> J[Telegram Alerts]
        I --> K[Streamlit Dashboard]
        I --> L[Next.js Frontend]
    end
```

---

## 🛠️ Tecnologias Utilizadas
- **Linguagem:** Python 3.10+ (Core), Go (Microservices Scaffolds).
- **Data:** SQLite (Local Dev), PostgreSQL (Production), DuckDB (Research).
- **IA/ML:** Scikit-Learn, Optuna (Auto-ML), NLP Scoring.
- **Interface:** FastAPI (Backend API), Next.js (Frontend), Streamlit (Dashboard Interno).
- **Infraestrutura:** Docker, Alembic (Migrations), Pytest.

---

## 🚀 Como Iniciar

### 1. Preparar o Ambiente
```powershell
# Clone o repositório
git clone https://github.com/seu-usuario/alphascope.git
cd alphascope

# Crie e ative o ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Instale as dependências
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 2. Validar a Instalação
```powershell
python -m alphascope.cli doctor
```

---

## 💻 Comandos Principais

### 📊 Operações de Mercado
| Comando | Descrição |
| :--- | :--- |
| `ingest-market` | Coleta dados históricos da Binance. |
| `build-features` | Processa indicadores técnicos (RSI, Médias, etc). |
| `rank-assets` | Gera o ranking de ativos baseado no modelo de IA. |
| `backtest` | Simula uma estratégia no passado. |

### 🤖 Automação e Runtime
| Comando | Descrição |
| :--- | :--- |
| `run-pipeline` | Executa o ciclo completo (Ingest -> Feature -> Rank). |
| `paper-trade` | Inicia o trading simulado em tempo real. |
| `run-continuous` | Mantém o sistema rodando em ciclos infinitos. |
| `runtime-status` | Verifica a saúde do sistema e do Daemon. |

### 🌐 Interfaces
| Comando | Descrição |
| :--- | :--- |
| `run-platform-api` | Inicia a API FastAPI (Porta 8010). |
| `npm run dev` (na pasta frontend) | Inicia o Dashboard Next.js. |

---

## 📈 Melhorias e Futuro
Se você deseja contribuir ou expandir o AlphaScope:
1.  **Conexão Real:** Implementar a execução real via CCXT (atualmente o foco é Paper Trading).
2.  **Meta-Learning:** Evoluir o módulo de retreino automático para que a IA aprenda com seus erros de trade.
3.  **Frontend:** Finalizar a integração total entre o Next.js e a API FastAPI.

---

## ⚠️ Aviso Legal
Este software é para fins educacionais e de pesquisa. O trading de criptomoedas envolve alto risco. Não nos responsabilizamos por perdas financeiras.

---
⭐ **Gostou do projeto? Dê um Star no repositório!**
