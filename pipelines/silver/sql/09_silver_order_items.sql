-- silver_order_items: typed, deduped order lines, FK-checked against
-- orders/products, USD-normalized via a month+currency join to
-- silver_exchange_rates. Rows where the FX join doesn't resolve
-- (unit_price_usd or line_net_amount_usd ends up NULL) are dropped --
-- the SQL equivalent of the Databricks build's "fx_resolved" expectation.
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_order_items` AS
WITH typed AS (
  SELECT
    order_item_id,
    order_id,
    product_id,
    SAFE_CAST(quantity AS INT64) AS quantity,
    SAFE_CAST(unit_price_local AS NUMERIC) AS unit_price_local,
    SAFE_CAST(discount_pct AS FLOAT64) AS discount_pct,
    SAFE_CAST(line_net_amount_local AS NUMERIC) AS line_net_amount_local,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_order_items`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY order_item_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
),
joined AS (
  SELECT
    d.order_item_id, d.order_id, d.product_id, d.quantity, d.discount_pct,
    d.unit_price_local, d.line_net_amount_local,
    o.currency AS _currency, o.order_date AS _order_date
  FROM deduped d
  INNER JOIN `__PROJECT__.silver.silver_orders` o ON d.order_id = o.order_id
  INNER JOIN `__PROJECT__.silver.silver_products` p ON d.product_id = p.product_id
),
fx_applied AS (
  SELECT
    j.*,
    ROUND(j.unit_price_local * fx.rate_to_usd, 2) AS unit_price_usd,
    ROUND(j.line_net_amount_local * fx.rate_to_usd, 2) AS line_net_amount_usd
  FROM joined j
  LEFT JOIN `__PROJECT__.silver.silver_exchange_rates` fx
    ON DATE_TRUNC(j._order_date, MONTH) = fx.rate_month
    AND j._currency = fx.currency
)
SELECT order_item_id, order_id, product_id, quantity,
       unit_price_local, unit_price_usd,
       discount_pct,
       line_net_amount_local, line_net_amount_usd
FROM fx_applied
WHERE order_item_id IS NOT NULL
  AND quantity > 0
  AND discount_pct >= 0 AND discount_pct < 1
  AND unit_price_usd IS NOT NULL
  AND line_net_amount_usd IS NOT NULL;
