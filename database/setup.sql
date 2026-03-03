-- ============================================================
-- Financial Data Pipeline — Database Setup
-- Run this script once in MySQL to create the stored procedure
-- and seed the assets lookup table for multi-asset tracking.
-- ============================================================

-- ----- Seed Data: Tracked Assets ---------------------------
-- INSERT IGNORE keeps this script idempotent (safe to re-run).

INSERT IGNORE INTO assets (asset_id, symbol, name) VALUES
    (1, 'BTC', 'Bitcoin'),
    (2, 'ETH', 'Ethereum');


-- ----- Stored Procedure: sp_insert_snapshot ----------------
-- Encapsulates the INSERT logic so the Python pipeline calls
-- a single procedure instead of embedding raw SQL.

DROP PROCEDURE IF EXISTS sp_insert_snapshot;

DELIMITER //

CREATE PROCEDURE sp_insert_snapshot(
    IN p_asset_id    INT,
    IN p_price       DECIMAL(18, 2),
    IN p_market_cap  BIGINT,
    IN p_blocks      INT,
    IN p_dominance   DECIMAL(5, 2)
)
BEGIN
    INSERT INTO market_snapshots
        (asset_id, price_usd, market_cap_usd, total_blocks, dominance_pct)
    VALUES
        (p_asset_id, p_price, p_market_cap, p_blocks, p_dominance);
END //

DELIMITER ;
