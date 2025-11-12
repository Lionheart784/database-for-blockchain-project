# 区块链代币分析系统 - SQL vs NoSQL 性能对比实验

---

## 📌 项目概述

### 项目定位

这是一个**学术实验项目**，旨在通过真实的商业场景来对比 SQL 和 NoSQL 数据库的性能特点。

### 核心目标

1. ✅ 设计一个真实的区块链代币分析系统数据库
2. ✅ 实现 **PostgreSQL (SQL)** 和 **MongoDB + Redis (NoSQL)** 两套方案
3. ✅ 对比两种方案在不同查询场景下的性能表现

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

## 🧪 实验设计

### 5 个关键查询场景

| 场景 | 查询类型 | 业务场景 | 预期赢家 |
|-----|---------|---------|---------|
| **Q1** | 点查询 | 获取单个代币最新信息 | NoSQL (Redis) |
| **Q2** | 范围查询 | 获取价格历史走势 | 平手 |
| **Q3** | 聚合查询 | Top 10 高评分代币 | SQL |
| **Q4** | 复杂 JOIN | 持仓集中度分析 | SQL |
| **Q5** | 批量写入 | 每分钟更新 1000 个代币价格 | NoSQL |


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

---

## 📄 许可证

MIT License
