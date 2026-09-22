-- silver_customers: typed, deduped customer dimension
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_customers` AS
WITH typed AS (
  SELECT
    customer_id,
    first_name,
    last_name,
    email,
    region,
    country,
    city,
    home_currency,
    acquisition_channel,
    SAFE_CAST(signup_date AS DATE) AS signup_date,
    SAFE_CAST(is_active AS BOOL) AS is_active,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_customers`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY customer_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT customer_id, first_name, last_name, email, region, country, city,
       home_currency, acquisition_channel, signup_date, is_active
FROM deduped
WHERE customer_id IS NOT NULL
  AND email IS NOT NULL AND email LIKE '%@%';
