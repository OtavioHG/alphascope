# Estratégia multi-linguagem do AlphaScope

Este documento define o papel esperado de cada linguagem no projeto para evitar sobreposição de responsabilidades.

## Python
Responsável por:
- core de negócio
- pipeline quantitativo
- CLI principal
- API oficial
- dashboard Streamlit
- orquestração operacional

## TypeScript / React / Next.js
Responsável por:
- interface web moderna
- control plane web
- observabilidade visual
- consumo da API Python

## Rust
Responsável por:
- kernels numéricos de alta performance
- aceleração opcional para cálculos críticos
- integração via bindings Python

## Go
Responsável por:
- serviços auxiliares concorrentes
- ingestão desacoplada
- adapters de exchange
- workers e serviços de infraestrutura

## Julia
Responsável por:
- pesquisa quantitativa offline
- simulação e prototipagem numérica
- experimentos antes da promoção para Python ou Rust

## R
Responsável por:
- validação estatística offline
- significância, regimes e relatórios estatísticos

## Regra de promoção
Se uma linguagem fora do core Python gerar valor operacional:
1. provar utilidade em pesquisa/scaffold
2. documentar objetivo e entrada/saída
3. adicionar testes ou validações mínimas
4. integrar com o core sem duplicar regras de negócio
