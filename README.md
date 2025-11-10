# 区块链代币分析系统 - SQL vs NoSQL 性能对比实验

---

## 📌 项目概述

### 项目定位

这是一个**学术实验项目**，旨在通过真实的商业场景来对比 SQL 和 NoSQL 数据库的性能特点。

### 核心目标

1. ✅ 设计一个真实的区块链代币分析系统数据库
2. ✅ 实现 **PostgreSQL (SQL)** 和 **MongoDB + Redis (NoSQL)** 两套方案
3. ✅ 对比两种方案在不同查询场景下的性能表现

### 预期成果

- 两套可运行的数据库系统（SQL + NoSQL）
- 5 个关键查询场景的性能对比数据
- 10-12 页学术报告（包含文献引用）
- 完整的代码和文档交付

---

## 🎯 业务场景

### 业务目标

为加密货币投资者提供**实时代币评分和风险预警系统**，帮助他们做出投资决策。

### 核心功能

| 功能模块 | 描述 | 数据来源 |
|---------|------|---------|
| 📊 **实时价格监控** | 追踪 DEX/CEX 代币价格走势 | Uniswap, Binance API |
| 👥 **持仓分析** | 分析代币持仓集中度，识别"巨鲸" | 链上数据查询 |
| 💹 **流动性监控** | 监测 TVL 和流动性深度 | DEX 池数据 |
| 🎯 **代币评分** | 基于多维度给代币打分 (0-100) | 综合计算 |
| ⚠️ **风险预警** | 检测价格异常、流动性枯竭 | 实时监控系统 |
| 💻 **开发活跃度** | 跟踪项目 GitHub 活跃度 | GitHub API |

### 利益相关者

- **个人投资者**: 需要快速查询代币评分和价格
- **量化交易员**: 需要低延迟的市场数据
- **研究分析师**: 需要复杂的历史数据分析
- **系统管理员**: 需要低成本、易维护的系统

### 业务痛点

现有系统无法同时满足：
- ⚡ **低延迟**: 点查询 < 50ms (P95)
- 🔍 **复杂查询**: 支持多表 JOIN 和聚合分析
- 💰 **成本控制**: 云成本 < $100/月
- 📈 **可扩展性**: 支持 1000+ 代币，每分钟更新

---

## 🏗️ 技术架构

### 系统架构对比

```
┌─────────────────────────────────────────────────────┐
│            数据采集层（模拟）                          │
│  合成数据生成器 → 模拟 DEX/CEX API 响应                 │
└────────────────────┬────────────────────────────────┘
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
    ┌─────────────┐     ┌─────────────┐
    │ SQL方案     │     │ NoSQL方案   │
    ├─────────────┤     ├─────────────┤
    │ PostgreSQL  │     │ MongoDB     │
    │ • 规范化设计 │     │ • 内嵌文档   │
    │ • 分区表    │     │ • 预计算     │
    │ • B树索引   │     │ + Redis     │
    │ • 强一致性  │     │ • 缓存热数据  │
    └──────┬──────┘     └──────┬──────┘
           │                   │
           └─────────┬─────────┘
                     ▼
            ┌────────────────┐
            │  性能测试框架   │
            │  (Python)      │
            └────────┬───────┘
                     ▼
            ┌────────────────┐
            │  对比分析报告   │
            └────────────────┘
```

### SQL 方案设计要点

**PostgreSQL 14+**

| 特性 | 实现方式 | 优势 |
|------|---------|------|
| **规范化设计** | 7 个独立表，避免冗余 | 数据一致性 |
| **分区策略** | 时序表按月分区 | 查询性能 |
| **索引优化** | B 树 + 复合索引 | JOIN 效率 |
| **事务支持** | ACID 保证 | 强一致性 |

**适用场景**:
- ✅ 复杂关联查询（多表 JOIN）
- ✅ 聚合分析（GROUP BY, SUM）
- ✅ 强一致性要求
- ✅ 历史数据分析

### NoSQL 方案设计要点

**MongoDB + Redis**

| 特性 | 实现方式 | 优势 |
|------|---------|------|
| **内嵌文档** | 最新价格内嵌到代币文档 | 点查询快 |
| **预计算** | 持仓集中度预先计算 | 减少实时计算 |
| **缓存层** | Redis 缓存热点数据 (TTL=5分钟) | 超低延迟 |
| **水平扩展** | 分片支持 | 高并发写入 |

**适用场景**:
- ✅ 高并发写入（每秒 1000+ 更新）
- ✅ 点查询为主（单代币查询）
- ✅ 灵活 schema 需求
- ✅ 分布式部署

---

## 🗂️ 数据库设计

### 实体关系图（简化版 - 7 个核心实体）

```
            ┌─────────────┐
            │   TOKEN     │ ◄─── 中心实体
            │ ─────────── │
            │ token_address (PK)
            │ symbol      │
            │ name        │
            │ chain       │
            │ is_proxy    │
            │ is_upgradeable
            └──────┬──────┘
                   │
         ┌─────────┼─────────┬──────────┬──────────┐
         │         │         │          │          │
    ┌────▼───┐ ┌──▼──────┐ ┌▼────────┐ ┌▼───────┐ ┌▼─────┐
    │DEX     │ │CEX      │ │TOKEN    │ │TOKEN   │ │PROJECT│
    │PRICE   │ │PRICE    │ │HOLDER   │ │SCORE   │ │       │
    │        │ │         │ │         │ │        │ │       │
    │时序数据│ │时序数据  │ │快照数据 │ │事件数据│ │静态数据│
    └────────┘ └─────────┘ └─────────┘ └────────┘ └───────┘
                                                   ┌──────┐
                                                   │ALERT │
                                                   │预警  │
                                                   └──────┘
```

### 核心实体说明

| 实体 | 类型 | 更新频率 | 记录数 (估算) | 关键属性 |
|-----|------|---------|--------------|---------|
| **TOKEN** | 静态 | 低 | 1,000 | symbol, chain, 合约风险标识 |
| **DEX_PRICE** | 时序 | 每分钟 | 100万+/月 | price, tvl, liquidity_depth |
| **CEX_PRICE** | 时序 | 高频 | 100万+/月 | spot_price, funding_rate |
| **TOKEN_HOLDER** | 快照 | 每天 | 10万/天 | holder_address, balance, rank |
| **TOKEN_SCORE** | 事件 | 变化时 | 1万/天 | score, score_factors (JSON) |
| **PROJECT** | 静态 | 每周 | 1,000 | github_repo, commit_count |
| **ALERT** | 事件 | 触发时 | 1000/天 | alert_type, severity |

### SQL Schema 示例

```sql
-- 代币主表
CREATE TABLE TOKEN (
    token_address VARCHAR(42) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    chain VARCHAR(20) NOT NULL,
    is_proxy BOOLEAN DEFAULT false,
    is_upgradeable BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DEX 价格表（分区）
CREATE TABLE DEX_PRICE (
    id BIGSERIAL,
    token_address VARCHAR(42) NOT NULL REFERENCES TOKEN(token_address),
    dex_name VARCHAR(50),
    price DECIMAL(30, 18),
    tvl DECIMAL(20, 2),
    liquidity_depth DECIMAL(20, 2),
    volume_24h DECIMAL(20, 2),
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 按月分区
CREATE TABLE DEX_PRICE_2025_01 PARTITION OF DEX_PRICE
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### NoSQL Schema 示例

```javascript
// MongoDB - Token 集合（内嵌最新数据）
{
  "_id": "0x1234...",
  "symbol": "ETH",
  "name": "Ethereum",
  "chain": "ETH",
  "latest_price": {  // 内嵌最新价格，减少查询
    "dex_price": 2000.50,
    "cex_price": 2001.00,
    "tvl": 1000000,
    "timestamp": ISODate("2025-11-06T10:00:00Z")
  },
  "latest_score": {  // 内嵌最新评分
    "score": 85,
    "factors": {
      "liquidity": 90,
      "holder_concentration": 70,
      "github_activity": 95
    },
    "timestamp": ISODate("2025-11-06T10:00:00Z")
  },
  "risk_flags": {
    "is_proxy": false,
    "is_upgradeable": false
  }
}

// Redis 缓存策略
// Key: token:{address}:latest
// Value: JSON 字符串
// TTL: 300 秒 (5分钟)
```

---

## 🧪 实验设计

### 5 个关键查询场景

| 场景 | 查询类型 | 业务场景 | 预期赢家 |
|-----|---------|---------|---------|
| **Q1** | 点查询 | 获取单个代币最新信息 | NoSQL (Redis) |
| **Q2** | 范围查询 | 获取价格历史走势 | 平手 |
| **Q3** | 聚合查询 | Top 10 高评分代币 | SQL |
| **Q4** | 复杂 JOIN | 持仓集中度分析 | SQL |
| **Q5** | 批量写入 | 每分钟更新 1000 个代币价格 | NoSQL |

### Q1: 点查询 - 获取单个代币最新信息

**业务场景**: 用户查看某个代币的当前状态

<details>
<summary><b>SQL 查询</b></summary>

```sql
SELECT
    t.symbol,
    d.price,
    d.tvl,
    s.score
FROM TOKEN t
JOIN LATERAL (
    SELECT price, tvl
    FROM DEX_PRICE
    WHERE token_address = t.token_address
    ORDER BY timestamp DESC
    LIMIT 1
) d ON true
JOIN LATERAL (
    SELECT score
    FROM TOKEN_SCORE
    WHERE token_address = t.token_address
    ORDER BY timestamp DESC
    LIMIT 1
) s ON true
WHERE t.token_address = '0x...';
```
</details>

<details>
<summary><b>NoSQL 查询</b></summary>

```python
# Redis 缓存优先
cached = redis.get(f"token:{address}:latest")
if cached:
    return json.loads(cached)

# MongoDB fallback
token = db.tokens.find_one(
    {"_id": address},
    {"symbol": 1, "latest_price": 1, "latest_score": 1}
)
```
</details>

**预期结果**: NoSQL (Redis 缓存) 延迟 < 5ms vs SQL 延迟 20-50ms

---

### Q2: 范围查询 - 获取价格历史走势

**业务场景**: 查看某代币过去 24 小时价格走势

<details>
<summary><b>SQL 查询</b></summary>

```sql
SELECT timestamp, price, tvl
FROM DEX_PRICE
WHERE token_address = '0x...'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp;
```
</details>

<details>
<summary><b>NoSQL 查询</b></summary>

```python
db.dex_prices.find(
    {
        "token_address": address,
        "timestamp": {"$gte": datetime.now() - timedelta(days=1)}
    }
).sort("timestamp", 1)
```
</details>

**预期结果**: 两者性能接近，PostgreSQL 分区可能略优

---

### Q3: 聚合查询 - Top 10 高评分代币

**业务场景**: 推荐系统展示最佳投资标的

<details>
<summary><b>SQL 查询</b></summary>

```sql
SELECT
    t.symbol,
    s.score,
    d.tvl
FROM TOKEN t
JOIN TOKEN_SCORE s ON t.token_address = s.token_address
JOIN DEX_PRICE d ON t.token_address = d.token_address
WHERE s.timestamp = (SELECT MAX(timestamp) FROM TOKEN_SCORE WHERE token_address = t.token_address)
  AND d.timestamp = (SELECT MAX(timestamp) FROM DEX_PRICE WHERE token_address = t.token_address)
ORDER BY s.score DESC
LIMIT 10;
```
</details>

<details>
<summary><b>NoSQL 查询</b></summary>

```python
db.tokens.find().sort("latest_score.score", -1).limit(10)
```
</details>

**预期结果**: SQL 的 JOIN 优化可能更优（但 NoSQL 的内嵌文档避免了 JOIN）

---

### Q4: 复杂 JOIN - 持仓集中度分析

**业务场景**: 识别高风险代币（筹码过于集中）

<details>
<summary><b>SQL 查询</b></summary>

```sql
SELECT
    t.symbol,
    SUM(CASE WHEN h.rank <= 10 THEN h.percentage ELSE 0 END) as top10_concentration
FROM TOKEN t
JOIN TOKEN_HOLDER h ON t.token_address = h.token_address
WHERE h.snapshot_date = CURRENT_DATE
GROUP BY t.symbol, t.token_address
HAVING SUM(CASE WHEN h.rank <= 10 THEN h.percentage ELSE 0 END) > 50
ORDER BY top10_concentration DESC;
```
</details>

<details>
<summary><b>NoSQL 查询</b></summary>

```python
# 需要应用层聚合（性能劣势）
tokens = db.tokens.find()
for token in tokens:
    holders = db.token_holders.find({
        "token_address": token["address"],
        "rank": {"$lte": 10}
    })
    concentration = sum(h["percentage"] for h in holders)
    if concentration > 50:
        results.append({"symbol": token["symbol"], "concentration": concentration})
```
</details>

**预期结果**: SQL 明显优于 NoSQL（原生 JOIN 和聚合）

---

### Q5: 批量写入 - 高频价格更新

**业务场景**: 每分钟更新 1000 个代币的价格

<details>
<summary><b>SQL 插入</b></summary>

```sql
INSERT INTO DEX_PRICE (token_address, price, tvl, timestamp)
VALUES
    ('0x...', 2000.50, 1000000, NOW()),
    ('0x...', 1500.20, 500000, NOW()),
    ...  -- 1000 条记录
ON CONFLICT (token_address, timestamp) DO UPDATE
SET price = EXCLUDED.price, tvl = EXCLUDED.tvl;
```
</details>

<details>
<summary><b>NoSQL 插入</b></summary>

```python
# MongoDB 批量插入
db.dex_prices.insert_many([
    {"token_address": "0x...", "price": 2000.50, "tvl": 1000000, "timestamp": datetime.now()},
    # ... 1000 条记录
])

# 同时更新 Redis 缓存
pipe = redis.pipeline()
for record in records:
    pipe.setex(f"token:{record['address']}:latest", 300, json.dumps(record))
pipe.execute()
```
</details>

**预期结果**: NoSQL 写入吞吐量更高（无 MVCC 开销）

---

### 评估指标

| 指标 | 单位 | 测量方法 | 目标值 |
|------|------|---------|-------|
| **平均延迟** | 毫秒 (ms) | 100 次查询的平均响应时间 | < 50ms |
| **P95 延迟** | 毫秒 (ms) | 95% 请求的响应时间 | < 100ms |
| **吞吐量** | QPS | 每秒查询数 | > 100 QPS |
| **存储空间** | MB | 数据库实际占用空间 | - |
| **索引大小** | MB | 索引占用空间 | - |

---

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Python 3.8+
- 至少 4GB RAM

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd blockchain-token-analyzer
```

### 2. 启动数据库服务

```bash
# 启动 PostgreSQL, MongoDB, Redis
docker-compose up -d

# 验证服务状态
docker-compose ps
```

### 3. 初始化 SQL 数据库

```bash
# 执行 Schema
docker exec -i token-postgres psql -U postgres -d token_analyzer < schema.sql

# 验证表创建
docker exec -it token-postgres psql -U postgres -d token_analyzer -c "\dt"
```

### 4. 初始化 NoSQL 数据库

```bash
# MongoDB 初始化
python scripts/nosql_setup.py

# Redis 配置
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 5. 生成测试数据

```bash
# 生成 10 万条合成数据
python scripts/data_generator.py --records 100000

# 加载数据到 SQL
python scripts/sql_data_loader.py

# 加载数据到 NoSQL
python scripts/nosql_data_loader.py
```

### 6. 运行性能测试

```bash
# 执行 5 个查询场景的性能测试
python scripts/benchmark.py

# 查看结果
cat results/performance_report.json
```

---

## 📊 核心查询场景

### 场景 1: 代币综合仪表盘

```sql
-- SQL: 使用预定义视图
SELECT * FROM v_token_dashboard
WHERE symbol = 'ETH';
```

```javascript
// NoSQL: 直接查询文档
db.tokens.findOne({ symbol: "ETH" });
```

### 场景 2: 流动性监控

检测 TVL 异常下降（24 小时内下降 > 20%）

```sql
WITH current_tvl AS (
    SELECT token_address, SUM(tvl) as tvl
    FROM DEX_PRICE
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY token_address
),
previous_tvl AS (
    SELECT token_address, SUM(tvl) as tvl
    FROM DEX_PRICE
    WHERE timestamp BETWEEN NOW() - INTERVAL '25 hours'
                        AND NOW() - INTERVAL '24 hours'
    GROUP BY token_address
)
SELECT
    t.symbol,
    (c.tvl - p.tvl) / p.tvl * 100 as tvl_change_pct
FROM TOKEN t
JOIN current_tvl c ON t.token_address = c.token_address
JOIN previous_tvl p ON t.token_address = p.token_address
WHERE (c.tvl - p.tvl) / p.tvl < -0.2
ORDER BY tvl_change_pct;
```

### 场景 3: CEX-DEX 套利机会

检测价差超过 2% 且流动性充足的代币

```sql
SELECT
    t.symbol,
    d.price as dex_price,
    c.spot_price as cex_price,
    (c.spot_price - d.price) / d.price * 100 as price_diff_pct,
    d.liquidity_depth
FROM TOKEN t
JOIN DEX_PRICE d ON t.token_address = d.token_address
JOIN CEX_PRICE c ON t.symbol = c.token_symbol
WHERE d.timestamp > NOW() - INTERVAL '5 minutes'
  AND c.timestamp > NOW() - INTERVAL '5 minutes'
  AND ABS((c.spot_price - d.price) / d.price) > 0.02
  AND d.liquidity_depth > 100000
ORDER BY ABS((c.spot_price - d.price) / d.price) DESC;
```

---

## 👥 团队分工

### 组 1: SQL 方案实现（2 人）


**任务**:
- [ ] 实现 PostgreSQL 数据库（7 个核心表）
- [ ] 创建必要的索引和视图
- [ ] 编写数据插入脚本 (`sql_data_loader.py`)
- [ ] 实现 5 个关键查询 (`sql_queries.py`)
- [ ] 性能优化和测试

**交付物**:
- `sql_schema_simplified.sql`
- `sql_data_loader.py`
- `sql_queries.py`
- `SQL_IMPLEMENTATION.md`（设计文档）

---

### 组 2: NoSQL 方案实现（2 人）


**任务**:
- [ ] 设计 MongoDB 文档结构
- [ ] 配置 Redis 缓存策略
- [ ] 创建必要的索引
- [ ] 编写数据插入脚本 (`nosql_data_loader.py`)
- [ ] 实现相同的 5 个查询 (`nosql_queries.py`)

**交付物**:
- `nosql_schema.md`（文档结构说明）
- `nosql_data_loader.py`
- `nosql_queries.py`
- `NOSQL_IMPLEMENTATION.md`（设计文档）

---

### 组 3: 实验设计和报告撰写（2 人）

**任务**:
- [ ] 设计性能测试框架 (`benchmark.py`)
- [ ] 生成合成测试数据 (`data_generator.py`)
- [ ] 执行性能测试，收集 QPS、延迟、存储数据
- [ ] 查找和引用 3 篇以上学术文献
- [ ] 撰写 10-12 页报告

**交付物**:
- `benchmark.py`（性能测试框架）
- `data_generator.py`（合成数据生成器）
- `EXPERIMENT_RESULTS.md`（实验数据）
- `CDS534_Group_[TeamName]_Final.pdf`（最终报告）

---

## 📦 交付清单

### 代码和脚本

- [ ] `sql_schema_simplified.sql` - SQL 建表脚本
- [ ] `sql_data_loader.py` - SQL 数据加载
- [ ] `sql_queries.py` - SQL 查询实现
- [ ] `nosql_schema.md` - NoSQL 结构说明
- [ ] `nosql_data_loader.py` - NoSQL 数据加载
- [ ] `nosql_queries.py` - NoSQL 查询实现
- [ ] `data_generator.py` - 合成数据生成器
- [ ] `benchmark.py` - 性能测试框架

### 报告大纲（10-12 页）

1. **标题页**（1 页）
   - 课程名称、项目标题、团队成员（学号 + 姓名）

2. **Motivation + Problem Definition**（2 页）
   - 业务背景、可衡量目标、痛点分析

3. **Literature Review**（2 页）
   - SQL vs NoSQL 对比表、3 篇文献总结、APA 引用

4. **Our Approach**（2 页）
   - 系统架构图、技术决策、数据模型设计

5. **Challenges + Solutions**（1 页）
   - 时序数据高写入压力、复杂 JOIN 性能、一致性权衡

6. **Evaluations**（3 页）
   - 实验设置、5 个查询性能对比、结论

7. **References + Team Management**（1 页）
   - APA 格式参考文献、团队分工表

---

## 🎯 成功标准

1. ✅ 两套数据库方案都能正常运行
2. ✅ 5 个查询场景都有性能对比数据
3. ✅ 报告覆盖所有必需章节
4. ✅ 至少 3 篇 APA 格式文献引用
5. ✅ 按时提交（2025 年 11 月 12 日晚 8 点前）

---

## 📚 参考资源

### 学术文献（建议）

1. **区块链数据分析**
   - 搜索关键词: blockchain data analytics, cryptocurrency market analysis

2. **SQL vs NoSQL 性能对比**
   - Cattell, R. (2011). Scalable SQL and NoSQL data stores. *ACM SIGMOD Record*, 39(4), 12-27.

3. **时序数据库优化**
   - 搜索关键词: time-series database optimization, partitioning strategies

### 技术文档

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [MongoDB 官方文档](https://docs.mongodb.com/)
- [Redis 官方文档](https://redis.io/documentation)
- [TimescaleDB 文档](https://docs.timescale.com/)（时序数据优化）

### 数据源

- [The Graph](https://thegraph.com/) - 区块链数据索引
- [Dune Analytics](https://dune.com/) - 链上数据分析参考
- [Uniswap v3 Subgraph](https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3)

---

## 🛠️ 技术栈

| 组件 | 技术选型 | 版本 | 原因 |
|------|---------|------|------|
| SQL 数据库 | PostgreSQL | 14+ | 免费、强大、支持 JSON |
| NoSQL 文档 | MongoDB | 5.0+ | 免费、易用、聚合管道 |
| NoSQL 缓存 | Redis | 6.0+ | 免费、高性能 |
| 编程语言 | Python | 3.8+ | 简单、库丰富 |
| 测试框架 | pytest + locust | latest | 性能测试 |
| 数据可视化 | matplotlib + pandas | latest | 生成图表 |
| 容器化 | Docker | latest | 环境一致性 |

---

## ⚠️ 风险缓解

| 风险 | 缓解措施 | 状态 |
|------|---------|------|
| 真实数据获取困难 | 使用合成数据生成器，模拟真实分布 | ✅ |
| NoSQL 组没经验 | 提供详细的 MongoDB/Redis 教程链接 | ✅ |
| 时间不够 | 简化到 7 个实体，5 个查询 | ✅ |
| 硬件限制 | Docker 本地部署，数据量控制在 10 万条 | ✅ |
| 报告写不完 | 提供模板，每人负责特定章节 | 📝 |

---

## 📈 预期实验结果

基于 SQL vs NoSQL 特性，我们预期：

| 场景 | SQL 优势 | NoSQL 优势 | 预期赢家 |
|------|---------|-----------|---------|
| Q1: 点查询 | 索引 B 树 | Redis 缓存 | **NoSQL** |
| Q2: 范围查询 | 分区表 | 灵活分片 | **平手** |
| Q3: 聚合查询 | 优化器强大 | 聚合管道 | **SQL** |
| Q4: 复杂 JOIN | 原生支持 | 需应用层 | **SQL** |
| Q5: 批量写入 | MVCC 开销 | 写优化 | **NoSQL** |

**总体结论**（预期）:
- **SQL 适合**: 复杂查询、强一致性、OLAP 分析
- **NoSQL 适合**: 高并发写入、点查询、灵活 schema

---

## 📄 许可证

MIT License
