strategy_a <- c(0.01, 0.015, -0.005, 0.02, 0.012)
strategy_b <- c(0.005, 0.01, -0.004, 0.011, 0.009)

test <- wilcox.test(strategy_a, strategy_b, paired = FALSE)
print("Wilcoxon test between strategy_a and strategy_b")
print(test)
