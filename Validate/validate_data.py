"""
数据规模验证脚本
检查SQL和NoSQL数据库的数据完整性和一致性
"""

import psycopg2
from pymongo import MongoClient

def validate_databases():
    """验证两个数据库的数据规模"""

    # 连接SQL数据库
    print("="*60)
    print("1. 连接数据库")
    print("="*60)

    try:
        pg_conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="token_analyzer",
            user="postgres",
            password="yourpassword"
        )
        pg_cur = pg_conn.cursor()
        print("✓ PostgreSQL连接成功")
    except Exception as e:
        print(f"✗ PostgreSQL连接失败: {e}")
        return False

    # 连接NoSQL数据库
    try:
        mongo_client = MongoClient("mongodb://admin:yourpassword@localhost:27017/")
        mongo_db = mongo_client["token_analyzer"]
        print("✓ MongoDB连接成功")
    except Exception as e:
        print(f"✗ MongoDB连接失败: {e}")
        return False

    print("\n" + "="*60)
    print("2. 验证数据规模")
    print("="*60)

    # 验证代币数量
    pg_cur.execute("SELECT COUNT(*) FROM TOKEN")
    sql_tokens = pg_cur.fetchone()[0]
    nosql_tokens = mongo_db.tokens.count_documents({})
    print(f"\n代币数量:")
    print(f"  SQL:    {sql_tokens:>6}")
    print(f"  NoSQL:  {nosql_tokens:>6}")
    print(f"  状态:   {'✓ 一致' if sql_tokens == nosql_tokens else '✗ 不一致'}")

    # 验证DEX价格记录数
    pg_cur.execute("SELECT COUNT(*) FROM DEX_PRICE")
    sql_dex_prices = pg_cur.fetchone()[0]
    nosql_dex_prices = mongo_db.dex_prices.count_documents({})
    print(f"\nDEX价格记录:")
    print(f"  SQL:    {sql_dex_prices:>6}")
    print(f"  NoSQL:  {nosql_dex_prices:>6}")
    print(f"  状态:   {'✓ 一致' if sql_dex_prices == nosql_dex_prices else '✗ 不一致'}")

    # 验证CEX价格记录数
    pg_cur.execute("SELECT COUNT(*) FROM CEX_PRICE")
    sql_cex_prices = pg_cur.fetchone()[0]
    nosql_cex_prices = mongo_db.cex_prices.count_documents({})
    print(f"\nCEX价格记录:")
    print(f"  SQL:    {sql_cex_prices:>6}")
    print(f"  NoSQL:  {nosql_cex_prices:>6}")
    print(f"  状态:   {'✓ 一致' if sql_cex_prices == nosql_cex_prices else '✗ 不一致'}")

    # 验证持仓记录数
    pg_cur.execute("SELECT COUNT(*) FROM TOKEN_HOLDER")
    sql_holders = pg_cur.fetchone()[0]
    nosql_holders = mongo_db.token_holders.count_documents({})
    print(f"\n持仓记录:")
    print(f"  SQL:    {sql_holders:>6}")
    print(f"  NoSQL:  {nosql_holders:>6}")
    print(f"  状态:   {'✓ 一致' if sql_holders == nosql_holders else '✗ 不一致'}")

    print("\n" + "="*60)
    print("3. 验证存储空间")
    print("="*60)

    # 验证存储空间
    pg_cur.execute("SELECT pg_size_pretty(pg_database_size('token_analyzer'))")
    sql_size = pg_cur.fetchone()[0]

    mongo_stats = mongo_db.command("dbstats")
    nosql_size_mb = mongo_stats['dataSize'] / (1024 * 1024)

    print(f"\n数据库大小:")
    print(f"  SQL:    {sql_size}")
    print(f"  NoSQL:  {nosql_size_mb:.2f} MB")

    print("\n" + "="*60)
    print("✅ 数据验证完成")
    print("="*60)

    # 清理连接
    pg_conn.close()
    mongo_client.close()

    return True

if __name__ == "__main__":
    validate_databases()