#!/usr/bin/env python3
"""
NoSQL数据加载脚本 - NoSQL组员1
功能: 生成并加载测试数据到MongoDB和Redis
数据规模: 100个代币，10万+条价格记录
"""
from pymongo import MongoClient
import redis
from datetime import datetime, timedelta
import random
import json
import os
from faker import Faker

# 初始化Faker
fake = Faker()

# ============================================================================
# 配置参数（优先使用环境变量）
# ============================================================================
MONGO_CONFIG = {
    "host": os.getenv("MONGO_HOST", "localhost"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "username": os.getenv("MONGO_USER", "admin"),
    "password": os.getenv("MONGO_PASS", "123456789"),  # ⚠️ 请修改为你的实际密码或设置环境变量
    "authSource": os.getenv("MONGO_AUTHSOURCE", "admin"),
    "database": os.getenv("MONGO_DB", "token_analyzer")
}

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "password": os.getenv("REDIS_PASS", "yourpassword"),  # ⚠️ 请修改或设置环境变量
    "decode_responses": True
}

# 数据生成配置
NUM_TOKENS = 100                # 生成100个代币
NUM_DEX_PRICES_PER_TOKEN = 1000 # 每个代币1000条价格记录
NUM_HOLDERS_PER_TOKEN = 20      # 每个代币20个持仓地址
NUM_SCORES_PER_TOKEN = 10       # 每个代币10条历史评分

# ============================================================================
# 辅助函数
# ============================================================================
def generate_eth_address():
    return '0x' + ''.join(random.choices('0123456789abcdef', k=40))

def generate_price_series(base_price, num_points, volatility=0.05):
    prices = [base_price]
    for _ in range(num_points - 1):
        change = random.gauss(0, volatility)
        new_price = prices[-1] * (1 + change)
        new_price = max(new_price, 0.0001)
        prices.append(new_price)
    return prices

def connect_mongo_with_retries(config, try_hosts=None, timeout_ms=5000):
    """尝试多个host，返回 (client, db) 或抛出最后异常"""
    tried = []
    last_exc = None
    hosts = []
    if try_hosts:
        hosts.extend(try_hosts)
    # 优先使用配置的 host，然后尝试常用备选项（去重）
    hosts.extend([config["host"], "localhost", "token-analyzer-mongo"])
    seen = set()
    hosts = [h for h in hosts if h and (h not in seen and not seen.add(h))]

    for host in hosts:
        tried.append(host)
        try:
            client = MongoClient(
                host=host,
                port=config["port"],
                username=config["username"],
                password=config["password"],
                authSource=config.get("authSource", "admin"),
                serverSelectionTimeoutMS=timeout_ms
            )
            client.server_info()  # 强制触发连接/认证
            db = client[config["database"]]
            print(f"✓ MongoDB connected (host={host})")
            return client, db
        except Exception as e:
            print(f"✗ MongoDB connect failed (host={host}): {e}")
            last_exc = e
    raise last_exc

# ============================================================================
# 主程序
# ============================================================================
def main():
    print("=" * 60)
    print("NoSQL数据加载脚本启动")
    print("=" * 60)

    # 连接MongoDB（会尝试配置的 host、localhost、token-analyzer-mongo）
    print("\n[1/8] 连接MongoDB...")
    try:
        mongo_client, db = connect_mongo_with_retries(MONGO_CONFIG)
    except Exception as e:
        print(f"✗ MongoDB连接失败: {e}")
        print("检查点：1) 容器是否运行 docker ps 2) 用户/密码及 authSource 是否正确 3) 是否需要在宿主上映射端口")
        return

    # 连接Redis
    print("\n[2/8] 连接Redis...")
    try:
        redis_client = redis.Redis(**REDIS_CONFIG)
        redis_client.ping()
        print("✓ Redis连接成功")
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        # 不立即退出，可根据需要 decide
        return

    # ========================================================================
    # 步骤1: 生成并插入tokens数据
    # ========================================================================
    print(f"\n[3/8] 生成 {NUM_TOKENS} 个代币数据...")

    tokens = []
    token_addresses = []

    for i in range(NUM_TOKENS):
        address = generate_eth_address()
        token_addresses.append(address)

        # 生成最新价格数据
        base_price = random.uniform(0.1, 10000)
        latest_price = {
            "dex_price": round(base_price, 2),
            "cex_price": round(base_price * random.uniform(0.99, 1.01), 2),
            "tvl": round(random.uniform(100000, 100000000), 2),
            "liquidity_depth": round(random.uniform(10000, 10000000), 2),
            "volume_24h": round(random.uniform(50000, 5000000), 2),
            "timestamp": datetime.now()
        }

        # 生成评分数据
        liquidity_score = random.randint(50, 100)
        holder_score = random.randint(40, 90)
        dev_score = random.randint(30, 95)
        market_score = random.randint(45, 85)

        overall_score = int(
            liquidity_score * 0.3 +
            holder_score * 0.2 +
            dev_score * 0.3 +
            market_score * 0.2
        )

        latest_score = {
            "score": overall_score,
            "factors": {
                "liquidity_score": liquidity_score,
                "holder_score": holder_score,
                "dev_score": dev_score,
                "market_score": market_score
            },
            "timestamp": datetime.now()
        }

        # 生成项目信息
        project = {
            "name": f"{fake.company()} Protocol",
            "github_repo": f"https://github.com/{fake.user_name()}/{fake.word()}",
            "stars": random.randint(10, 50000),
            "commit_count_7d": random.randint(0, 100),
            "last_commit_at": datetime.now() - timedelta(days=random.randint(0, 30))
        }

        # 组装完整的代币文档
        token = {
            "address": address,
            "symbol": fake.cryptocurrency_code(),
            "name": fake.cryptocurrency_name(),
            "chain": random.choice(['ETH', 'BSC', 'POLYGON', 'ARBITRUM']),
            "is_proxy": random.random() < 0.3,
            "is_upgradeable": random.random() < 0.2,
            "latest_price": latest_price,
            "latest_score": latest_score,
            "project": project,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        tokens.append(token)

    # 批量插入tokens
    result = db.tokens.insert_many(tokens)
    print(f"✓ 插入了 {len(result.inserted_ids)} 个代币到MongoDB")

    # 缓存到Redis（优化点查询）
    print("\n[4/8] 缓存tokens数据到Redis...")
    cached_count = 0
    for token in tokens:
        cache_key = f"token:{token['address']}:latest"
        cache_data = {
            "symbol": token["symbol"],
            "name": token["name"],
            "price": token["latest_price"]["dex_price"],
            "tvl": token["latest_price"]["tvl"],
            "score": token["latest_score"]["score"]
        }
        redis_client.setex(cache_key, 300, json.dumps(cache_data))
        cached_count += 1

    print(f"✓ 缓存了 {cached_count} 个代币到Redis (TTL=5分钟)")

    # ========================================================================
    # 步骤2: 生成并插入dex_prices数据
    # ========================================================================
    print(f"\n[5/8] 生成 DEX价格数据（目标: {NUM_TOKENS * NUM_DEX_PRICES_PER_TOKEN}条）...")

    dex_prices = []

    for token_address in token_addresses:
        # 生成价格序列
        base_price = random.uniform(0.1, 10000)
        price_series = generate_price_series(base_price, NUM_DEX_PRICES_PER_TOKEN, volatility=0.03)

        # 生成时间戳序列（过去30天，每15分钟一个点）
        end_time = datetime.now()
        time_delta = timedelta(minutes=15)

        for i, price in enumerate(price_series):
            timestamp = end_time - (NUM_DEX_PRICES_PER_TOKEN - i - 1) * time_delta

            tvl = price * random.uniform(100000, 10000000)
            liquidity_depth = tvl * random.uniform(0.01, 0.1)
            volume_24h = tvl * random.uniform(0.05, 0.5)

            # 小时聚合字段（用于优化查询）
            hour = timestamp.replace(minute=0, second=0, microsecond=0)

            dex_prices.append({
                "token_address": token_address,
                "price": round(price, 8),
                "tvl": round(tvl, 2),
                "liquidity_depth": round(liquidity_depth, 2),
                "volume_24h": round(volume_24h, 2),
                "timestamp": timestamp,
                "hour": hour
            })

    # 分批插入（每次1万条）
    batch_size = 10000
    for i in range(0, len(dex_prices), batch_size):
        batch = dex_prices[i:i+batch_size]
        db.dex_prices.insert_many(batch)
        print(f"  已插入 {min(i+batch_size, len(dex_prices))} / {len(dex_prices)} 条记录...")

    print(f"✓ 插入了 {len(dex_prices)} 条DEX价格记录")

    # ========================================================================
    # 步骤3: 生成并插入cex_prices数据
    # ========================================================================
    print(f"\n[6/8] 生成 CEX价格数据...")

    cex_prices = []
    exchanges = ['Binance', 'OKX', 'Coinbase', 'Kraken', 'Bybit']

    for token in tokens:
        symbol = token["symbol"]

        # 每个代币在2-3个交易所上市
        selected_exchanges = random.sample(exchanges, k=random.randint(2, 3))

        for exchange in selected_exchanges:
            for i in range(100):  # 每个交易所100个数据点
                timestamp = datetime.now() - timedelta(hours=100-i)

                spot_price = random.uniform(0.1, 10000)
                funding_rate = random.gauss(0, 0.001)  # 资金费率通常很小
                volume_24h = random.uniform(100000, 10000000)

                cex_prices.append({
                    "token_symbol": symbol,
                    "exchange": exchange,
                    "spot_price": round(spot_price, 8),
                    "funding_rate": round(funding_rate, 8),
                    "volume_24h": round(volume_24h, 2),
                    "timestamp": timestamp
                })

    db.cex_prices.insert_many(cex_prices)
    print(f"✓ 插入了 {len(cex_prices)} 条CEX价格记录")

    # ========================================================================
    # 步骤4: 生成并插入token_holders数据（使用数组存储）
    # ========================================================================
    print(f"\n[7/8] 生成 持仓分布数据...")

    holders_docs = []

    for token_address in token_addresses:
        # 生成持仓分布（幂律分布）
        total_supply = 1000000000
        holders = []

        for rank in range(1, NUM_HOLDERS_PER_TOKEN + 1):
            holder_address = generate_eth_address()
            balance = int(total_supply / (rank ** 1.5))
            percentage = (balance / total_supply) * 100

            holders.append({
                "address": holder_address,
                "balance": str(balance),  # 使用字符串存储大数字
                "percentage": round(percentage, 4),
                "rank": rank
            })

        # 计算集中度
        top10_concentration = sum(h["percentage"] for h in holders[:10])
        top20_concentration = sum(h["percentage"] for h in holders[:20])

        holders_docs.append({
            "token_address": token_address,
            "holders": holders,
            "top10_concentration": round(top10_concentration, 2),
            "top20_concentration": round(top20_concentration, 2),
            "total_holders": random.randint(5000, 50000),
            "snapshot_date": datetime.now(),
            "updated_at": datetime.now()
        })

    db.token_holders.insert_many(holders_docs)
    print(f"✓ 插入了 {len(holders_docs)} 个代币的持仓数据（每个包含{NUM_HOLDERS_PER_TOKEN}个持仓者）")

    # ========================================================================
    # 步骤5: 生成并插入token_scores数据
    # ========================================================================
    print(f"\n[8/8] 生成 评分历史数据...")

    scores = []

    for token_address in token_addresses:
        for i in range(NUM_SCORES_PER_TOKEN):
            timestamp = datetime.now() - timedelta(hours=i*24)

            liquidity_score = random.randint(50, 100)
            holder_score = random.randint(40, 90)
            dev_score = random.randint(30, 95)
            market_score = random.randint(45, 85)

            overall_score = int(
                liquidity_score * 0.3 +
                holder_score * 0.2 +
                dev_score * 0.3 +
                market_score * 0.2
            )

            scores.append({
                "token_address": token_address,
                "score": overall_score,
                "score_factors": {
                    "liquidity_score": liquidity_score,
                    "holder_score": holder_score,
                    "dev_score": dev_score,
                    "market_score": market_score
                },
                "timestamp": timestamp
            })

    db.token_scores.insert_many(scores)
    print(f"✓ 插入了 {len(scores)} 条评分记录")

    # ========================================================================
    # 步骤6: 生成并插入alerts数据
    # ========================================================================
    print(f"\n[额外] 生成 预警数据...")

    alert_types = ['LIQUIDITY_DROP', 'PRICE_SPIKE', 'WHALE_MOVEMENT', 'RUG_PULL_RISK']
    severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    alerts = []

    # 为前50个代币生成预警
    for token_address in random.sample(token_addresses, 50):
        for i in range(10):
            alerts.append({
                "token_address": token_address,
                "alert_type": random.choice(alert_types),
                "severity": random.choice(severities),
                "message": f"Alert: {fake.sentence()}",
                "timestamp": datetime.now() - timedelta(hours=i*6),
                "acknowledged": random.choice([True, False])
            })

    db.alerts.insert_many(alerts)
    print(f"✓ 插入了 {len(alerts)} 条预警")

    # ========================================================================
    # 数据统计
    # ========================================================================
    print("\n" + "=" * 60)
    print("数据加载完成！统计信息:")
    print("=" * 60)

    print(f"代币数量 (MongoDB):      {db.tokens.count_documents({})}")
    print(f"代币数量 (Redis缓存):    {len(tokens)}")
    print(f"DEX价格记录:            {db.dex_prices.count_documents({})}")
    print(f"CEX价格记录:            {db.cex_prices.count_documents({})}")
    print(f"持仓记录:               {db.token_holders.count_documents({})}")
    print(f"评分记录:               {db.token_scores.count_documents({})}")
    print(f"预警记录:               {db.alerts.count_documents({})}")

    # 关闭连接
    mongo_client.close()

    print("\n✅ NoSQL数据加载成功！")

if __name__ == "__main__":
    main()
