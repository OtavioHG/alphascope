using Statistics

weights = [0.4, 0.35, 0.25]
expected_returns = [0.12, 0.18, 0.22]
volatility = [0.20, 0.30, 0.40]

portfolio_return = sum(weights .* expected_returns)
portfolio_risk = sum(weights .* volatility)

println("portfolio_return=", portfolio_return)
println("portfolio_risk_proxy=", portfolio_risk)
