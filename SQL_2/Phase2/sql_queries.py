#!/usr/bin/env python3
"""
SQL查询实现脚本 - SQL组员2（修正版）
功能: 实现5个关键查询并测量性能
适配: Windows/macOS/Linux
"""

import psycopg2
import time
import json
from datetime import datetime, timedelta
import sys

# 数据库配置
DB_CONFIG = {
    "host": "",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "123456"  # ⚠️ 修改为实际密码
}

# ============================================================================
# 辅助函数
# ============================================================================

def get_connection():
    """获取数据库连接"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        print(f"❌ 数据库连接失败: {e}")
        print("请检查：")
        print("1. Docker容器是否运行")
        print("2. 密码是否正确")
        sys.exit(1)

def benchmark_query(name, query, params=None, iterations=100):
    """
    执行查询并测量性能

    参数:
        name: 查询名称
        query: SQL查询语句
        params: 查询参数（可选）
        iterations: 测试迭代次数

    返回:
        dict: 性能统计结果
    """
    conn = get_connection()
    cur = conn.cursor()

    # 预热查询（让数据进入缓存）
    try:
        cur.execute(query, params)
        results = cur.fetchall()
        result_count = len(results)
    except Exception as e:
        print(f"❌ 查询执行失败: {e}")
        cur.close()
        conn.close()
        return None

    # 正式测试
    latencies = []
    for i in range(iterations):
        start = time.time()
        cur.execute(query, params)
        cur.fetchall()  # 必须获取结果才算完整查询
        latency = (time.time() - start) * 1000  # 转换为毫秒
        latencies.append(latency)

    cur.close()
    conn.close()

    # 计算统计指标
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    min_latency = min(latencies)
    max_latency = max(latencies)

    # 打印结果
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    print(f"返回行数:     {result_count}")
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
# Q1: 点查询 - 获取单个代币最新信息
# ============================================================================

def query_q1_point_lookup():
    """
    Q1: 点查询 - 获取单个代币的最新价格、评分等信息

    业务场景: 用户查看代币详情页，需要快速加载所有最新信息
    预期性能: < 50ms
    """

    # 首先获取一个示例token地址
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT token_address FROM TOKEN LIMIT 1")
    result = cur.fetchone()
    if not result:
        print("❌ TOKEN表为空，请先加载数据")
        cur.close()
        conn.close()
        return None
    sample_token = result[0]
    cur.close()
    conn.close()

    # 查询SQL
    query = """
    SELECT
        t.token_address,
        t.symbol,
        t.name,
        t.chain,
        t.is_proxy,
        t.is_upgradeable,
        d.price as latest_dex_price,
        d.tvl,
        d.liquidity_depth,
        d.volume_24h,
        s.score as latest_score,
        s.score_factors,
        p.project_name,
        p.github_stars,
        p.commit_count_7d
    FROM TOKEN t
    LEFT JOIN LATERAL (
        SELECT price, tvl, liquidity_depth, volume_24h
        FROM DEX_PRICE
        WHERE token_address = t.token_address
        ORDER BY timestamp DESC
        LIMIT 1
    ) d ON true
    LEFT JOIN LATERAL (
        SELECT score, score_factors
        FROM TOKEN_SCORE
        WHERE token_address = t.token_address
        ORDER BY timestamp DESC
        LIMIT 1
    ) s ON true
    LEFT JOIN PROJECT p ON t.token_address = p.token_address
    WHERE t.token_address = %s;
    """

    return benchmark_query(
        "Q1: 点查询 - 单个代币最新信息",
        query,
        (sample_token,),
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
    """

    # 获取示例token
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT token_address FROM TOKEN LIMIT 1")
    result = cur.fetchone()
    if not result:
        print("❌ TOKEN表为空")
        return None
    sample_token = result[0]
    cur.close()
    conn.close()

    query = """
    SELECT
        timestamp,
        price,
        tvl,
        liquidity_depth,
        volume_24h
    FROM DEX_PRICE
    WHERE token_address = %s
      AND timestamp > NOW() - INTERVAL '24 hours'
    ORDER BY timestamp DESC;
    """

    return benchmark_query(
        "Q2: 范围查询 - 24小时价格历史",
        query,
        (sample_token,),
        iterations=100
    )

# ============================================================================
# Q3: 聚合查询 - Top 10高评分代币
# ============================================================================

def query_q3_aggregation():
    """
    Q3: 聚合查询 - 获取评分最高的10个代币

    业务场景: 首页推荐列表
    预期性能: < 200ms
    """

    query = """
    SELECT
        t.token_address,
        t.symbol,
        t.name,
        s.score as latest_score,
        d.tvl as latest_tvl,
        d.volume_24h
    FROM TOKEN t
    LEFT JOIN LATERAL (
        SELECT score
        FROM TOKEN_SCORE
        WHERE token_address = t.token_address
        ORDER BY timestamp DESC
        LIMIT 1
    ) s ON true
    LEFT JOIN LATERAL (
        SELECT tvl, volume_24h
        FROM DEX_PRICE
        WHERE token_address = t.token_address
        ORDER BY timestamp DESC
        LIMIT 1
    ) d ON true
    WHERE s.score IS NOT NULL
    ORDER BY s.score DESC
    LIMIT 10;
    """

    return benchmark_query(
        "Q3: 聚合查询 - Top 10 高评分代币",
        query,
        None,
        iterations=100
    )

# ============================================================================
# Q4: 复杂JOIN - 代币风险分析
# ============================================================================

def query_q4_complex_join():
    """
    Q4: 复杂JOIN查询 - 综合风险分析

    业务场景: 风险评估报告
    预期性能: < 500ms
    """

    query = """
    SELECT
        t.symbol,
        t.name,
        t.is_proxy,
        t.is_upgradeable,
        AVG(d.price) as avg_price_7d,
        STDDEV(d.price) as price_volatility,
        MAX(h.percentage) as max_holder_percentage,
        COUNT(DISTINCT h.holder_address) as top_holder_count,
        s.score as latest_score,
        COUNT(a.alert_id) as alert_count
    FROM TOKEN t
    LEFT JOIN DEX_PRICE d ON t.token_address = d.token_address
        AND d.timestamp > NOW() - INTERVAL '7 days'
    LEFT JOIN TOKEN_HOLDER h ON t.token_address = h.token_address
        AND h.rank <= 10
    LEFT JOIN LATERAL (
        SELECT score
        FROM TOKEN_SCORE
        WHERE token_address = t.token_address
        ORDER BY timestamp DESC
        LIMIT 1
    ) s ON true
    LEFT JOIN ALERT a ON t.token_address = a.token_address
        AND a.severity IN ('high', 'critical')
    GROUP BY t.token_address, t.symbol, t.name, t.is_proxy,
             t.is_upgradeable, s.score
    HAVING COUNT(DISTINCT h.holder_address) > 0
    ORDER BY alert_count DESC, price_volatility DESC
    LIMIT 20;
    """

    return benchmark_query(
        "Q4: 复杂JOIN - 代币风险分析",
        query,
        None,
        iterations=50  # 复杂查询减少迭代次数
    )

# ============================================================================
# Q5: 批量写入性能测试
# ============================================================================

def query_q5_batch_insert():
    """
    Q5: 批量写入测试 - 测试插入性能

    业务场景: 实时价格数据写入
    预期性能: > 1000条/秒
    """

    print(f"\n{'='*60}")
    print("Q5: 批量写入性能测试")
    print(f"{'='*60}")

    conn = get_connection()
    cur = conn.cursor()

    # 获取一个测试token
    cur.execute("SELECT token_address FROM TOKEN LIMIT 1")
    result = cur.fetchone()
    if not result:
        print("❌ TOKEN表为空")
        return None
    token_address = result[0]

    # 准备测试数据
    test_data = []
    batch_size = 1000
    base_time = datetime.now()

    for i in range(batch_size):
        test_data.append((
            token_address,
            100.0 + i * 0.01,  # price
            1000000.0,          # tvl
            500000.0,           # liquidity_depth
            100000.0,           # volume_24h
            base_time + timedelta(seconds=i)
        ))

    # 测试批量插入
    insert_sql = """
    INSERT INTO DEX_PRICE (token_address, price, tvl, liquidity_depth,
                           volume_24h, timestamp)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        start = time.time()
        cur.executemany(insert_sql, test_data)
        conn.commit()
        elapsed = time.time() - start

        throughput = batch_size / elapsed
        avg_latency = (elapsed / batch_size) * 1000

        print(f"批量大小:     {batch_size} 条")
        print(f"总耗时:       {elapsed:.2f} 秒")
        print(f"吞吐量:       {throughput:.2f} 条/秒")
        print(f"平均延迟:     {avg_latency:.2f} ms/条")

        # 清理测试数据
        cur.execute("""
            DELETE FROM DEX_PRICE
            WHERE token_address = %s
            AND timestamp >= %s
        """, (token_address, base_time))
        conn.commit()

        cur.close()
        conn.close()

        return {
            "query_name": "Q5: 批量写入性能",
            "batch_size": batch_size,
            "total_time_s": round(elapsed, 2),
            "throughput_per_s": round(throughput, 2),
            "avg_latency_ms": round(avg_latency, 2)
        }

    except Exception as e:
        print(f"❌ 批量插入失败: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return None

# ============================================================================
# 主函数 - 运行所有查询
# ============================================================================

def main():
    """运行所有查询测试"""
    print("="*60)
    print("SQL查询性能测试 - 开始")
    print("="*60)

    results = []

    # Q1: 点查询
    print("\n[1/5] 执行点查询测试...")
    result = query_q1_point_lookup()
    if result:
        results.append(result)

    # Q2: 范围查询
    print("\n[2/5] 执行范围查询测试...")
    result = query_q2_range_query()
    if result:
        results.append(result)

    # Q3: 聚合查询
    print("\n[3/5] 执行聚合查询测试...")
    result = query_q3_aggregation()
    if result:
        results.append(result)

    # Q4: 复杂JOIN
    print("\n[4/5] 执行复杂JOIN查询测试...")
    result = query_q4_complex_join()
    if result:
        results.append(result)

    # Q5: 批量写入
    print("\n[5/5] 执行批量写入测试...")
    result = query_q5_batch_insert()
    if result:
        results.append(result)

    # 保存结果
    output_file = "D:\\LU_database_Project\\Out_put\\sql_query_results.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 测试结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n⚠️ 保存结果失败: {e}")

    # 打印汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    for r in results:
        print(f"{r['query_name']}: {r.get('avg_latency_ms', r.get('avg_latency_ms', 'N/A'))} ms")

    print("\n✅ 所有测试完成！")

if __name__ == "__main__":
    main()