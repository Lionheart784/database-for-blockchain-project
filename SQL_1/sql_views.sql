CREATE OR REPLACE VIEW v_token_dashboard AS
SELECT
    t.token_address,
    t.symbol,
    t.name,
    t.chain,
    t.is_proxy,
    t.is_upgradeable,
    -- 最新DEX价格（使用LATERAL JOIN优化子查询）
    d.price as latest_dex_price,
    d.tvl,
    d.volume_24h,
    -- 最新评分
    s.score as latest_score,
    s.score_factors,
    -- 项目信息
    p.project_name,
    p.github_stars,
    p.commit_count_7d,
    p.last_commit_at
FROM TOKEN t
LEFT JOIN LATERAL (
    SELECT price, tvl, volume_24h
    FROM DEX_PRICE
    WHERE token_address = t.token_address
    ORDER BY timestamp DESC
    LIMIT 1
) d ON true
LEFT JOIN LATERAL (
    SELECT score, score_factors
    FROM TOKEN_SCORE
    WHERE token_address = t.token_address
    ORDER BY timestamp DESC
    LIMIT 1
) s ON true
LEFT JOIN PROJECT p ON t.token_address = p.token_address;

COMMENT ON VIEW v_token_dashboard IS '代币综合仪表盘 - 汇总最新价格、评分、项目信息';

SELECT * FROM v_token_dashboard WHERE symbol = 'ETH';