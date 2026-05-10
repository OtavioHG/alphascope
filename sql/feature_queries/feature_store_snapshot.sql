SELECT
    symbol,
    feature_name,
    feature_value,
    timestamp
FROM feature_store
WHERE timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
