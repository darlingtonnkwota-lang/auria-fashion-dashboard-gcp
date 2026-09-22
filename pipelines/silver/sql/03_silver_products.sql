-- silver_products: typed, deduped product dimension
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_products` AS
WITH typed AS (
  SELECT
    product_id,
    product_name,
    category,
    sub_category,
    gender,
    supplier_id,
    season_affinity,
    size_range,
    SAFE_CAST(unit_cost_usd AS NUMERIC) AS unit_cost_usd,
    SAFE_CAST(unit_price_usd AS NUMERIC) AS unit_price_usd,
    SAFE_CAST(launch_date AS DATE) AS launch_date,
    SAFE_CAST(NULLIF(TRIM(discontinued_date), '') AS DATE) AS discontinued_date,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_products`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY product_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT product_id, product_name, category, sub_category, gender, supplier_id,
       season_affinity, size_range, unit_cost_usd, unit_price_usd,
       launch_date, discontinued_date
FROM deduped
WHERE product_id IS NOT NULL
  AND unit_price_usd > 0 AND unit_cost_usd > 0;
