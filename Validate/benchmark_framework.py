"""
数据库性能基准测试框架
支持SQL和NoSQL的对比测试，自动记录性能指标
"""

import time
import psycopg2
from pymongo import MongoClient
import redis
import json
from datetime import datetime
import statistics

class DatabaseBenchmark:
    """数据库性能测试框架"""

    def __init__(self):
        """初始化数据库连接"""

        print("初始化测试框架...")

        # SQL连接
        self.pg_conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="token_analyzer",
            user="postgres",
            password="123456"
        )
        self.pg_cur = self.pg_conn.cursor()
        print("✓ PostgreSQL连接成功")

        # NoSQL连接
        self.mongo_client = MongoClient("mongodb://admin:123456789@localhost:27017/")
        self.mongo_db = self.mongo_client["token_analyzer"]
        print("✓ MongoDB连接成功")

        # Redis连接
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        print("✓ Redis连接成功")

        # 结果存储
        self.results = []
        print("✓ 框架初始化完成\n")

    def run_benchmark(self, test_name, sql_query_func, nosql_query_func, iterations=100, warmup=10):
        """
        执行性能基准测试

        Args:
            test_name: 测试场景名称
            sql_query_func: SQL查询函数
            nosql_query_func: NoSQL查询函数
            iterations: 迭代次数
            warmup: 预热次数

        Returns:
            dict: 包含详细性能指标的结果字典
        """

        print(f"\n{'='*70}")
        print(f"测试场景: {test_name}")
        print(f"{'='*70}")
        print(f"迭代次数: {iterations}, 预热次数: {warmup}")

        # ===== SQL测试 =====
        print(f"\n[SQL测试]")

        # 预热阶段
        print(f"  预热中... (执行{warmup}次)")
        for i in range(warmup):
            try:
                sql_query_func()
            except Exception as e:
                print(f"  ✗ 预热失败: {e}")
                return None

        # 正式测试
        print(f"  正式测试中... (执行{iterations}次)")
        sql_latencies = []

        for i in range(iterations):
            start = time.perf_counter()  # 使用高精度计时器
            try:
                sql_result = sql_query_func()
                latency = (time.perf_counter() - start) * 1000  # 转换为毫秒
                sql_latencies.append(latency)
            except Exception as e:
                print(f"  ✗ 第{i+1}次迭代失败: {e}")
                continue

            # 每20次显示进度
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{iterations}")

        # 计算SQL统计指标
        if not sql_latencies:
            print(f"  ✗ 没有成功的测试结果")
            return None

        sql_avg = statistics.mean(sql_latencies)
        sql_median = statistics.median(sql_latencies)
        sql_stdev = statistics.stdev(sql_latencies) if len(sql_latencies) > 1 else 0
        sql_min = min(sql_latencies)
        sql_max = max(sql_latencies)
        sql_p95 = sorted(sql_latencies)[int(len(sql_latencies) * 0.95)]
        sql_p99 = sorted(sql_latencies)[int(len(sql_latencies) * 0.99)]
        sql_qps = 1000 / sql_avg  # 每秒查询数

        print(f"\n  SQL性能:")
        print(f"    平均延迟: {sql_avg:.2f} ms")
        print(f"    中位延迟: {sql_median:.2f} ms")
        print(f"    P95延迟:  {sql_p95:.2f} ms")
        print(f"    P99延迟:  {sql_p99:.2f} ms")
        print(f"    最小延迟: {sql_min:.2f} ms")
        print(f"    最大延迟: {sql_max:.2f} ms")
        print(f"    标准差:   {sql_stdev:.2f} ms")
        print(f"    吞吐量:   {sql_qps:.2f} QPS")

        # ===== NoSQL测试 =====
        print(f"\n[NoSQL测试]")

        # 预热阶段
        print(f"  预热中... (执行{warmup}次)")
        for i in range(warmup):
            try:
                nosql_query_func()
            except Exception as e:
                print(f"  ✗ 预热失败: {e}")
                return None

        # 正式测试
        print(f"  正式测试中... (执行{iterations}次)")
        nosql_latencies = []

        for i in range(iterations):
            start = time.perf_counter()
            try:
                nosql_result = nosql_query_func()
                latency = (time.perf_counter() - start) * 1000
                nosql_latencies.append(latency)
            except Exception as e:
                print(f"  ✗ 第{i+1}次迭代失败: {e}")
                continue

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{iterations}")

        # 计算NoSQL统计指标
        if not nosql_latencies:
            print(f"  ✗ 没有成功的测试结果")
            return None

        nosql_avg = statistics.mean(nosql_latencies)
        nosql_median = statistics.median(nosql_latencies)
        nosql_stdev = statistics.stdev(nosql_latencies) if len(nosql_latencies) > 1 else 0
        nosql_min = min(nosql_latencies)
        nosql_max = max(nosql_latencies)
        nosql_p95 = sorted(nosql_latencies)[int(len(nosql_latencies) * 0.95)]
        nosql_p99 = sorted(nosql_latencies)[int(len(nosql_latencies) * 0.99)]
        nosql_qps = 1000 / nosql_avg

        print(f"\n  NoSQL性能:")
        print(f"    平均延迟: {nosql_avg:.2f} ms")
        print(f"    中位延迟: {nosql_median:.2f} ms")
        print(f"    P95延迟:  {nosql_p95:.2f} ms")
        print(f"    P99延迟:  {nosql_p99:.2f} ms")
        print(f"    最小延迟: {nosql_min:.2f} ms")
        print(f"    最大延迟: {nosql_max:.2f} ms")
        print(f"    标准差:   {nosql_stdev:.2f} ms")
        print(f"    吞吐量:   {nosql_qps:.2f} QPS")

        # ===== 对比分析 =====
        winner = "SQL" if sql_avg < nosql_avg else "NoSQL"
        speedup = max(sql_avg, nosql_avg) / min(sql_avg, nosql_avg)

        print(f"\n{'='*70}")
        print(f"🏆 赢家: {winner}")
        print(f"⚡ 性能提升: {speedup:.2f}x")
        print(f"{'='*70}")

        # 记录结果
        result = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "iterations": iterations,
            "sql_avg_ms": round(sql_avg, 2),
            "sql_median_ms": round(sql_median, 2),
            "sql_p95_ms": round(sql_p95, 2),
            "sql_p99_ms": round(sql_p99, 2),
            "sql_min_ms": round(sql_min, 2),
            "sql_max_ms": round(sql_max, 2),
            "sql_stdev_ms": round(sql_stdev, 2),
            "sql_qps": round(sql_qps, 2),
            "nosql_avg_ms": round(nosql_avg, 2),
            "nosql_median_ms": round(nosql_median, 2),
            "nosql_p95_ms": round(nosql_p95, 2),
            "nosql_p99_ms": round(nosql_p99, 2),
            "nosql_min_ms": round(nosql_min, 2),
            "nosql_max_ms": round(nosql_max, 2),
            "nosql_stdev_ms": round(nosql_stdev, 2),
            "nosql_qps": round(nosql_qps, 2),
            "winner": winner,
            "speedup": round(speedup, 2)
        }

        self.results.append(result)

        return result

    def save_results(self, filename="benchmark_results.json"):
        """保存测试结果到JSON文件"""

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 测试结果已保存到: {filename}")

    def cleanup(self):
        """清理数据库连接"""

        self.pg_conn.close()
        self.mongo_client.close()
        print("\n✓ 数据库连接已关闭")

# 使用示例
if __name__ == "__main__":
    # 创建测试框架
    benchmark = DatabaseBenchmark()

    # 示例: 测试简单查询
    def sql_test():
        benchmark.pg_cur.execute("SELECT COUNT(*) FROM TOKEN")
        return benchmark.pg_cur.fetchone()

    def nosql_test():
        return benchmark.mongo_db.tokens.count_documents({})

    # 运行测试
    benchmark.run_benchmark(
        test_name="简单计数查询",
        sql_query_func=sql_test,
        nosql_query_func=nosql_test,
        iterations=50
    )

    # 保存结果
    benchmark.save_results()

    # 清理
    benchmark.cleanup()