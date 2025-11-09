// ============================================================================
// MongoDB索引创建脚本（修正版）
// 作者: NoSQL组员1
// 日期: 2025-11-06
// ============================================================================
try {
    print("Starting index creation...");

    // 兼容两种执行方式：mongosh 已有 db 或需显式 connect()
    if (typeof db === "undefined") {
        const conn = connect("mongodb://admin:123456789@localhost:27017/?authSource=admin");
        db = conn.getDB("token_analyzer");
        print("Connected via connect(), using db: token_analyzer");
    } else {
        db = db.getSiblingDB("token_analyzer");
        print("Using existing db connection: token_analyzer");
    }

    print("开始创建索引...\n");

    // ============================================================================
    // 1. tokens集合索引
    // ============================================================================
    print("创建 tokens 集合索引...");

    db.tokens.createIndex({ "address": 1 }, { unique: true, name: "idx_address_unique" });
    db.tokens.createIndex({ "symbol": 1 }, { name: "idx_symbol" });
    db.tokens.createIndex({ "latest_price.dex_price": -1, "latest_score.score": -1 }, { name: "idx_price_score" });
    db.tokens.createIndex({ "latest_score.score": -1 }, { name: "idx_latest_score" });
    db.tokens.createIndex({ "is_proxy": 1, "is_upgradeable": 1 }, { name: "idx_risk_flags" });

    print("✓ tokens 索引创建完成\n");

    // ============================================================================
    // 2. dex_prices集合索引（时序数据）
    // ============================================================================
    print("创建 dex_prices 集合索引...");

    // 复合索引：按代币+时间查询（常用）
    db.dex_prices.createIndex({ "token_address": 1, "timestamp": -1 }, { name: "idx_token_timestamp" });

    // 保留 TTL 单字段索引用于自动清理（升序单字段索引）
    db.dex_prices.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 7776000, name: "idx_ttl_30days" });

    // 小时聚合索引
    db.dex_prices.createIndex({ "hour": 1 }, { name: "idx_hour" });

    print("✓ dex_prices 索引创建完成\n");

    // ============================================================================
    // 3. cex_prices集合索引
    // ============================================================================
    print("创建 cex_prices 集合索引...");

    db.cex_prices.createIndex({ "token_symbol": 1, "timestamp": -1 }, { name: "idx_symbol_timestamp" });
    db.cex_prices.createIndex({ "exchange": 1, "timestamp": -1 }, { name: "idx_exchange_timestamp" });

    print("✓ cex_prices 索引创建完成\n");

    // ============================================================================
    // 4. token_holders集合索引
    // ============================================================================
    print("创建 token_holders 集合索引...");

    db.token_holders.createIndex({ "token_address": 1, "snapshot_date": -1 }, { unique: true, name: "idx_token_snapshot_unique" });
    db.token_holders.createIndex({ "snapshot_date": -1 }, { name: "idx_snapshot_date" });
    db.token_holders.createIndex({ "holders.address": 1 }, { name: "idx_holder_address" });
    db.token_holders.createIndex({ "top10_concentration": -1 }, { name: "idx_concentration" });

    print("✓ token_holders 索引创建完成\n");

    // ============================================================================
    // 5. token_scores集合索引
    // ============================================================================
    print("创建 token_scores 集合索引...");

    db.token_scores.createIndex({ "token_address": 1, "timestamp": -1 }, { name: "idx_token_timestamp" });
    db.token_scores.createIndex({ "score": -1, "timestamp": -1 }, { name: "idx_score_timestamp" });

    print("✓ token_scores 索引创建完成\n");

    // ============================================================================
    // 6. alerts集合索引
    // ============================================================================
    print("创建 alerts 集合索引...");

    db.alerts.createIndex({ "token_address": 1, "timestamp": -1 }, { name: "idx_token_timestamp" });
    db.alerts.createIndex({ "severity": 1, "timestamp": -1 }, { name: "idx_severity_timestamp" });
    db.alerts.createIndex({ "acknowledged": 1, "timestamp": -1 }, { name: "idx_acknowledged_timestamp" });

    print("✓ alerts 索引创建完成\n");

    // ============================================================================
    // 验证索引创建
    // ============================================================================
    print("====================================");
    print("索引创建汇总:");
    print("====================================");

    print("\n1. tokens 索引数量: " + db.tokens.getIndexes().length);
    print("2. dex_prices 索引数量: " + db.dex_prices.getIndexes().length);
    print("3. cex_prices 索引数量: " + db.cex_prices.getIndexes().length);
    print("4. token_holders 索引数量: " + db.token_holders.getIndexes().length);
    print("5. token_scores 索引数量: " + db.token_scores.getIndexes().length);
    print("6. alerts 索引数量: " + db.alerts.getIndexes().length);

    print("\n✅ 所有索引创建完成！");
} catch (error) {
    print("Error creating indexes: " + error);
    throw error;
}
