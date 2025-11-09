#!/usr/bin/env python3
"""
Redis缓存工具 - NoSQL组员1
功能: 提供统一的缓存接口
"""

import redis
import json
from typing import Any, Optional

class RedisCache:
    """Redis缓存管理器"""

    def __init__(self, host='localhost', port=6379, password=None):
        """初始化Redis连接"""
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True
        )

    def set_token_latest(self, token_address: str, data: dict, ttl: int = 300):
        """
        缓存代币最新信息

        参数:
            token_address: 代币地址
            data: 缓存数据
            ttl: 过期时间（秒），默认5分钟
        """
        key = f"token:{token_address}:latest"
        self.client.setex(key, ttl, json.dumps(data))

    def get_token_latest(self, token_address: str) -> Optional[dict]:
        """获取代币最新信息"""
        key = f"token:{token_address}:latest"
        cached = self.client.get(key)
        return json.loads(cached) if cached else None

    def set_top_tokens(self, tokens: list, ttl: int = 600):
        """
        缓存Top代币列表

        参数:
            tokens: 代币列表
            ttl: 过期时间（秒），默认10分钟
        """
        key = "tokens:top10"
        self.client.setex(key, ttl, json.dumps(tokens))

    def get_top_tokens(self) -> Optional[list]:
        """获取Top代币列表"""
        cached = self.client.get("tokens:top10")
        return json.loads(cached) if cached else None

    def invalidate_token(self, token_address: str):
        """
        使代币相关缓存失效

        使用场景: 当代币数据更新时调用
        """
        keys_to_delete = [
            f"token:{token_address}:latest",
            f"token:{token_address}:score",
            f"token:{token_address}:price_24h"
        ]
        self.client.delete(*keys_to_delete)

        # 同时使Top列表失效（因为排名可能变化）
        self.client.delete("tokens:top10")

    def get_stats(self) -> dict:
        """获取Redis统计信息"""
        info = self.client.info()
        return {
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_keys": self.client.dbsize(),
            "hit_rate": self._calculate_hit_rate(info)
        }

    def _calculate_hit_rate(self, info: dict) -> float:
        """计算缓存命中率"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

# ============================================================================
# 使用示例
# ============================================================================
if __name__ == "__main__":
    # 初始化缓存
    cache = RedisCache(host='localhost', port=6379, password='yourpassword')

    # 示例1: 缓存代币信息
    token_data = {
        "symbol": "ETH",
        "price": 1800.50,
        "tvl": 1500000000,
        "score": 85
    }
    cache.set_token_latest("0x123...", token_data)
    print("✓ 缓存代币信息")

    # 示例2: 读取缓存
    cached = cache.get_token_latest("0x123...")
    if cached:
        print(f"✓ 缓存命中: {cached['symbol']} - ${cached['price']}")
    else:
        print("✗ 缓存未命中")

    # 示例3: 使缓存失效
    cache.invalidate_token("0x123...")
    print("✓ 缓存已失效")

    # 示例4: 查看统计
    stats = cache.get_stats()
    print(f"\nRedis统计:")
    print(f"  内存使用: {stats['used_memory']}")
    print(f"  总键数: {stats['total_keys']}")
    print(f"  命中率: {stats['hit_rate']:.2f}%")
