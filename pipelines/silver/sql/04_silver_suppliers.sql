-- silver_suppliers: typed, deduped supplier dimension
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_suppliers` AS
WITH typed AS (
  SELECT
    supplier_id,
    supplier_name,
    country,
    region,
    category_focus,
    SAFE_CAST(avg_lead_time_days AS FLOAT64) AS avg_lead_time_days,
    SAFE_CAST(lead_time_stddev_days AS FLOAT64) AS lead_time_stddev_days,
    SAFE_CAST(reliability_score AS FLOAT64) AS reliability_score,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_suppliers`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY supplier_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT supplier_id, supplier_name, country, region, category_focus,
       avg_lead_time_days, lead_time_stddev_days, reliability_score
FROM deduped
WHERE supplier_id IS NOT NULL;
