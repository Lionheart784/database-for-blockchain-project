-- 分析点查询的执行计划
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM v_token_dashboard WHERE symbol = 'TOKEN1';

-- 分析范围查询的执行计划
EXPLAIN (ANALYZE, BUFFERS)
SELECT timestamp, price
FROM DEX_PRICE
WHERE token_address = (SELECT token_address FROM TOKEN LIMIT 1)
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp;