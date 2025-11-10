# -*- coding: utf-8 -*-
"""
把“同一套数据”同时写入 PostgreSQL 与 MongoDB（口径对齐）
- TOKEN:         100 个
- DEX_PRICE:     每个 TOKEN 1000 条（15min 间隔，落于 2025-02）
- CEX_PRICE:     每个 TOKEN 固定 3 家交易所 × 100 条
- TOKEN_HOLDER:  每个 TOKEN 20 行（Mongo 也是“每行一持仓人”，与 SQL 口径一致）
运行后直接执行 validate_data.py，可得到完全一致的计数。
"""

import os, random, json
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_batch
from pymongo import MongoClient

# ========= 配置 =========
CLEAR_EXISTING = True  # 首次建议 True：清空后重装，确保计数严格一致
SEED = 42             # 固定随机种，保证可重复

NUM_TOKENS = 100
NUM_DEX_PER_TOKEN = 1000
NUM_CEX_POINTS_PER_EXCHANGE = 100
NUM_HOLDERS_PER_TOKEN = 20
EXCHANGES = ['Binance', 'OKX', 'Coinbase']  # 固定 3 家，避免随机差异

# PostgreSQL 连接（可用环境变量覆盖）
PG_CFG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DB", "token_analyzer"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASS", "123456"),
}

# Mongo 连接（可用环境变量覆盖）
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:123456789@localhost:27017/?authSource=admin")
MONGO_DB = os.getenv("MONGO_DB", "token_analyzer")


def generate_eth_address(rng):
    return "0x" + "".join(rng.choices("0123456789abcdef", k=40))


def generate_price_series(rng, base_price, n, volatility=0.05):
    prices = [base_price]
    for _ in range(n - 1):
        change = rng.gauss(0, volatility)
        new = max(prices[-1] * (1 + change), 0.0001)
        prices.append(new)
    return prices


def main():
    print("=" * 60)
    print("一致性数据加载器（PostgreSQL & MongoDB）")
    print("=" * 60)

    rng = random.Random(SEED)

    # ---- 连接数据库 ----
    print("\n[1/6] 连接 PostgreSQL / MongoDB ...")
    pg = psycopg2.connect(**PG_CFG)
    pg.autocommit = False
    cur = pg.cursor()

    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    mdb = mongo_client[MONGO_DB]
    print("✓ 连接成功")

    # ---- 清空旧数据（可选）----
    if CLEAR_EXISTING:
        print("\n[2/6] 清空旧数据 ...")
        # SQL：按外键依赖顺序清空
        for sql in [
            "TRUNCATE TABLE token_holder RESTART IDENTITY",
            "TRUNCATE TABLE cex_price RESTART IDENTITY",
            "TRUNCATE TABLE dex_price RESTART IDENTITY",
            "TRUNCATE TABLE token_score RESTART IDENTITY",
            "TRUNCATE TABLE token RESTART IDENTITY",
        ]:
            try:
                cur.execute(sql)
            except Exception as e:
                # 某些表可能不存在，忽略
                pg.rollback()
                pass
        pg.commit()

        # Mongo：直接清集合
        for name in ["tokens", "dex_prices", "cex_prices", "token_holders", "token_scores", "alerts"]:
            try:
                mdb[name].drop()
            except Exception:
                pass
        print("✓ 已清空")

    # ---- 生成 TOKEN ----
    print("\n[3/6] 生成 TOKEN ...")
    tokens = []
    sql_token_rows = []
    for i in range(NUM_TOKENS):
        addr = generate_eth_address(rng)
        symbol = f"TOKEN{i+1}"
        name = f"Test Token {i+1}"
        chain = rng.choice(['ETH', 'BSC', 'POLYGON', 'ARBITRUM'])
        is_proxy = rng.random() < 0.3
        is_upgradeable = rng.random() < 0.2
        tokens.append({
            "address": addr, "symbol": symbol, "name": name,
            "chain": chain, "is_proxy": is_proxy, "is_upgradeable": is_upgradeable,
            "created_at": datetime(2025,2,1,12,0,0), "updated_at": datetime(2025,2,1,12,0,0)
        })
        sql_token_rows.append((addr, symbol, name, chain, is_proxy, is_upgradeable))

    # SQL: 插入 TOKEN
    execute_batch(cur, """
        INSERT INTO token (token_address, symbol, name, chain, is_proxy, is_upgradeable)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, sql_token_rows, page_size=500)
    pg.commit()

    # Mongo: 插入 tokens（与 SQL 口径一致，不含 latest_*）
    mdb.tokens.insert_many(tokens)
    print(f"✓ TOKEN 写入完成: {len(tokens)}")

    # ---- 生成 DEX_PRICE ----
    print("\n[4/6] 生成 DEX_PRICE ...（1000/Token，落在 2025-02）")
    end_time = datetime(2025, 2, 28, 23, 45, 0)
    step = timedelta(minutes=15)
    sql_dex_rows = []
    mongo_dex_docs = []

    for t in tokens:
        base = rng.uniform(0.1, 1000)
        series = generate_price_series(rng, base, NUM_DEX_PER_TOKEN, volatility=0.05)
        for idx, price in enumerate(series):
            ts = end_time - step * (NUM_DEX_PER_TOKEN - idx - 1)
            tvl = price * rng.uniform(100000, 10000000)
            liq = tvl * rng.uniform(0.01, 0.1)
            vol = tvl * rng.uniform(0.05, 0.5)

            sql_dex_rows.append((
                t["address"], float(price), float(tvl), float(liq), float(vol), ts
            ))
            mongo_dex_docs.append({
                "token_address": t["address"],
                "price": float(price),
                "tvl": float(tvl),
                "liquidity_depth": float(liq),
                "volume_24h": float(vol),
                "timestamp": ts,
                "hour": ts.replace(minute=0, second=0, microsecond=0)
            })

    # SQL 批量
    for i in range(0, len(sql_dex_rows), 1000):
        execute_batch(cur, """
            INSERT INTO dex_price (token_address, price, tvl, liquidity_depth, volume_24h, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, sql_dex_rows[i:i+1000], page_size=500)
    pg.commit()

    # Mongo 批量
    for i in range(0, len(mongo_dex_docs), 10000):
        mdb.dex_prices.insert_many(mongo_dex_docs[i:i+10000])
    print(f"✓ DEX_PRICE 写入完成: {len(sql_dex_rows)}")

    # ---- 生成 CEX_PRICE（固定 3 交易所 × 100 点/Token）----
    print("\n[5/6] 生成 CEX_PRICE ...（3×100/Token）")
    sql_cex_rows = []
    mongo_cex_docs = []

    for t in tokens:
        symbol = t["symbol"]
        for ex in EXCHANGES:
            for j in range(NUM_CEX_POINTS_PER_EXCHANGE):
                ts = datetime(2025, 2, 15, 0, 0, 0) + timedelta(hours=j)
                spot = rng.uniform(0.1, 1000)
                fr = rng.gauss(0, 0.001)
                vol = rng.uniform(100000, 10000000)

                sql_cex_rows.append((symbol, ex, float(spot), float(fr), float(vol), ts))
                mongo_cex_docs.append({
                    "token_symbol": symbol,
                    "exchange": ex,
                    "spot_price": float(spot),
                    "funding_rate": float(fr),
                    "volume_24h": float(vol),
                    "timestamp": ts
                })

    # SQL 批量
    for i in range(0, len(sql_cex_rows), 1000):
        execute_batch(cur, """
            INSERT INTO cex_price (token_symbol, exchange, spot_price, funding_rate, volume_24h, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, sql_cex_rows[i:i+1000], page_size=500)
    pg.commit()

    # Mongo 批量
    for i in range(0, len(mongo_cex_docs), 10000):
        mdb.cex_prices.insert_many(mongo_cex_docs[i:i+10000])
    print(f"✓ CEX_PRICE 写入完成: {len(sql_cex_rows)}")

    # ---- 生成 TOKEN_HOLDER（“一行一人”口径）----
    print("\n[6/6] 生成 TOKEN_HOLDER ...（20/Token，行式存储）")
    snap_dt = datetime(2025, 2, 20, 0, 0, 0)  # Mongo 用
    today = snap_dt.date()  # Postgres 用
    sql_holder_rows = []
    mongo_holder_docs = []

    for t in tokens:
        total_supply = 1_000_000_000
        for rank in range(1, NUM_HOLDERS_PER_TOKEN + 1):
            holder = generate_eth_address(rng)
            balance = int(total_supply / (rank ** 1.5))
            pct = (balance / total_supply) * 100.0

            sql_holder_rows.append((t["address"], holder, balance, float(pct), rank, today))
            mongo_holder_docs.append({
                "token_address": t["address"],
                "holder_address": holder,
                "balance": balance,
                "percentage": float(pct),
                "rank": rank,
                "snapshot_date": snap_dt
            })

    # SQL 批量
    for i in range(0, len(sql_holder_rows), 1000):
        execute_batch(cur, """
            INSERT INTO token_holder (token_address, holder_address, balance, percentage, rank, snapshot_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, sql_holder_rows[i:i+1000], page_size=500)
    pg.commit()

    # Mongo 批量
    for i in range(0, len(mongo_holder_docs), 10000):
        mdb.token_holders.insert_many(mongo_holder_docs[i:i+10000])
    print(f"✓ TOKEN_HOLDER 写入完成: {len(sql_holder_rows)}")

    # ---- Mongo 索引（幂等）----
    mdb.tokens.create_index("address", unique=True)
    mdb.dex_prices.create_index([("token_address", 1), ("timestamp", -1)])
    mdb.cex_prices.create_index([("token_symbol", 1), ("exchange", 1), ("timestamp", -1)])
    mdb.token_holders.create_index(
        [("token_address", 1), ("holder_address", 1), ("snapshot_date", 1)], unique=True
    )

    # ---- 收尾 ----
    cur.close()
    pg.close()
    mongo_client.close()

    print("\n" + "=" * 60)
    print("✅ 同源数据加载完成！现在运行：python3 Validate/validate_data.py")
    print("=" * 60)


if __name__ == "__main__":
    main()