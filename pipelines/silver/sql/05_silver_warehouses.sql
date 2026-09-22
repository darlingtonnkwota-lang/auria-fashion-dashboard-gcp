-- silver_warehouses: typed, deduped warehouse dimension
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_warehouses` AS
WITH typed AS (
  SELECT warehouse_id, warehouse_name, region, country, city, _ingested_at
  FROM `__PROJECT__.bronze.bronze_warehouses`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY warehouse_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT warehouse_id, warehouse_name, region, country, city
FROM deduped
WHERE warehouse_id IS NOT NULL;
