#!/usr/bin/env python3
"""
Redis缓存优化脚本 - NoSQL组员2
功能: 实现缓存预热、监控、优化策略
"""

import os
import json
from pymongo import MongoClient
import redis
from datetime import datetime
from typing import List, Dict

# Database configuration with explicit auth settings
MONGO_CONFIG = {
    "host": os.getenv("MONGO_HOST", "token-analyzer-mongo"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "username": os.getenv("MONGO_USER", "admin"),
    "password": os.getenv("MONGO_PASS", "123456789"),
    "authSource": os.getenv("MONGO_AUTHSOURCE", "admin")
}

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "token-analyzer-redis"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "password": os.getenv("REDIS_PASS", "yourpassword"),
    "decode_responses": True
}

def init_connections():
    """Initialize database connections with error handling"""
    try:
        # MongoDB connection with explicit authentication
        mongo_client = MongoClient(**MONGO_CONFIG)
        # Test connection and authentication
        mongo_client.admin.command('ping')
        print("✓ MongoDB连接成功")
        
        # Redis connection
        redis_client = redis.Redis(**REDIS_CONFIG)
        redis_client.ping()
        print("✓ Redis连接成功")
        
        return mongo_client, redis_client
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        raise

# ============================================================================
# 缓存预热（Warm-up）
# ============================================================================

def cache_warmup():
    """
    缓存预热：在系统启动时预先加载热点数据到Redis

    策略:
    1. 缓存所有代币的最新信息
    2. 缓存Top 10代币列表
    3. 缓存高危预警
    """
    print("\n" + "="*60)
    print("Redis缓存预热")
    print("="*60)

    try:
        # Initialize connections
        mongo_client, redis_client = init_connections()
        db = mongo_client[os.getenv("MONGO_DB", "token_analyzer")]
        
        # 1. 缓存所有代币的最新信息
        print("\n[1/3] 缓存所有代币最新信息...")
        tokens = db.tokens.find({}, {
            "address": 1,
            "symbol": 1,
            "name": 1,
            "latest_price": 1,
            "latest_score": 1,
            "project": 1
        })

        cached_count = 0
        for token in tokens:
            cache_key = f"token:{token['address']}:latest"
            cache_data = {
                "symbol": token["symbol"],
                "name": token["name"],
                "price": token["latest_price"]["dex_price"],
                "tvl": token["latest_price"]["tvl"],
                "score": token["latest_score"]["score"],
                "github_stars": token.get("project", {}).get("stars", 0)
            }

            # 设置5分钟TTL
            redis_client.setex(cache_key, 300, json.dumps(cache_data))
            cached_count += 1

        print(f"✓ 缓存了 {cached_count} 个代币")

        # 2. 缓存Top 10代币列表
        print("\n[2/3] 缓存Top 10代币列表...")
        top_tokens = list(db.tokens.find(
            {},
            {
                "address": 1,
                "symbol": 1,
                "name": 1,
                "latest_score.score": 1,
                "latest_price.tvl": 1,
                "_id": 0
            }
        ).sort("latest_score.score", -1).limit(10))

        redis_client.setex("tokens:top10", 600, json.dumps(top_tokens, default=str))
        print(f"✓ 缓存了 Top 10 代币列表")

        # 3. 缓存高危预警
        print("\n[3/3] 缓存高危预警...")
        critical_alerts = list(db.alerts.find(
            {"severity": {"$in": ["HIGH", "CRITICAL"]}, "acknowledged": False},
            {"token_address": 1, "alert_type": 1, "message": 1, "timestamp": 1, "_id": 0}
        ).sort("timestamp", -1).limit(20))

        redis_client.setex("alerts:critical", 300, json.dumps(critical_alerts, default=str))
        print(f"✓ 缓存了 {len(critical_alerts)} 条高危预警")

        print("\n✅ 缓存预热完成！")

    except Exception as e:
        print(f"✗ 缓存预热失败: {str(e)}")
        raise
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()

# ============================================================================
# 缓存监控
# ============================================================================

def monitor_cache():
    """
    监控Redis缓存状态

    指标:
    1. 内存使用
    2. 键数量
    3. 命中率
    4. 连接数
    """
    print("\n" + "="*60)
    print("Redis缓存监控")
    print("="*60)

    redis_client = redis.Redis(**REDIS_CONFIG)

    # 获取Redis信息
    info = redis_client.info()

    # 内存使用
    used_memory = info.get("used_memory_human")
    max_memory = info.get("maxmemory_human", "unlimited")
    print(f"\n内存使用:")
    print(f"  当前使用: {used_memory}")
    print(f"  最大限制: {max_memory}")

    # 键统计
    total_keys = redis_client.dbsize()
    token_keys = len(redis_client.keys("token:*"))
    list_keys = len(redis_client.keys("tokens:*"))
    alert_keys = len(redis_client.keys("alerts:*"))

    print(f"\n键统计:")
    print(f"  总键数:     {total_keys}")
    print(f"  代币缓存:   {token_keys}")
    print(f"  列表缓存:   {list_keys}")
    print(f"  预警缓存:   {alert_keys}")

    # 命中率
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total_requests = hits + misses
    hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

    print(f"\n命中率:")
    print(f"  命中次数:   {hits}")
    print(f"  未命中次数: {misses}")
    print(f"  命中率:     {hit_rate:.2f}%")

    # 连接信息
    connected_clients = info.get("connected_clients", 0)
    print(f"\n连接信息:")
    print(f"  连接客户端: {connected_clients}")

    # 性能指标
    ops_per_sec = info.get("instantaneous_ops_per_sec", 0)
    print(f"\n性能指标:")
    print(f"  每秒操作数: {ops_per_sec}")

    # 持久化状态
    aof_enabled = info.get("aof_enabled", 0)
    print(f"\n持久化:")
    print(f"  AOF启用:    {'是' if aof_enabled else '否'}")

# ============================================================================
# 缓存优化建议
# ============================================================================

def optimize_cache():
    """
    分析缓存使用情况并提供优化建议
    """
    print("\n" + "="*60)
    print("缓存优化分析")
    print("="*60)

    redis_client = redis.Redis(**REDIS_CONFIG)
    info = redis_client.info()

    # 分析命中率
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0

    print(f"\n1. 命中率分析 ({hit_rate:.2f}%)")
    if hit_rate < 80:
        print("   ⚠️ 命中率偏低，建议:")
        print("   - 增加TTL时间")
        print("   - 预热更多热点数据")
        print("   - 检查缓存键命名是否一致")
    elif hit_rate >= 90:
        print("   ✓ 命中率优秀！")
    else:
        print("   ✓ 命中率良好")

    # 分析内存使用
    used_memory = info.get("used_memory")
    max_memory = info.get("maxmemory", 0)

    if max_memory > 0:
        memory_usage = (used_memory / max_memory * 100)
        print(f"\n2. 内存使用分析 ({memory_usage:.2f}%)")
        if memory_usage > 80:
            print("   ⚠️ 内存使用率高，建议:")
            print("   - 减少TTL时间")
            print("   - 清理不常用的键")
            print("   - 增加maxmemory限制")
        else:
            print("   ✓ 内存使用正常")

    # 分析过期键
    expired_keys = info.get("expired_keys", 0)
    evicted_keys = info.get("evicted_keys", 0)

    print(f"\n3. 键过期统计")
    print(f"   过期键数:   {expired_keys}")
    print(f"   驱逐键数:   {evicted_keys}")

    if evicted_keys > 0:
        print("   ⚠️ 发生键驱逐，建议增加内存或优化TTL")

    # 检查慢查询
    slowlog = redis_client.slowlog_get(10)
    print(f"\n4. 慢查询日志 (最近10条)")
    if slowlog:
        for entry in slowlog[:5]:
            duration = entry['duration'] / 1000  # 转换为毫秒
            cmd = ' '.join(str(arg, 'utf-8') if isinstance(arg, bytes) else str(arg) for arg in entry['command'])
            print(f"   {duration:.2f}ms - {cmd[:50]}...")
    else:
        print("   ✓ 无慢查询")

    print("\n" + "="*60)

# ============================================================================
# 缓存失效策略
# ============================================================================

def invalidate_stale_cache():
    """
    清理过期或陈旧的缓存

    策略:
    1. 删除TTL=0的键（永久键）
    2. 删除匹配特定模式的键
    """
    print("\n" + "="*60)
    print("清理陈旧缓存")
    print("="*60)

    redis_client = redis.Redis(**REDIS_CONFIG)

    # 查找所有代币缓存键
    token_keys = redis_client.keys("token:*:latest")

    cleaned = 0
    for key in token_keys:
        # 检查TTL
        ttl = redis_client.ttl(key)

        # TTL=-1表示永久键（没有设置过期时间）
        if ttl == -1:
            redis_client.delete(key)
            cleaned += 1

    print(f"✓ 清理了 {cleaned} 个永久键")

    # 可以添加更多清理逻辑...

    print("\n✅ 清理完成")

# ============================================================================
# 主程序
# ============================================================================

def main():
    """运行缓存优化工具"""
    
    while True:
        print("\n" + "="*60)
        print("Redis缓存优化工具")
        print("="*60)
        print("1. 缓存预热")
        print("2. 缓存监控")
        print("3. 缓存优化分析")
        print("4. 清理陈旧缓存")
        print("5. 退出")

        choice = input("\n请选择操作 (1-5): ").strip()

        if choice == "1":
            cache_warmup()
        elif choice == "2":
            monitor_cache()
        elif choice == "3":
            optimize_cache()
        elif choice == "4":
            invalidate_stale_cache()
        elif choice == "5":
            print("\n再见！")
            break
        else:
            print("\n无效选择，请重试")

def auto_execute_all():
    """Automatically execute all optimization tasks in sequence"""
    print("\n" + "="*60)
    print("执行缓存优化任务")
    print("="*60)

    # 1. Cache Warmup
    print("\n[1/4] 执行缓存预热...")
    cache_warmup()
    print("✓ 缓存预热完成")

    # 2. Cache Monitoring
    print("\n[2/4] 执行缓存监控...")
    monitor_cache()
    print("✓ 缓存监控完成")

    # 3. Cache Optimization
    print("\n[3/4] 执行缓存优化分析...")
    optimize_cache()
    print("✓ 优化分析完成")

    # 4. Stale Cache Cleanup
    print("\n[4/4] 执行陈旧缓存清理...")
    cleanup_stale_cache()
    print("✓ 缓存清理完成")

    print("\n" + "="*60)
    print("所有优化任务执行完成！")
    print("="*60)

if __name__ == "__main__":
    main()
