#!/usr/bin/env python3
"""
NoSQL查询实现脚本 - NoSQL组员2
功能: 实现5个关键查询并测量性能
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pymongo import MongoClient
import redis
import time

# Database configuration with Docker service names
MONGO_CONFIG = {
    "host": os.getenv("MONGO_HOST", "token-analyzer-mongo"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "username": os.getenv("MONGO_USER", "admin"),
    "password": os.getenv("MONGO_PASS", "123456789"),
    "database": os.getenv("MONGO_DB", "token_analyzer"),
    "authSource": os.getenv("MONGO_AUTHSOURCE", "admin")
}

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "token-analyzer-redis"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "password": os.getenv("REDIS_PASS", "yourpassword"),
    "decode_responses": True
}

# 全局连接
mongo_client = None
db = None
redis_client = None

# ============================================================================
# 辅助函数
# ============================================================================

def init_connections():
    """初始化数据库连接"""
    global mongo_client, db, redis_client

    try:
        # 创建MongoDB连接
        mongo_client = MongoClient(
            host=MONGO_CONFIG["host"],
            port=MONGO_CONFIG["port"],
            username=MONGO_CONFIG["username"],
            password=MONGO_CONFIG["password"],
            authSource=MONGO_CONFIG["authSource"]
        )
        db = mongo_client[MONGO_CONFIG["database"]]
        # 测试连接
        mongo_client.server_info()
        print("✓ MongoDB连接成功")
    except Exception as e:
        print(f"✗ MongoDB连接失败: {str(e)}")
        raise

    try:
        redis_client = redis.Redis(**REDIS_CONFIG)
        redis_client.ping()
        print("✓ Redis连接成功")
    except Exception as e:
        print(f"✗ Redis连接失败: {str(e)}")
        raise

def benchmark_query(name: str, query_func, iterations: int = 100) -> Dict[str, Any]:
    """
    执行查询并测量性能

    参数:
        name: 查询名称
        query_func: 查询函数
        iterations: 测试迭代次数

    返回:
        性能统计字典
    """
    # 预热查询
    result = query_func()
    result_count = len(result) if isinstance(result, list) else 1

    # 正式测试
    latencies = []
    for _ in range(iterations):
        start = time.time()
        query_func()
        latency = (time.time() - start) * 1000  # 转换为毫秒
        latencies.append(latency)

    # 计算统计指标
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    min_latency = min(latencies)
    max_latency = max(latencies)

    # 打印结果
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    print(f"返回结果数:   {result_count}")
    print(f"平均延迟:     {avg_latency:.2f} ms")
    print(f"P95延迟:      {p95_latency:.2f} ms")
    print(f"最小延迟:     {min_latency:.2f} ms")
    print(f"最大延迟:     {max_latency:.2f} ms")
    print(f"测试迭代:     {iterations} 次")

    return {
        "query_name": name,
        "result_count": result_count,
        "avg_latency_ms": round(avg_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "min_latency_ms": round(min_latency, 2),
        "max_latency_ms": round(max_latency, 2),
        "iterations": iterations
    }

# ============================================================================
# Q1: 点查询 - 获取单个代币最新信息（使用Redis缓存）
# ============================================================================

def query_q1_point_lookup():
    """
    Q1: 点查询 - 获取单个代币的最新信息

    业务场景: 用户查看代币详情页
    预期性能: < 5ms (Redis缓存)

    NoSQL优势:
    1. Redis缓存提供超低延迟
    2. MongoDB内嵌文档，无需JOIN
    3. 一次查询获取所有信息
    """
    # 获取示例token地址
    sample_token = db.tokens.find_one()
    token_address = sample_token["address"]

    def query():
        # 策略1: 先查Redis缓存
        cache_key = f"token:{token_address}:latest"
        cached = redis_client.get(cache_key)

        if cached:
            # 缓存命中（超快！）
            return json.loads(cached)

        # 策略2: 缓存未命中，查MongoDB
        token = db.tokens.find_one(
            {"address": token_address},
            {
                "symbol": 1,
                "name": 1,
                "latest_price": 1,
                "latest_score": 1,
                "project": 1,
                "_id": 0
            }
        )

        if token:
            # 更新缓存（5分钟TTL）
            cache_data = {
                "symbol": token["symbol"],
                "name": token["name"],
                "price": token["latest_price"]["dex_price"],
                "tvl": token["latest_price"]["tvl"],
                "score": token["latest_score"]["score"],
                "github_stars": token.get("project", {}).get("stars", 0)
            }
            redis_client.setex(cache_key, 300, json.dumps(cache_data))

            return cache_data

        return None

    return benchmark_query(
        "Q1: 点查询 - 单个代币最新信息 (Redis缓存)",
        lambda: [query()],
        iterations=100
    )

# ============================================================================
# Q2: 范围查询 - 获取价格历史走势
# ============================================================================

def query_q2_range_query():
    """
    Q2: 范围查询 - 获取某代币过去24小时的价格走势

    业务场景: 显示价格K线图
    预期性能: < 100ms

    NoSQL优势:
    1. MongoDB对时序数据查询优化良好
    2. 索引(token_address, timestamp)加速查询
    """
    # 获取示例token地址
    sample_token = db.tokens.find_one()
    token_address = sample_token["address"]

    def query():
        # 查询过去24小时的价格
        start_time = datetime.now() - timedelta(hours=24)

        cursor = db.dex_prices.find(
            {
                "token_address": token_address,
                "timestamp": {"$gte": start_time}
            },
            {
                "timestamp": 1,
                "price": 1,
                "tvl": 1,
                "volume_24h": 1,
                "_id": 0
            }
        ).sort("timestamp", -1)  # -1表示降序

        return list(cursor)

    return benchmark_query(
        "Q2: 范围查询 - 24小时价格历史",
        query,
        iterations=100
    )

# ============================================================================
# Q3: 聚合查询 - Top 10高评分代币
# ============================================================================

def query_q3_aggregation():
    """
    Q3: 聚合查询 - 获取评分最高的10个代币

    业务场景: 首页推荐列表
    预期性能: < 50ms

    NoSQL优势:
    1. 内嵌latest_score字段，无需JOIN
    2. 直接排序和限制，无需子查询
    3. 索引(latest_score.score)加速排序
    """
    def query():
        # 先尝试从Redis获取
        cached = redis_client.get("tokens:top10")
        if cached:
            return json.loads(cached)

        # 查询MongoDB
        cursor = db.tokens.find(
            {},
            {
                "address": 1,
                "symbol": 1,
                "name": 1,
                "latest_score.score": 1,
                "latest_price.tvl": 1,
                "latest_price.volume_24h": 1,
                "project.github_stars": 1,
                "_id": 0
            }
        ).sort("latest_score.score", -1).limit(10)

        results = list(cursor)

        # 缓存结果（10分钟TTL）
        redis_client.setex("tokens:top10", 600, json.dumps(results, default=str))

        return results

    return benchmark_query(
        "Q3: 聚合查询 - Top 10高评分代币",
        query,
        iterations=50
    )

# ============================================================================
# Q4: 复杂查询 - 持仓集中度分析（利用预计算字段）
# ============================================================================

def query_q4_complex_aggregation():
    """
    Q4: 复杂查询 - 分析持仓集中度，识别高风险代币

    业务场景: 风险预警系统
    预期性能: < 100ms

    NoSQL优势:
    1. 使用预计算的top10_concentration字段
    2. 避免实时GROUP BY聚合
    3. 一次查询获取结果
    """
    def query():
        # 使用聚合管道（类似SQL的JOIN）
        pipeline = [
            # 筛选：集中度 > 30%
            {
                "$match": {
                    "top10_concentration": {"$gt": 30}
                }
            },
            # 关联tokens集合获取代币信息
            {
                "$lookup": {
                    "from": "tokens",
                    "localField": "token_address",
                    "foreignField": "address",
                    "as": "token_info"
                }
            },
            # 展开数组
            {"$unwind": "$token_info"},
            # 选择需要的字段
            {
                "$project": {
                    "token_address": 1,
                    "symbol": "$token_info.symbol",
                    "name": "$token_info.name",
                    "top10_concentration": 1,
                    "top20_concentration": 1,
                    "total_holders": 1,
                    "_id": 0
                }
            },
            # 排序
            {"$sort": {"top10_concentration": -1}},
            # 限制结果
            {"$limit": 20}
        ]

        return list(db.token_holders.aggregate(pipeline))

    return benchmark_query(
        "Q4: 复杂查询 - 持仓集中度分析 (预计算优化)",
        query,
        iterations=50
    )

# ============================================================================
# Q5: 批量写入测试
# ============================================================================

def query_q5_batch_insert():
    """
    Q5: 批量写入 - 模拟每分钟更新1000个代币价格

    业务场景: 实时价格更新
    预期性能: < 1000ms/1000条

    NoSQL优势:
    1. MongoDB批量写入性能优秀
    2. 无需维护MVCC（多版本并发控制）
    3. 可以异步更新Redis缓存
    """
    print(f"\n{'='*60}")
    print("Q5: 批量写入测试 - 插入1000条价格记录")
    print(f"{'='*60}")

    # 获取示例token地址
    sample_token = db.tokens.find_one()
    token_address = sample_token["address"]

    # 准备测试数据
    test_data = []
    base_price = 100.0
    timestamp_base = datetime.now()

    for i in range(1000):
        price = base_price + i * 0.1
        tvl = price * 1000000
        liquidity_depth = tvl * 0.05
        volume_24h = tvl * 0.2
        timestamp = timestamp_base + timedelta(seconds=i)
        hour = timestamp.replace(minute=0, second=0, microsecond=0)

        test_data.append({
            "token_address": token_address,
            "price": round(price, 8),
            "tvl": round(tvl, 2),
            "liquidity_depth": round(liquidity_depth, 2),
            "volume_24h": round(volume_24h, 2),
            "timestamp": timestamp,
            "hour": hour
        })

    # 测试批量插入性能
    start = time.time()
    db.dex_prices.insert_many(test_data)
    total_time = (time.time() - start) * 1000  # 转换为毫秒

    # 同步更新Redis缓存（可选）
    cache_key = f"token:{token_address}:latest"
    latest_data = {
        "symbol": sample_token["symbol"],
        "price": test_data[-1]["price"],
        "tvl": test_data[-1]["tvl"],
        "timestamp": str(test_data[-1]["timestamp"])
    }
    redis_client.setex(cache_key, 300, json.dumps(latest_data))

    print(f"批量插入1000条:   {total_time:.2f} ms")
    print(f"平均每条:         {total_time/1000:.2f} ms")
    print(f"吞吐量:          {1000/(total_time/1000):.0f} 条/秒")

    return {
        "query_name": "Q5: 批量写入测试",
        "total_time_ms": round(total_time, 2),
        "per_record_ms": round(total_time/1000, 2),
        "throughput_per_sec": round(1000/(total_time/1000), 0)
    }

# ============================================================================
# 主程序
# ============================================================================

def main():
    """运行所有查询测试"""

    print("\n" + "="*60)
    print("NoSQL查询性能测试开始")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库: MongoDB + Redis")

    # 初始化连接
    print("\n初始化数据库连接...")
    init_connections()
    print("✓ 连接成功")

    # 存储所有测试结果
    results = []

    try:
        # 执行5个查询
        results.append(query_q1_point_lookup())
        results.append(query_q2_range_query())
        results.append(query_q3_aggregation())
        results.append(query_q4_complex_aggregation())
        results.append(query_q5_batch_insert())

        # 总结
        print("\n" + "="*60)
        print("测试完成！汇总结果:")
        print("="*60)

        for result in results:
            print(f"\n{result['query_name']}:")
            if 'avg_latency_ms' in result:
                print(f"  平均延迟: {result['avg_latency_ms']} ms")
                print(f"  P95延迟:  {result['p95_latency_ms']} ms")
                print(f"  返回行数: {result['result_count']}")
            else:
                print(f"  总时间:   {result['total_time_ms']} ms")
                print(f"  吞吐量:   {result['throughput_per_sec']} 条/秒")

        # 保存结果到JSON文件
        output = {
            'test_time': datetime.now().isoformat(),
            'database': 'MongoDB + Redis',
            'results': results
        }

        with open('nosql_query_results.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\n✅ 结果已保存到 nosql_query_results.json")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 关闭连接
        if mongo_client:
            mongo_client.close()

if __name__ == "__main__":
    main()
