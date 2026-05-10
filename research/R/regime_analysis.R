returns <- c(0.03, 0.02, -0.01, -0.02, 0.005, 0.001)
volatility <- c(0.05, 0.04, 0.02, 0.03, 0.01, 0.015)

regime <- ifelse(returns > 0.01 & volatility < 0.05, "bullish",
          ifelse(returns < -0.01, "bearish", "sideways"))

print(data.frame(returns, volatility, regime))
