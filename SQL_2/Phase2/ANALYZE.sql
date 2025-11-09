-- 更新所有表的统计信息
ANALYZE TOKEN;
ANALYZE DEX_PRICE;
ANALYZE CEX_PRICE;
ANALYZE TOKEN_HOLDER;
ANALYZE TOKEN_SCORE;
ANALYZE PROJECT;
ANALYZE ALERT;

-- 查看表的统计信息（修正版）
SELECT
    schemaname,
    relname as tablename,
    n_live_tup as row_count,
    n_dead_tup as dead_rows,
    last_analyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;