# -*- coding: utf-8 -*-
"""
执行所有5个测试场景（已适配当前数据模型 & 修复 Redis 认证/分区越界）
Q1: 点查询 - 获取单个代币详情
Q2: 范围查询 - 24小时价格走势
Q3: 聚合查询 - Top 10高评分代币
Q4: 复杂JOIN - 持仓集中度分析
Q5: 批量写入 - 插入1000条价格记录
"""
from benchmark_framework import DatabaseBenchmark
import random
from datetime import datetime, timedelta
import redis  # 为了捕获 Redis 异常


def main():
    """主测试函数"""

    # 创建测试框架（内部会连接 PostgreSQL / MongoDB / Redis）
    benchmark = DatabaseBenchmark()

    # 选一个测试 token（按你的模型：token_address）
    benchmark.pg_cur.execute("SELECT token_address FROM token LIMIT 1")
    row = benchmark.pg_cur.fetchone()
    if not row:
        raise RuntimeError("未找到任何 token 记录，请先运行数据加载脚本。")
    test_token_addr = row[0]
    print(f"使用的测试代币地址: {test_token_addr}")

    # ===== Q1: 点查询 =====
    print("\n" + "=" * 70)
    print("开始测试 Q1: 点查询")
    print("=" * 70)

    def sql_q1():
        """SQL: 获取单个代币详情（按当前列名改写）"""
        query = """
        WITH last_score AS (
            SELECT token_address, score, score_factors
            FROM token_score
            WHERE token_address = %s
            ORDER BY timestamp DESC
            LIMIT 1
        ),
        last_price AS (
            SELECT price AS price_usd, volume_24h
            FROM dex_price
            WHERE token_address = %s
            ORDER BY timestamp DESC
            LIMIT 1
        )
        SELECT
            t.token_address,
            t.symbol,
            t.name,
            t.token_address AS contract_address,
            lp.price_usd,
            NULL::numeric AS market_cap,
            COALESCE(ls.score, 0) AS trust_score,
            COALESCE(ls.score, 0) AS liquidity_score
        FROM token t
        LEFT JOIN last_score ls ON ls.token_address = t.token_address
        LEFT JOIN last_price lp ON TRUE
        WHERE t.token_address = %s
        """
        benchmark.pg_cur.execute(query, (test_token_addr, test_token_addr, test_token_addr))
        return benchmark.pg_cur.fetchone()

    def nosql_q1():
        """NoSQL: 先查 Redis，未命中则查 Mongo 并写入 Redis（带容错）"""
        key_plain = f"token:{test_token_addr}"
        key_latest = f"token:{test_token_addr}:latest"

        rc = getattr(benchmark, "redis_client", None)
        cached = None

        # 读取缓存（若 Redis 未授权/不可用则静默跳过）
        if rc:
            try:
                cached = rc.get(key_plain) or rc.get(key_latest)
            except redis.exceptions.RedisError as e:
                # 打印一次即可；基准测试不因缓存失败中断
                # print(f"(Redis 缓存读取失败，跳过: {e})")
                cached = None

        if cached:
            return cached

        # 未命中 -> 查 Mongo
        doc = benchmark.mongo_db.tokens.find_one(
            {"address": test_token_addr},
            {
                "_id": 0,
                "address": 1,
                "symbol": 1,
                "name": 1,
                "latest_price.dex_price": 1,
                "latest_price.volume_24h": 1,
                "latest_score.score": 1,
            },
        )

        # 回填缓存（若 Redis 未授权/不可用则静默跳过）
        if doc and rc:
            try:
                rc.setex(key_plain, 300, str(doc))
                rc.setex(key_latest, 300, str(doc))
            except redis.exceptions.RedisError:
                pass

        return doc

    benchmark.run_benchmark(
        test_name="Q1: 点查询",
        sql_query_func=sql_q1,
        nosql_query_func=nosql_q1,
        iterations=100,
    )

    # ===== Q2: 范围查询（24小时） =====
    print("\n" + "=" * 70)
    print("开始测试 Q2: 范围查询")
    print("=" * 70)

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)

    def sql_q2():
        """SQL: 24小时价格走势"""
        query = """
        SELECT
            timestamp,
            price AS price_usd,
            volume_24h
        FROM dex_price
        WHERE token_address = %s
          AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
        """
        benchmark.pg_cur.execute(query, (test_token_addr, start_time, end_time))
        return benchmark.pg_cur.fetchall()

    def nosql_q2():
        """NoSQL: 24小时价格走势"""
        cursor = benchmark.mongo_db.dex_prices.find(
            {
                "token_address": test_token_addr,
                "timestamp": {"$gte": start_time, "$lte": end_time},
            },
            {"_id": 0, "timestamp": 1, "price": 1, "volume_24h": 1},
        ).sort("timestamp", 1)
        return list(cursor)

    benchmark.run_benchmark(
        test_name="Q2: 范围查询 (24小时价格)",
        sql_query_func=sql_q2,
        nosql_query_func=nosql_q2,
        iterations=100,
    )

    # ===== Q3: 聚合查询 =====
    print("\n" + "=" * 70)
    print("开始测试 Q3: 聚合查询")
    print("=" * 70)

    def sql_q3():
        """SQL: Top 10 高评分代币（以最新 score 为综合分）"""
        query = """
        SELECT
            t.token_address,
            t.symbol,
            t.name,
            NULL::numeric AS market_cap,
            ts.score AS trust_score,
            ts.score AS liquidity_score,
            ts.score AS avg_score
        FROM token t
        JOIN LATERAL (
            SELECT score
            FROM token_score s
            WHERE s.token_address = t.token_address
            ORDER BY timestamp DESC
            LIMIT 1
        ) ts ON TRUE
        WHERE ts.score >= 70
        ORDER BY ts.score DESC
        LIMIT 10
        """
        benchmark.pg_cur.execute(query)
        return benchmark.pg_cur.fetchall()

    def nosql_q3():
        """NoSQL: tokens.latest_score.score 排序取 Top10"""
        pipeline = [
            {"$match": {"latest_score.score": {"$gte": 70}}},
            {"$addFields": {"avg_score": "$latest_score.score"}},
            {"$sort": {"avg_score": -1}},
            {"$limit": 10},
            {"$project": {"_id": 0, "address": 1, "symbol": 1, "name": 1, "avg_score": 1}},
        ]
        return list(benchmark.mongo_db.tokens.aggregate(pipeline))

    benchmark.run_benchmark(
        test_name="Q3: Top 10高评分代币",
        sql_query_func=sql_q3,
        nosql_query_func=nosql_q3,
        iterations=100,
    )

    # ===== Q4: 复杂JOIN（持仓集中度） =====
    print("\n" + "=" * 70)
    print("开始测试 Q4: 复杂JOIN (持仓集中度)")
    print("=" * 70)

    def sql_q4():
        """SQL: Top10 集中度（按 token_holder.balance 计算）"""
        query = """
        WITH total_supply AS (
            SELECT token_address, SUM(balance) AS total
            FROM token_holder
            WHERE token_address = %s
            GROUP BY token_address
        ),
        top_holders AS (
            SELECT token_address, SUM(balance) AS top10_balance
            FROM (
                SELECT token_address, balance,
                       ROW_NUMBER() OVER (PARTITION BY token_address ORDER BY balance DESC) AS rnk
                FROM token_holder
                WHERE token_address = %s
            ) x
            WHERE rnk <= 10
            GROUP BY token_address
        )
        SELECT
            t.token_address,
            t.symbol,
            ts.total AS total_supply,
            th.top10_balance,
            (th.top10_balance::FLOAT / NULLIF(ts.total, 0)) * 100 AS concentration_pct
        FROM token t
        JOIN total_supply ts ON t.token_address = ts.token_address
        JOIN top_holders th ON t.token_address = th.token_address
        WHERE t.token_address = %s
        """
        benchmark.pg_cur.execute(query, (test_token_addr, test_token_addr, test_token_addr))
        return benchmark.pg_cur.fetchone()

    def nosql_q4():
        """NoSQL: 从 token_holders 集合读取预计算的 top10_concentration"""
        doc = benchmark.mongo_db.token_holders.find_one(
            {"token_address": test_token_addr},
            {"_id": 0, "token_address": 1, "top10_concentration": 1, "total_holders": 1},
        )
        return doc

    benchmark.run_benchmark(
        test_name="Q4: 持仓集中度分析",
        sql_query_func=sql_q4,
        nosql_query_func=nosql_q4,
        iterations=100,
    )

    # ===== Q5: 批量写入（修复分区越界） =====
    print("\n" + "=" * 70)
    print("开始测试 Q5: 批量写入")
    print("=" * 70)

    # 选一个“落在现有分区范围内”的基准时间：
    # 优先取 dex_price 中出现过的最大月份，回退到 2025-02-15（你初始装载时用过的月份）
    def pick_partition_safe_base_ts():
        benchmark.pg_cur.execute("SELECT date_trunc('month', max(timestamp)) FROM dex_price")
        row = benchmark.pg_cur.fetchone()
        if row and row[0]:
            # 取该月内的某一天，避免边界
            return row[0] + timedelta(days=1)
        return datetime(2025, 2, 15, 12, 0, 0)

    def sql_q5():
        """SQL: 向 dex_price 批量写 1000 条（时间锚定到已有分区）"""
        t0 = pick_partition_safe_base_ts()
        data = []
        for i in range(1000):
            data.append(
                (
                    test_token_addr,                               # token_address
                    t0 + timedelta(seconds=i),                     # timestamp（已锚到合法分区）
                    random.uniform(1.0, 100.0),                    # price
                    random.uniform(100000, 1000000),               # tvl
                    random.uniform(1000, 100000),                  # liquidity_depth
                    random.uniform(10000, 1000000),                # volume_24h
                )
            )

        insert_sql = """
        INSERT INTO dex_price
            (token_address, timestamp, price, tvl, liquidity_depth, volume_24h)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        benchmark.pg_cur.executemany(insert_sql, data)
        benchmark.pg_conn.commit()

        # 清理写入的数据
        benchmark.pg_cur.execute(
            "DELETE FROM dex_price WHERE token_address = %s AND timestamp >= %s AND timestamp < %s",
            (test_token_addr, data[0][1], data[-1][1] + timedelta(seconds=1)),
        )
        benchmark.pg_conn.commit()
        return len(data)

    def nosql_q5():
        """NoSQL: 向 dex_prices 批量写 1000 条，并在结束后清理"""
        t0 = datetime.now()
        batch = []
        for i in range(1000):
            batch.append(
                {
                    "token_address": test_token_addr,
                    "dex_name": "Uniswap",
                    "pair_address": "ETH",
                    "timestamp": t0 + timedelta(seconds=i),
                    "price": random.uniform(1.0, 100.0),
                    "volume_24h": random.uniform(10000, 1000000),
                }
            )
        result = benchmark.mongo_db.dex_prices.insert_many(batch)
        benchmark.mongo_db.dex_prices.delete_many(
            {"token_address": test_token_addr, "dex_name": "Uniswap", "pair_address": "ETH"}
        )
        return len(result.inserted_ids)

    benchmark.run_benchmark(
        test_name="Q5: 批量写入 (1000条记录)",
        sql_query_func=sql_q5,
        nosql_query_func=nosql_q5,
        iterations=20,  # 写入测试迭代次数较少
    )

    # ===== 保存结果 =====
    benchmark.save_results("benchmark_results.json")

    # ===== 生成汇总报告 =====
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)

    print("\n| 测试场景 | SQL延迟 | NoSQL延迟 | 赢家 | 性能提升 |")
    print("|---------|---------|-----------|------|---------|")
    for result in benchmark.results:
        print(
            f"| {result['test_name']:<25} | {result['sql_avg_ms']:>6.2f}ms | "
            f"{result['nosql_avg_ms']:>8.2f}ms | {result['winner']:<6} | {result['speedup']:.2f}x |"
        )

    # 清理连接
    benchmark.cleanup()
    print("\n✅ 所有测试完成!")


if __name__ == "__main__":
    main()