-- silver_exchange_rates: typed, deduped FX rates (1 unit of currency -> USD, by month)
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_exchange_rates` AS
WITH typed AS (
  SELECT
    SAFE_CAST(rate_month AS DATE) AS rate_month,
    UPPER(TRIM(currency)) AS currency,
    SAFE_CAST(rate_to_usd AS NUMERIC) AS rate_to_usd,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_exchange_rates`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY rate_month, currency ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT rate_month, currency, rate_to_usd
FROM deduped
WHERE rate_month IS NOT NULL
  AND currency IS NOT NULL
  AND rate_to_usd > 0;
