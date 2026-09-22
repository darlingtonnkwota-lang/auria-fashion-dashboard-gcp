-- silver_promotions: typed, deduped promotions dimension
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_promotions` AS
WITH typed AS (
  SELECT
    promotion_id,
    promotion_name,
    SAFE_CAST(start_date AS DATE) AS start_date,
    SAFE_CAST(end_date AS DATE) AS end_date,
    SAFE_CAST(discount_pct AS FLOAT64) AS discount_pct,
    scope_region,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_promotions`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY promotion_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT promotion_id, promotion_name, start_date, end_date, discount_pct, scope_region
FROM deduped
WHERE promotion_id IS NOT NULL
  AND discount_pct > 0 AND discount_pct <= 1;
