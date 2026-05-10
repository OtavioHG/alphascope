# AlphaScope Research em R

Esta pasta é reservada para validação estatística offline em R.

Papel recomendado do R no projeto:
- testes de significância
- análise estatística de regimes
- validação de estratégia
- geração de relatórios estatísticos de pesquisa

Regra operacional:
- R não participa do runtime de produção.
- Resultados úteis devem ser exportados como CSV/JSON/Markdown e consumidos pelo core Python ou pela documentação.

Arquivos atuais:
- `strategy_significance_tests.R`
- `regime_analysis.R`
- `statistical_validation.R`

Quando a toolchain R estiver disponível, use:
```bash
cd research/R
Rscript statistical_validation.R
```
