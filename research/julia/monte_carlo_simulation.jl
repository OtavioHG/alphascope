using Random, Statistics

Random.seed!(42)

function monte_carlo_returns(mu::Float64, sigma::Float64, periods::Int64, paths::Int64)
    simulations = [cumprod(1 .+ randn(periods) .* sigma .+ mu) for _ in 1:paths]
    terminal_values = [path[end] for path in simulations]
    println("mean_terminal_value=", mean(terminal_values))
    println("std_terminal_value=", std(terminal_values))
end

monte_carlo_returns(0.001, 0.02, 252, 500)
