set.seed(42)

returns <- c(0.01, -0.005, 0.012, 0.004, -0.003, 0.015, 0.006)
t_test <- t.test(returns)

print("Mean return:")
print(mean(returns))
print("T-test:")
print(t_test)
