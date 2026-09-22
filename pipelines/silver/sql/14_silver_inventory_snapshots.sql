-- silver_inventory_snapshots: typed, deduped monthly stock snapshot,
-- FK-checked against warehouses/products (both required)
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_inventory_snapshots` AS
WITH typed AS (
  SELECT
    SAFE_CAST(snapshot_month AS DATE) AS snapshot_month,
    warehouse_id,
    product_id,
    SAFE_CAST(stock_on_hand AS INT64) AS stock_on_hand,
    SAFE_CAST(stockout_flag AS BOOL) AS stockout_flag,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_inventory_snapshots`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY snapshot_month, warehouse_id, product_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT d.snapshot_month, d.warehouse_id, d.product_id, d.stock_on_hand, d.stockout_flag
FROM deduped d
INNER JOIN `__PROJECT__.silver.silver_warehouses` w ON d.warehouse_id = w.warehouse_id
INNER JOIN `__PROJECT__.silver.silver_products` p ON d.product_id = p.product_id
WHERE d.snapshot_month IS NOT NULL
  AND d.warehouse_id IS NOT NULL
  AND d.product_id IS NOT NULL
  AND d.stock_on_hand >= 0;
