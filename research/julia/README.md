# AlphaScope Research em Julia

Esta pasta é reservada para pesquisa quantitativa offline em Julia.

Papel recomendado da Julia no projeto:
- simulações numéricas exploratórias
- protótipos de risco e carteira
- estudos de Monte Carlo
- experimentos de alta performance antes de decidir promoção para Python ou Rust

Regra operacional:
- Julia é camada de pesquisa, não runtime de produção.
- Se um experimento provar valor, ele deve ser promovido para o core Python ou para kernels Rust quando fizer sentido.

Arquivos atuais:
- `portfolio_simulation.jl`
- `risk_modeling.jl`
- `monte_carlo_simulation.jl`

Quando a toolchain Julia estiver disponível, use:
```bash
cd research/julia
julia --project=. portfolio_simulation.jl
```
