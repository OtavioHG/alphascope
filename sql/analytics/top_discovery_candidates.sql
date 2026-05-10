SELECT
    strategy_id,
    alpha_discovery_score,
    promotion_status,
    created_at
FROM discovery_rankings
ORDER BY alpha_discovery_score DESC
LIMIT 20;
