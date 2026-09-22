-- silver_inventory_movements: typed, deduped inventory ledger, FK-checked
-- against warehouses/products (both required)
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_inventory_movements` AS
WITH typed AS (
  SELECT
    movement_id,
    SAFE_CAST(movement_date AS DATE) AS movement_date,
    warehouse_id,
    product_id,
    movement_type,
    SAFE_CAST(quantity_delta AS INT64) AS quantity_delta,
    NULLIF(TRIM(reference_id), '') AS reference_id,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_inventory_movements`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY movement_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT d.movement_id, d.movement_date, d.warehouse_id, d.product_id,
       d.movement_type, d.quantity_delta, d.reference_id
FROM deduped d
INNER JOIN `__PROJECT__.silver.silver_warehouses` w ON d.warehouse_id = w.warehouse_id
INNER JOIN `__PROJECT__.silver.silver_products` p ON d.product_id = p.product_id
WHERE d.movement_id IS NOT NULL
  AND d.movement_type IN ('Initial Stock', 'PO Receipt', 'Sale Fulfillment', 'Return Restock');
