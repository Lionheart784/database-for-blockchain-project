#!/usr/bin/env python3
"""
性能分析脚本 - SQL组员2（修正版）
"""

import psycopg2
import json

DB_CONFIG = {
    "host": "",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "123456"
}

def analyze_performance():
    """生成性能分析报告"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    report = {}

    # 1. 表统计信息（修正版）
    cur.execute("""
        SELECT
            relname as tablename,
            n_live_tup as row_count,
            pg_size_pretty(pg_relation_size(relname::regclass)) as table_size
        FROM pg_stat_user_tables
        ORDER BY n_live_tup DESC
    """)
    report['table_stats'] = [
        {"table": row[0], "rows": row[1], "size": row[2]}
        for row in cur.fetchall()
    ]

    # 2. 索引统计（修正版）
    cur.execute("""
        SELECT
            relname as tablename,
            indexrelname as indexname,
            idx_scan as scans,
            pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC
        LIMIT 10
    """)
    report['top_indexes'] = [
        {"table": row[0], "index": row[1], "scans": row[2], "size": row[3]}
        for row in cur.fetchall()
    ]

    # 3. 缓存命中率
    cur.execute("""
        SELECT
            sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0)
            as cache_hit_ratio
        FROM pg_statio_user_tables
    """)
    cache_ratio = cur.fetchone()[0]
    report['cache_hit_ratio'] = f"{float(cache_ratio or 0) * 100:.2f}%"

    cur.close()
    conn.close()

    # 保存报告
    with open('D:\\LU_database_Project\\Out_put\\performance_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("✅ 性能分析报告已生成: performance_analysis.json")
    print(f"缓存命中率: {report['cache_hit_ratio']}")

if __name__ == "__main__":
    analyze_performance()