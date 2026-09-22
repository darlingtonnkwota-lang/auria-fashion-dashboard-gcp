-- silver_purchase_orders: typed, deduped purchase orders, FK-checked
-- against suppliers/warehouses (both required)
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_purchase_orders` AS
WITH typed AS (
  SELECT
    po_id,
    supplier_id,
    warehouse_id,
    SAFE_CAST(order_date AS DATE) AS order_date,
    SAFE_CAST(expected_date AS DATE) AS expected_date,
    SAFE_CAST(NULLIF(TRIM(received_date), '') AS DATE) AS received_date,
    status,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_purchase_orders`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY po_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT d.po_id, d.supplier_id, d.warehouse_id, d.order_date, d.expected_date,
       d.received_date, d.status
FROM deduped d
INNER JOIN `__PROJECT__.silver.silver_suppliers` s ON d.supplier_id = s.supplier_id
INNER JOIN `__PROJECT__.silver.silver_warehouses` w ON d.warehouse_id = w.warehouse_id
WHERE d.po_id IS NOT NULL
  AND d.status IN ('Open', 'Received', 'Received (Late)');
