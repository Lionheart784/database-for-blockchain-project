"""
执行所有5个测试场景
Q1: 点查询 - 获取单个代币详情
Q2: 范围查询 - 24小时价格走势
Q3: 聚合查询 - Top 10高评分代币
Q4: 复杂JOIN - 持仓集中度分析
Q5: 批量写入 - 插入1000条价格记录
"""

from benchmark_framework import DatabaseBenchmark
import random
from datetime import datetime, timedelta

def main():
    """主测试函数"""

    # 创建测试框架
    benchmark = DatabaseBenchmark()

    # 获取测试数据的ID
    benchmark.pg_cur.execute("SELECT token_id FROM TOKEN LIMIT 1")
    test_token_id = benchmark.pg_cur.fetchone()[0]

    print(f"使用的测试代币ID: {test_token_id}")

    # ===== Q1: 点查询 =====
    print("\n" + "="*70)
    print("开始测试 Q1: 点查询")
    print("="*70)

    def sql_q1():
        """SQL: 获取单个代币详情"""
        query = """
        SELECT
            t.token_id,
            t.symbol,
            t.name,
            t.contract_address,
            t.current_price,
            t.market_cap,
            ts.trust_score,
            ts.liquidity_score
        FROM TOKEN t
        LEFT JOIN TOKEN_SCORE ts ON t.token_id = ts.token_id
        WHERE t.token_id = %s
        """
        benchmark.pg_cur.execute(query, (test_token_id,))
        return benchmark.pg_cur.fetchone()

    def nosql_q1():
        """NoSQL: 从Redis缓存获取代币详情"""
        # 先尝试从Redis获取
        cache_key = f"token:{test_token_id}"
        cached = benchmark.redis_client.get(cache_key)

        if cached:
            return cached

        # Redis未命中，从MongoDB获取
        token = benchmark.mongo_db.tokens.find_one(
            {"token_id": test_token_id},
            {
                "token_id": 1,
                "symbol": 1,
                "name": 1,
                "contract_address": 1,
                "current_price": 1,
                "market_cap": 1,
                "trust_score": 1,
                "liquidity_score": 1
            }
        )

        # 写入Redis缓存
        if token:
            benchmark.redis_client.setex(
                cache_key,
                300,  # TTL 5分钟
                str(token)
            )

        return token

    benchmark.run_benchmark(
        test_name="Q1: 点查询",
        sql_query_func=sql_q1,
        nosql_query_func=nosql_q1,
        iterations=100
    )

    # ===== Q2: 范围查询 =====
    print("\n" + "="*70)
    print("开始测试 Q2: 范围查询")
    print("="*70)

    # 计算24小时前的时间
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)

    def sql_q2():
        """SQL: 获取24小时价格走势"""
        query = """
        SELECT
            timestamp,
            price_usd,
            volume_24h
        FROM DEX_PRICE
        WHERE token_id = %s
          AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
        """
        benchmark.pg_cur.execute(query, (test_token_id, start_time, end_time))
        return benchmark.pg_cur.fetchall()

    def nosql_q2():
        """NoSQL: 从MongoDB获取24小时价格走势"""
        prices = benchmark.mongo_db.dex_prices.find(
            {
                "token_id": test_token_id,
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            },
            {
                "timestamp": 1,
                "price_usd": 1,
                "volume_24h": 1
            }
        ).sort("timestamp", 1)

        return list(prices)

    benchmark.run_benchmark(
        test_name="Q2: 范围查询 (24小时价格)",
        sql_query_func=sql_q2,
        nosql_query_func=nosql_q2,
        iterations=100
    )

    # ===== Q3: 聚合查询 =====
    print("\n" + "="*70)
    print("开始测试 Q3: 聚合查询")
    print("="*70)

    def sql_q3():
        """SQL: Top 10高评分代币"""
        query = """
        SELECT
            t.token_id,
            t.symbol,
            t.name,
            t.market_cap,
            ts.trust_score,
            ts.liquidity_score,
            (ts.trust_score + ts.liquidity_score) / 2 as avg_score
        FROM TOKEN t
        JOIN TOKEN_SCORE ts ON t.token_id = ts.token_id
        WHERE ts.trust_score >= 7.0
          AND ts.liquidity_score >= 7.0
        ORDER BY avg_score DESC
        LIMIT 10
        """
        benchmark.pg_cur.execute(query)
        return benchmark.pg_cur.fetchall()

    def nosql_q3():
        """NoSQL: 使用聚合管道获取Top 10"""
        pipeline = [
            # 过滤条件
            {
                "$match": {
                    "trust_score": {"$gte": 7.0},
                    "liquidity_score": {"$gte": 7.0}
                }
            },
            # 计算平均分
            {
                "$addFields": {
                    "avg_score": {
                        "$divide": [
                            {"$add": ["$trust_score", "$liquidity_score"]},
                            2
                        ]
                    }
                }
            },
            # 排序
            {"$sort": {"avg_score": -1}},
            # 限制结果
            {"$limit": 10},
            # 投影
            {
                "$project": {
                    "token_id": 1,
                    "symbol": 1,
                    "name": 1,
                    "market_cap": 1,
                    "trust_score": 1,
                    "liquidity_score": 1,
                    "avg_score": 1
                }
            }
        ]

        return list(benchmark.mongo_db.tokens.aggregate(pipeline))

    benchmark.run_benchmark(
        test_name="Q3: Top 10高评分代币",
        sql_query_func=sql_q3,
        nosql_query_func=nosql_q3,
        iterations=100
    )

    # ===== Q4: 复杂JOIN =====
    print("\n" + "="*70)
    print("开始测试 Q4: 复杂JOIN (持仓集中度)")
    print("="*70)

    def sql_q4():
        """SQL: 计算持仓集中度 (Top 10持有人占比)"""
        query = """
        WITH total_supply AS (
            SELECT
                token_id,
                SUM(balance) as total
            FROM TOKEN_HOLDER
            WHERE token_id = %s
            GROUP BY token_id
        ),
        top_holders AS (
            SELECT
                token_id,
                SUM(balance) as top10_balance
            FROM (
                SELECT
                    token_id,
                    balance,
                    ROW_NUMBER() OVER (PARTITION BY token_id ORDER BY balance DESC) as rank
                FROM TOKEN_HOLDER
                WHERE token_id = %s
            ) ranked
            WHERE rank <= 10
            GROUP BY token_id
        )
        SELECT
            t.token_id,
            t.symbol,
            ts.total as total_supply,
            th.top10_balance,
            (th.top10_balance::FLOAT / ts.total) * 100 as concentration_pct
        FROM TOKEN t
        JOIN total_supply ts ON t.token_id = ts.token_id
        JOIN top_holders th ON t.token_id = th.token_id
        """
        benchmark.pg_cur.execute(query, (test_token_id, test_token_id))
        return benchmark.pg_cur.fetchone()

    def nosql_q4():
        """NoSQL: 从预计算字段获取集中度"""
        # MongoDB方案中已经预计算了top10_concentration字段
        token = benchmark.mongo_db.tokens.find_one(
            {"token_id": test_token_id},
            {
                "token_id": 1,
                "symbol": 1,
                "total_supply": 1,
                "top10_concentration": 1
            }
        )
        return token

    benchmark.run_benchmark(
        test_name="Q4: 持仓集中度分析",
        sql_query_func=sql_q4,
        nosql_query_func=nosql_q4,
        iterations=100
    )

    # ===== Q5: 批量写入 =====
    print("\n" + "="*70)
    print("开始测试 Q5: 批量写入")
    print("="*70)

    def sql_q5():
        """SQL: 批量插入1000条价格记录"""
        # 生成测试数据
        data = []
        for i in range(1000):
            data.append((
                test_token_id,
                "Uniswap",
                "ETH",
                datetime.now() + timedelta(seconds=i),
                random.uniform(1.0, 100.0),
                random.uniform(10000, 1000000)
            ))

        # 批量插入
        insert_query = """
        INSERT INTO DEX_PRICE (token_id, dex_name, pair_address, timestamp, price_usd, volume_24h)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        benchmark.pg_cur.executemany(insert_query, data)
        benchmark.pg_conn.commit()

        # 清理测试数据
        benchmark.pg_cur.execute(
            "DELETE FROM DEX_PRICE WHERE token_id = %s AND dex_name = 'Uniswap' AND pair_address = 'ETH'",
            (test_token_id,)
        )
        benchmark.pg_conn.commit()

        return len(data)

    def nosql_q5():
        """NoSQL: 批量插入1000条价格记录"""
        # 生成测试数据
        data = []
        for i in range(1000):
            data.append({
                "token_id": test_token_id,
                "dex_name": "Uniswap",
                "pair_address": "ETH",
                "timestamp": datetime.now() + timedelta(seconds=i),
                "price_usd": random.uniform(1.0, 100.0),
                "volume_24h": random.uniform(10000, 1000000)
            })

        # 批量插入
        result = benchmark.mongo_db.dex_prices.insert_many(data)

        # 清理测试数据
        benchmark.mongo_db.dex_prices.delete_many({
            "token_id": test_token_id,
            "dex_name": "Uniswap",
            "pair_address": "ETH"
        })

        return len(result.inserted_ids)

    benchmark.run_benchmark(
        test_name="Q5: 批量写入 (1000条记录)",
        sql_query_func=sql_q5,
        nosql_query_func=nosql_q5,
        iterations=20  # 写入测试迭代次数较少
    )

    # ===== 保存结果 =====
    benchmark.save_results("benchmark_results.json")

    # ===== 生成汇总报告 =====
    print("\n" + "="*70)
    print("测试汇总")
    print("="*70)

    print("\n| 测试场景 | SQL延迟 | NoSQL延迟 | 赢家 | 性能提升 |")
    print("|---------|---------|-----------|------|---------|")

    for result in benchmark.results:
        print(f"| {result['test_name']:<25} | {result['sql_avg_ms']:>6.2f}ms | {result['nosql_avg_ms']:>8.2f}ms | {result['winner']:<6} | {result['speedup']:.2f}x |")

    # 清理连接
    benchmark.cleanup()

    print("\n✅ 所有测试完成!")

if __name__ == "__main__":
    main()