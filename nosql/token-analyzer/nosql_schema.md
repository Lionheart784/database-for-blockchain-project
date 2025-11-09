# NoSQL文档结构设计

## 1. tokens（代币集合）- 核心集合

### 设计思路
将代币的**最新价格、评分、项目信息**内嵌到主文档中，避免JOIN。

### 文档结构
\`\`\`javascript
{
  _id: ObjectId("..."),              // MongoDB自动生成的ID
  address: "0x...",                  // 代币地址（唯一索引）
  symbol: "ETH",                     // 代币符号
  name: "Ethereum",                  // 代币全称
  chain: "ETH",                      // 所在链
  is_proxy: false,                   // 是否为代理合约
  is_upgradeable: false,             // 是否可升级

  // ⭐ 内嵌最新价格（避免JOIN dex_prices表）
  latest_price: {
    dex_price: 1800.50,
    cex_price: 1801.20,
    tvl: 1500000000,
    liquidity_depth: 5000000,
    volume_24h: 2000000,
    timestamp: ISODate("2025-01-09T10:30:00Z")
  },

  // ⭐ 内嵌最新评分（避免JOIN token_scores表）
  latest_score: {
    score: 85,
    factors: {
      liquidity_score: 90,
      holder_score: 75,
      dev_score: 88,
      market_score: 82
    },
    timestamp: ISODate("2025-01-09T10:30:00Z")
  },

  // ⭐ 内嵌项目信息（避免JOIN project表）
  project: {
    name: "Ethereum Foundation",
    github_repo: "https://github.com/ethereum/go-ethereum",
    stars: 45000,
    commit_count_7d: 50,
    last_commit_at: ISODate("2025-01-09T08:20:00Z")
  },

  created_at: ISODate("2025-01-01T00:00:00Z"),
  updated_at: ISODate("2025-01-09T10:30:00Z")
}
\`\`\`

### 查询优势
\`\`\`javascript
// 一次查询获取所有信息（无需JOIN）
db.tokens.findOne({address: "0x..."})

// 对比SQL需要多次JOIN
SELECT t.*, d.price, s.score, p.github_stars
FROM TOKEN t
LEFT JOIN DEX_PRICE d ON ...
LEFT JOIN TOKEN_SCORE s ON ...
LEFT JOIN PROJECT p ON ...
\`\`\`

---

## 2. dex_prices（DEX价格时序数据）

### 设计思路
存储历史价格数据，用于绘制K线图和趋势分析。

### 文档结构
\`\`\`javascript
{
  _id: ObjectId("..."),
  token_address: "0x...",            // 索引字段
  price: 1800.50,
  tvl: 1500000000,
  liquidity_depth: 5000000,
  volume_24h: 2000000,
  timestamp: ISODate("2025-01-09T10:30:00Z"),  // 索引字段

  // ⭐ 预聚合字段（优化小时级查询）
  hour: ISODate("2025-01-09T10:00:00Z")
}
\`\`\`

### 索引设计
\`\`\`javascript
// 复合索引：按代币+时间查询
db.dex_prices.createIndex({token_address: 1, timestamp: -1})

// 单字段索引：按时间范围查询
db.dex_prices.createIndex({timestamp: -1})
\`\`\`

---

## 3. cex_prices（CEX价格数据）

### 文档结构
\`\`\`javascript
{
  _id: ObjectId("..."),
  token_symbol: "ETH",               // 注意：用symbol而非address
  exchange: "Binance",               // 交易所名称
  spot_price: 1801.20,
  funding_rate: 0.0001,              // 资金费率
  volume_24h: 5000000,
  timestamp: ISODate("2025-01-09T10:30:00Z")
}
\`\`\`

---

## 4. token_holders（持仓分布）

### 设计思路
使用**数组**存储所有持仓者，并**预计算**Top 10集中度。

### 文档结构
\`\`\`javascript
{
  _id: ObjectId("..."),
  token_address: "0x...",

  // ⭐ 数组存储所有持仓者（避免多条记录）
  holders: [
    {
      address: "0xabc...",
      balance: "1000000000000000000",  // 使用字符串存储大数字
      percentage: 15.5,
      rank: 1
    },
    {
      address: "0xdef...",
      balance: "500000000000000000",
      percentage: 8.2,
      rank: 2
    }
    // ... 最多存储Top 100
  ],

  // ⭐ 预计算字段（避免实时聚合）
  top10_concentration: 65.8,         // Top 10持仓占比
  top20_concentration: 82.3,         // Top 20持仓占比
  total_holders: 15234,              // 总持仓地址数

  snapshot_date: ISODate("2025-01-09T00:00:00Z"),
  updated_at: ISODate("2025-01-09T00:00:00Z")
}
\`\`\`

### 查询优势
\`\`\`javascript
// 直接使用预计算字段，无需实时聚合
db.token_holders.find({
  top10_concentration: {$gt: 50}    // 查找集中度>50%的代币
})

// 对比SQL需要实时GROUP BY聚合
SELECT token_address, SUM(percentage)
FROM TOKEN_HOLDER
WHERE rank <= 10
GROUP BY token_address
HAVING SUM(percentage) > 50
\`\`\`

---

## 5. token_scores（评分历史）

### 文档结构
\`\`\`javascript
{
  _id: ObjectId("..."),
  token_address: "0x...",
  score: 85,
  score_factors: {                   // 使用对象存储评分因子
    liquidity_score: 90,
    holder_score: 75,
    dev_score: 88,
    market_score: 82
  },
  timestamp: ISODate("2025-01-09T10:30:00Z")
}
\`\`\`

---

## 6. alerts（预警记录）

### 文档结构
\`\`\`javascript
{
  _id: ObjectId("..."),
  token_address: "0x...",
  alert_type: "LIQUIDITY_DROP",      // 预警类型
  severity: "HIGH",                  // 严重程度
  message: "TVL dropped by 25% in the last hour",
  timestamp: ISODate("2025-01-09T10:30:00Z"),
  acknowledged: false                // 是否已确认
}
\`\`\`

---

## 设计对比总结

| 设计决策 | SQL方案 | NoSQL方案 | 优势 |
|---------|---------|----------|------|
| 最新价格 | 分离表 + LATERAL JOIN | 内嵌到tokens | 减少JOIN，一次查询 |
| 持仓数据 | 每个持仓者一条记录 | 数组存储所有持仓者 | 减少记录数，一次查询 |
| 集中度计算 | 实时GROUP BY | 预计算字段 | 无需实时聚合，查询快 |
| Schema | 严格固定 | 灵活可变 | 易于扩展新字段 |
