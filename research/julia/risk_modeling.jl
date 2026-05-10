using Statistics

returns = [0.01, -0.02, 0.015, 0.005, -0.03, 0.02, 0.01]

sorted_returns = sort(returns)
var95 = sorted_returns[ceil(Int, 0.05 * length(sorted_returns))]
cvar95 = mean(filter(x -> x <= var95, returns))

println("VaR95=", var95)
println("CVaR95=", cvar95)
