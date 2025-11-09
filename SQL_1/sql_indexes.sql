CREATE INDEX IF NOT EXISTS idx_dex_price_token_ts_price
ON DEX_PRICE(token_address, timestamp DESC, price);

CREATE INDEX IF NOT EXISTS idx_score_token_value
ON TOKEN_SCORE(token_address, score DESC, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_alert_time
ON ALERT(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_cex_exchange_symbol
ON CEX_PRICE(exchange, token_symbol, timestamp DESC);

ANALYZE TOKEN;
ANALYZE DEX_PRICE;
ANALYZE CEX_PRICE;
ANALYZE TOKEN_HOLDER;
ANALYZE TOKEN_SCORE;
ANALYZE PROJECT;
ANALYZE ALERT;

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;