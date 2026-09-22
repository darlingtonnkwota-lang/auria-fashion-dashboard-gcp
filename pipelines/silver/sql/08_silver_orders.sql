-- silver_orders: typed, deduped order headers.
-- Required FK: customer_id, fulfilling_warehouse_id.
-- Nullable FK: store_id (blank for Online orders), promotion_id (blank if none).
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_orders` AS
WITH typed AS (
  SELECT
    order_id,
    SAFE_CAST(order_date AS DATE) AS order_date,
    customer_id,
    channel,
    NULLIF(TRIM(store_id), '') AS store_id,
    fulfilling_warehouse_id,
    UPPER(TRIM(currency)) AS currency,
    NULLIF(TRIM(promotion_id), '') AS promotion_id,
    order_status,
    payment_method,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_orders`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY order_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT d.order_id, d.order_date, d.customer_id, d.channel, d.store_id,
       d.fulfilling_warehouse_id, d.currency, d.promotion_id,
       d.order_status, d.payment_method
FROM deduped d
INNER JOIN `__PROJECT__.silver.silver_customers` c
  ON d.customer_id = c.customer_id
INNER JOIN `__PROJECT__.silver.silver_warehouses` w
  ON d.fulfilling_warehouse_id = w.warehouse_id
LEFT JOIN `__PROJECT__.silver.silver_stores` s
  ON d.store_id = s.store_id
LEFT JOIN `__PROJECT__.silver.silver_promotions` p
  ON d.promotion_id = p.promotion_id
WHERE d.order_id IS NOT NULL
  AND d.order_status IN ('Completed', 'Cancelled')
  AND (d.store_id IS NULL OR s.store_id IS NOT NULL)
  AND (d.promotion_id IS NULL OR p.promotion_id IS NOT NULL);
