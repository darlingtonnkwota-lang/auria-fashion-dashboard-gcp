-- silver_stores: typed, deduped store dimension, FK-checked against warehouses (required FK)
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_stores` AS
WITH typed AS (
  SELECT
    store_id,
    store_name,
    region,
    country,
    city,
    currency,
    store_type,
    SAFE_CAST(opened_date AS DATE) AS opened_date,
    home_warehouse_id,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_stores`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY store_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT d.store_id, d.store_name, d.region, d.country, d.city, d.currency,
       d.store_type, d.opened_date, d.home_warehouse_id
FROM deduped d
INNER JOIN `__PROJECT__.silver.silver_warehouses` w
  ON d.home_warehouse_id = w.warehouse_id
WHERE d.store_id IS NOT NULL;
