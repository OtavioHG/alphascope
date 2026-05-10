# Produção com IA treinando continuamente

Este guia resume como manter a camada de IA do AlphaScope treinada junto com a operação, sem depender apenas de treino manual.

## Objetivo

Combinar duas estratégias:

1. warm start inicial do modelo antes da operação
2. retreinamento contínuo automático durante os ciclos do sistema

## 1. Warm start inicial antes de subir operação

```bash
python -m alphascope.cli train-production-ai --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h --horizon-bars 8 --threshold-pct 0.015
```

Esse comando:
- constrói o dataset supervisionado de mercado
- treina o modelo de mercado
- avalia o artefato salvo
- deixa o stack de IA pronto para uso operacional

## 2. Retreinamento automático durante operação

O projeto já possui ciclo de aprendizado contínuo no núcleo moderno.

As variáveis principais são:

```env
AUTO_RETRAIN_ENABLED=true
AUTO_RETRAIN_MIN_TRADES=50
AUTO_RETRAIN_INTERVAL_HOURS=24
AUTO_RETRAIN_MIN_WIN_RATE=0.45
AUTO_RETRAIN_MAX_DRAWDOWN=0.15
AUTO_RETRAIN_MIN_MODEL_SCORE=0.55
CONTINUOUS_LEARNING_ENABLED=true
DYNAMIC_THRESHOLDS_ENABLED=true
```

Quando habilitado, o runtime pode:
- registrar snapshots de ranking, sinais, features e previsões
- avaliar degradação
- treinar novamente o modelo
- promover o melhor candidato para produção

## 3. Fluxo recomendado na sua máquina

### Etapa A — treino inicial

```bash
python -m alphascope.cli doctor
python -m alphascope.cli backup-db
python -m alphascope.cli train-production-ai --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Etapa B — iniciar operação contínua

```bash
python -m alphascope.cli start-daemon --symbols BTCUSDT,ETHUSDT,SOLUSDT --cycle-seconds 300 --timeframe 1h --limit 500
```

### Etapa C — monitorar

```bash
python -m alphascope.cli runtime-status
python -m alphascope.cli show-trader-mode
```

## 4. Recomendação importante

Mesmo com a IA treinando continuamente:
- mantenha PAPER como padrão inicial
- valide o comportamento antes de pensar em live real
- revise os artefatos em `models/`
- acompanhe métricas e drawdown

## 5. Artefatos esperados

- `models/market/best_market_model.joblib`
- `models/market/best_market_model.json`
- `models/production/`
- `models/staging/`
- `models/archive/`
- `data/processed/market_training_dataset.parquet`
- `data/processed/models/`

## 6. Comandos úteis relacionados

```bash
python -m alphascope.cli train-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli evaluate-market-model --symbols BTCUSDT,ETHUSDT --interval 1h
python -m alphascope.cli predict-market --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
python -m alphascope.cli runtime-status
python -m alphascope.cli backup-db
```
