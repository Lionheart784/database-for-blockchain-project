import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta
import random
from faker import Faker

# 初始化Faker（用于生成随机数据）
fake = Faker()

# ============================================================================
# 配置参数
# ============================================================================
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "token_analyzer",
    "user": "postgres",
    "password": "123456"  # ⚠️ 请修改为你的实际密码
}

# 数据生成配置
NUM_TOKENS = 100            # 生成100个代币
NUM_DEX_PRICES = 1000   # 每个代币生成1000条价格记录
NUM_HOLDERS_PER_TOKEN = 20  # 每个代币生成20个持仓地址
NUM_ALERTS_PER_TOKEN = 10   # 每个代币生成10条预警

# ============================================================================
# 辅助函数
# ============================================================================
def generate_eth_address():
    """生成随机的以太坊地址格式"""
    return '0x' + ''.join(random.choices('0123456789abcdef', k=40))

def generate_price_series(base_price, num_points, volatility=0.1):
    """
    生成价格时间序列（模拟随机游走）

    参数:
        base_price: 基准价格
        num_points: 生成点数
        volatility: 波动率（0.1表示±10%）

    返回:
        价格列表
    """
    prices = [base_price]
    for _ in range(num_points - 1):
        change = random.gauss(0, volatility)  # 正态分布的价格变化
        new_price = prices[-1] * (1 + change)
        new_price = max(new_price, 0.0001)    # 价格不能为负
        prices.append(new_price)
    return prices

# ============================================================================
# 主程序
# ============================================================================
def main():
    print("=" * 60)
    print("数据加载脚本启动")
    print("=" * 60)

    # 连接数据库
    print("\n[1/7] 连接数据库...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return

    # ========================================================================
    # 步骤1: 生成TOKEN数据
    # ========================================================================
    print(f"\n[2/7] 生成 {NUM_TOKENS} 个代币数据...")

    tokens = []
    chains = ['ETH', 'BSC', 'POLYGON', 'ARBITRUM']

    for i in range(NUM_TOKENS):
        token_address = generate_eth_address()
        symbol = f"TOKEN{i+1}"
        name = f"Test Token {i+1}"
        chain = random.choice(chains)
        is_proxy = random.random() < 0.3        # 30%概率为代理合约
        is_upgradeable = random.random() < 0.2  # 20%概率可升级

        tokens.append((
            token_address,
            symbol,
            name,
            chain,
            is_proxy,
            is_upgradeable
        ))

    # 批量插入TOKEN
    execute_batch(cur, """
        INSERT INTO TOKEN (token_address, symbol, name, chain, is_proxy, is_upgradeable)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (token_address) DO NOTHING
    """, tokens, page_size=100)

    print(f"✓ 插入了 {len(tokens)} 个代币")

    # ========================================================================
    # 步骤2: 生成DEX_PRICE数据
    # ========================================================================
    print(f"\n[3/7] 生成 DEX价格数据（目标: {NUM_DEX_PRICES}条）...")

    dex_prices = []
    prices_per_token = NUM_DEX_PRICES // NUM_TOKENS  # 每个代币的价格记录数

    for token_address, symbol, *_ in tokens:
        # 生成价格序列
        base_price = random.uniform(0.1, 1000)  # 随机基准价格
        price_series = generate_price_series(base_price, prices_per_token, volatility=0.05)

        # 生成时间戳序列（过去30天，每15分钟一个点）
        end_time = datetime.now()
        time_delta = timedelta(minutes=15)

        for i, price in enumerate(price_series):
            timestamp = end_time - (prices_per_token - i - 1) * time_delta

            # 确保timestamp在分区范围内
            if timestamp.year != 2025 or timestamp.month not in [1, 2, 3]:
                timestamp = datetime(2025, 2, 15) + i * time_delta

            tvl = price * random.uniform(100000, 10000000)      # TVL = 价格 × 流通量
            liquidity_depth = tvl * random.uniform(0.01, 0.1)   # 流动性深度约为TVL的1-10%
            volume_24h = tvl * random.uniform(0.05, 0.5)        # 24h交易量约为TVL的5-50%

            dex_prices.append((
                token_address,
                float(price),
                float(tvl),
                float(liquidity_depth),
                float(volume_24h),
                timestamp
            ))

    # 分批插入（每次1000条，避免内存占用过大）
    batch_size = 1000
    for i in range(0, len(dex_prices), batch_size):
        batch = dex_prices[i:i+batch_size]
        execute_batch(cur, """
            INSERT INTO DEX_PRICE (token_address, price, tvl, liquidity_depth, volume_24h, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, batch, page_size=100)

        if (i + batch_size) % 10000 == 0:
            print(f"  已插入 {i + batch_size} 条记录...")

    print(f"✓ 插入了 {len(dex_prices)} 条DEX价格记录")

    # ========================================================================
    # 步骤3: 生成CEX_PRICE数据
    # ========================================================================
    print(f"\n[4/7] 生成 CEX价格数据...")

    cex_prices = []
    exchanges = ['Binance', 'OKX', 'Coinbase', 'Kraken']

    for token_address, symbol, *_ in tokens:
        # 选择2-3个交易所
        selected_exchanges = random.sample(exchanges, k=random.randint(2, 3))

        for exchange in selected_exchanges:
            for i in range(100):  # 每个交易所100个数据点
                timestamp = datetime.now() - timedelta(hours=100-i)

                # 确保timestamp在分区范围内
                if timestamp.year != 2025 or timestamp.month not in [1, 2, 3]:
                    timestamp = datetime(2025, 2, 15) + timedelta(hours=i)

                spot_price = random.uniform(0.1, 1000)
                funding_rate = random.gauss(0, 0.001)  # 资金费率通常很小
                volume_24h = random.uniform(100000, 10000000)

                cex_prices.append((
                    symbol,
                    exchange,
                    float(spot_price),
                    float(funding_rate),
                    float(volume_24h),
                    timestamp
                ))

    # 批量插入
    execute_batch(cur, """
        INSERT INTO CEX_PRICE (token_symbol, exchange, spot_price, funding_rate, volume_24h, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, cex_prices, page_size=100)

    print(f"✓ 插入了 {len(cex_prices)} 条CEX价格记录")

    # ========================================================================
    # 步骤4: 生成TOKEN_HOLDER数据
    # ========================================================================
    print(f"\n[5/7] 生成 持仓分布数据...")

    holders = []
    today = datetime.now().date()

    for token_address, *_ in tokens:
        # 生成持仓分布（符合幂律分布）
        total_supply = 1000000000  # 假设总供应量10亿

        for rank in range(1, NUM_HOLDERS_PER_TOKEN + 1):
            holder_address = generate_eth_address()

            # 幂律分布：Top 1持仓最多，逐渐递减
            balance = total_supply / (rank ** 1.5)
            percentage = (balance / total_supply) * 100

            holders.append((
                token_address,
                holder_address,
                int(balance),
                float(percentage),
                rank,
                today
            ))

    execute_batch(cur, """
        INSERT INTO TOKEN_HOLDER (token_address, holder_address, balance, percentage, rank, snapshot_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (token_address, holder_address, snapshot_date) DO NOTHING
    """, holders, page_size=100)

    print(f"✓ 插入了 {len(holders)} 条持仓记录")

    # ========================================================================
    # 步骤5: 生成TOKEN_SCORE数据
    # ========================================================================
    print(f"\n[6/7] 生成 代币评分数据...")

    scores = []

    for token_address, *_ in tokens:
        for i in range(10):  # 每个代币10个历史评分
            timestamp = datetime.now() - timedelta(hours=10-i)

            # 生成评分因子
            liquidity_score = random.randint(50, 100)
            holder_score = random.randint(40, 90)
            dev_score = random.randint(30, 95)
            market_score = random.randint(45, 85)

            # 综合评分（加权平均）
            score = int(
                liquidity_score * 0.3 +
                holder_score * 0.2 +
                dev_score * 0.3 +
                market_score * 0.2
            )

            score_factors = {
                "liquidity": liquidity_score,
                "holder_concentration": holder_score,
                "github_activity": dev_score,
                "market_sentiment": market_score
            }

            scores.append((
                token_address,
                score,
                psycopg2.extras.Json(score_factors),
                timestamp
            ))

    execute_batch(cur, """
        INSERT INTO TOKEN_SCORE (token_address, score, score_factors, timestamp)
        VALUES (%s, %s, %s, %s)
    """, scores, page_size=100)

    print(f"✓ 插入了 {len(scores)} 条评分记录")

    # ========================================================================
    # 步骤6: 生成PROJECT数据
    # ========================================================================
    print(f"\n[7/7] 生成 项目信息数据...")

    projects = []

    for token_address, symbol, name, *_ in tokens:
        project_name = name
        github_repo = f"https://github.com/{fake.user_name()}/{symbol.lower()}"
        github_stars = random.randint(10, 50000)
        commit_count_7d = random.randint(0, 100)
        last_commit_at = datetime.now() - timedelta(days=random.randint(0, 30))

        projects.append((
            token_address,
            project_name,
            github_repo,
            github_stars,
            commit_count_7d,
            last_commit_at
        ))

    execute_batch(cur, """
        INSERT INTO PROJECT (token_address, project_name, github_repo, github_stars, commit_count_7d, last_commit_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (token_address) DO NOTHING
    """, projects, page_size=100)

    print(f"✓ 插入了 {len(projects)} 个项目")

    # ========================================================================
    # 步骤7: 生成ALERT数据
    # ========================================================================
    print(f"\n[8/7] 生成 预警数据...")

    alerts = []
    alert_types = ['LIQUIDITY_DROP', 'PRICE_SPIKE', 'WHALE_MOVEMENT', 'RUG_PULL_RISK']
    severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

    for token_address, symbol, *_ in tokens[:50]:  # 只为前50个代币生成预警
        for _ in range(NUM_ALERTS_PER_TOKEN):
            alert_type = random.choice(alert_types)
            severity = random.choice(severities)
            message = f"{symbol}: {alert_type} detected"
            timestamp = datetime.now() - timedelta(hours=random.randint(1, 720))

            alerts.append((
                token_address,
                alert_type,
                severity,
                message,
                timestamp
            ))

    execute_batch(cur, """
        INSERT INTO ALERT (token_address, alert_type, severity, message, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, alerts, page_size=100)

    print(f"✓ 插入了 {len(alerts)} 条预警")

    # ========================================================================
    # 提交事务
    # ========================================================================
    print("\n[提交] 提交事务到数据库...")
    conn.commit()

    # ========================================================================
    # 数据统计
    # ========================================================================
    print("\n" + "=" * 60)
    print("数据加载完成！统计信息:")
    print("=" * 60)

    cur.execute("SELECT COUNT(*) FROM TOKEN")
    print(f"代币数量:        {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM DEX_PRICE")
    print(f"DEX价格记录:     {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM CEX_PRICE")
    print(f"CEX价格记录:     {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM TOKEN_HOLDER")
    print(f"持仓记录:        {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM TOKEN_SCORE")
    print(f"评分记录:        {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM PROJECT")
    print(f"项目数量:        {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM ALERT")
    print(f"预警数量:        {cur.fetchone()[0]}")

    # 关闭连接
    cur.close()
    conn.close()

    print("\n✅ 所有数据加载成功！")

if __name__ == "__main__":
    main()