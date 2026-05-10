CREATE OR REPLACE VIEW latest_strategy_health AS
SELECT
    strategy_id,
    MAX(created_at) AS latest_snapshot,
    AVG(robustness_score) AS avg_robustness_score,
    AVG(rolling_sharpe) AS avg_rolling_sharpe,
    AVG(rolling_drawdown) AS avg_rolling_drawdown
FROM strategy_health
GROUP BY strategy_id;
