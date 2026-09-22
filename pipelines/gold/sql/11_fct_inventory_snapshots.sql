-- fct_inventory_snapshots: monthly stock snapshot fact (grain: product x
-- warehouse x month). Straight passthrough of Silver -- already at the
-- right grain, kept as its own Gold table so nothing downstream needs to
-- know Silver exists.
CREATE OR REPLACE TABLE `__PROJECT__.gold.fct_inventory_snapshots` AS
SELECT snapshot_month, warehouse_id, product_id, stock_on_hand, stockout_flag
FROM `__PROJECT__.silver.silver_inventory_snapshots`;
