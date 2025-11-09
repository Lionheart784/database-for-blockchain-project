CREATE TABLE TOKEN (
    token_address VARCHAR(42) PRIMARY KEY,          -- 以太坊地址格式：0x + 40个十六进制字符
    symbol VARCHAR(20) NOT NULL,                    -- 代币符号（如ETH, USDT）
    name VARCHAR(100) NOT NULL,                     -- 代币全称
    chain VARCHAR(20) NOT NULL DEFAULT 'ETH',       -- 所在区块链（ETH/BSC/POLYGON等）
    is_proxy BOOLEAN DEFAULT false,                 -- 是否为代理合约（安全风险标识）
    is_upgradeable BOOLEAN DEFAULT false,           -- 是否可升级（安全风险标识）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 记录创建时间
);

CREATE INDEX idx_token_symbol ON TOKEN(symbol);     -- 优化按symbol查询
CREATE INDEX idx_token_risk ON TOKEN(is_proxy, is_upgradeable)  -- 优化风险筛选查询
WHERE is_proxy = true OR is_upgradeable = true;

COMMENT ON TABLE TOKEN IS '代币基本信息表 - 系统中心实体';
COMMENT ON COLUMN TOKEN.is_proxy IS '代理合约标识（高风险因素）';
COMMENT ON COLUMN TOKEN.is_upgradeable IS '可升级合约标识（高风险因素）';

CREATE TABLE DEX_PRICE (
    price_id BIGSERIAL,                             -- 自增主键
    token_address VARCHAR(42) NOT NULL,             -- 关联代币地址
    price DECIMAL(36, 18) NOT NULL,                 -- 价格（支持极小金额，18位小数）
    tvl DECIMAL(36, 2),                             -- 总锁仓价值（Total Value Locked）
    liquidity_depth DECIMAL(36, 2),                 -- 流动性深度（1%价格影响下的可交易量）
    volume_24h DECIMAL(36, 2),                      -- 24小时交易量
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 价格快照时间

    PRIMARY KEY (price_id, timestamp),              -- 复合主键（分区表要求）
    CONSTRAINT fk_dex_token FOREIGN KEY (token_address)
        REFERENCES TOKEN(token_address)
) PARTITION BY RANGE (timestamp);                   -- 按时间范围分区

CREATE TABLE DEX_PRICE_2025_01 PARTITION OF DEX_PRICE
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE DEX_PRICE_2025_02 PARTITION OF DEX_PRICE
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE DEX_PRICE_2025_03 PARTITION OF DEX_PRICE
FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE INDEX idx_dex_token_time ON DEX_PRICE(token_address, timestamp DESC);  -- 查询特定代币的历史价格
CREATE INDEX idx_dex_time ON DEX_PRICE(timestamp DESC);                       -- 查询最新价格

COMMENT ON TABLE DEX_PRICE IS 'DEX价格时序数据（按月分区）';

CREATE TABLE CEX_PRICE (
    price_id BIGSERIAL,                             -- 自增主键
    token_symbol VARCHAR(20) NOT NULL,              -- 代币符号（注意：这里用symbol而非address）
    exchange VARCHAR(50) NOT NULL,                  -- 交易所名称（Binance/OKX/Coinbase等）
    spot_price DECIMAL(36, 18),                     -- 现货价格
    funding_rate DECIMAL(10, 8),                    -- 永续合约资金费率（市场情绪指标）
    volume_24h DECIMAL(36, 2),                      -- 24小时成交量
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (price_id, timestamp)
) PARTITION BY RANGE (timestamp);

CREATE TABLE CEX_PRICE_2025_01 PARTITION OF CEX_PRICE
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE CEX_PRICE_2025_02 PARTITION OF CEX_PRICE
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE CEX_PRICE_2025_03 PARTITION OF CEX_PRICE
FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE INDEX idx_cex_symbol_time ON CEX_PRICE(token_symbol, timestamp DESC);
CREATE INDEX idx_cex_exchange ON CEX_PRICE(exchange);

COMMENT ON TABLE CEX_PRICE IS 'CEX市场数据（按月分区）';

CREATE TABLE TOKEN_HOLDER (
    holder_id BIGSERIAL PRIMARY KEY,                -- 自增主键
    token_address VARCHAR(42) NOT NULL,             -- 关联代币地址
    holder_address VARCHAR(42) NOT NULL,            -- 持仓地址
    balance DECIMAL(78, 0) NOT NULL,                -- 持仓数量（最多78位整数）
    percentage DECIMAL(10, 6) NOT NULL,             -- 持仓占比（精确到0.0001%）
    rank INT NOT NULL,                              -- 持仓排名（1=最大持仓者）
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,  -- 快照日期

    CONSTRAINT fk_holder_token FOREIGN KEY (token_address)
        REFERENCES TOKEN(token_address),
    CONSTRAINT uq_holder_snapshot UNIQUE (token_address, holder_address, snapshot_date)  -- 每天每地址只有一条记录
);

CREATE INDEX idx_holder_token_date ON TOKEN_HOLDER(token_address, snapshot_date DESC);
CREATE INDEX idx_holder_rank ON TOKEN_HOLDER(token_address, rank) WHERE rank <= 10;  -- 部分索引：只索引Top 10

COMMENT ON TABLE TOKEN_HOLDER IS '代币持仓分布快照（每日更新）';

CREATE TABLE TOKEN_SCORE (
    score_id BIGSERIAL PRIMARY KEY,                 -- 自增主键
    token_address VARCHAR(42) NOT NULL,             -- 关联代币地址
    score INT NOT NULL CHECK (score >= 0 AND score <= 100),  -- 综合评分（0-100）
    score_factors JSONB,                            -- 评分因子详情（JSON格式）
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_score_token FOREIGN KEY (token_address)
        REFERENCES TOKEN(token_address)
);

CREATE INDEX idx_score_token_time ON TOKEN_SCORE(token_address, timestamp DESC);
CREATE INDEX idx_score_value ON TOKEN_SCORE(score DESC);  -- 优化Top N查询

COMMENT ON TABLE TOKEN_SCORE IS '代币综合评分（基于多维度因子）';

CREATE TABLE PROJECT (
    project_id SERIAL PRIMARY KEY,                  -- 自增主键
    token_address VARCHAR(42) NOT NULL UNIQUE,      -- 关联代币地址（一对一关系）
    project_name VARCHAR(100) NOT NULL,             -- 项目名称
    github_repo VARCHAR(200),                       -- GitHub仓库URL
    github_stars INT DEFAULT 0,                     -- Star数量
    commit_count_7d INT DEFAULT 0,                  -- 近7天提交次数
    last_commit_at TIMESTAMP,                       -- 最后提交时间

    CONSTRAINT fk_project_token FOREIGN KEY (token_address)
        REFERENCES TOKEN(token_address)
);

CREATE INDEX idx_project_token ON PROJECT(token_address);
CREATE INDEX idx_project_stars ON PROJECT(github_stars DESC);  -- 优化热门项目查询

COMMENT ON TABLE PROJECT IS '项目基本信息和GitHub活跃度';

CREATE TABLE ALERT (
    alert_id BIGSERIAL PRIMARY KEY,                 -- 自增主键
    token_address VARCHAR(42) NOT NULL,             -- 关联代币地址
    alert_type VARCHAR(50) NOT NULL,                -- 预警类型（LIQUIDITY_DROP/PRICE_SPIKE等）
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),  -- 严重程度
    message TEXT,                                   -- 预警详细信息
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_alert_token FOREIGN KEY (token_address)
        REFERENCES TOKEN(token_address)
);

CREATE INDEX idx_alert_token_time ON ALERT(token_address, timestamp DESC);
CREATE INDEX idx_alert_severity ON ALERT(severity, timestamp DESC)
WHERE severity IN ('HIGH', 'CRITICAL');  -- 部分索引：只索引高危预警

COMMENT ON TABLE ALERT IS '风险预警记录';

INSERT INTO TOKEN (token_address, symbol, name, is_proxy, is_upgradeable)
VALUES
    ('0x0000000000000000000000000000000000000001', 'ETH', 'Ethereum', false, false),
    ('0xdAC17F958D2ee523a2206206994597C13D831ec7', 'USDT', 'Tether USD', true, false),
    ('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'USDC', 'USD Coin', true, true)
ON CONFLICT (token_address) DO NOTHING;

SELECT 'Schema创建完成！共7个表，3个测试代币' as message;