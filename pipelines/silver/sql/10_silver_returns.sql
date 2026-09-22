-- silver_returns: typed, deduped returns, FK-checked against order_items,
-- USD-normalized via the parent order's currency. Rows where the FX join
-- doesn't resolve (refund_amount_usd ends up NULL) are dropped.
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_returns` AS
WITH typed AS (
  SELECT
    return_id,
    order_item_id,
    SAFE_CAST(return_date AS DATE) AS return_date,
    SAFE_CAST(quantity_returned AS INT64) AS quantity_returned,
    reason,
    SAFE_CAST(refund_amount_local AS NUMERIC) AS refund_amount_local,
    SAFE_CAST(restocked AS BOOL) AS restocked,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_returns`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY return_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
),
joined AS (
  SELECT
    d.return_id, d.order_item_id, d.return_date, d.quantity_returned,
    d.reason, d.refund_amount_local, d.restocked,
    o.currency AS _currency
  FROM deduped d
  INNER JOIN `__PROJECT__.silver.silver_order_items` oi ON d.order_item_id = oi.order_item_id
  INNER JOIN `__PROJECT__.silver.silver_orders` o ON oi.order_id = o.order_id
),
fx_applied AS (
  SELECT
    j.*,
    ROUND(j.refund_amount_local * fx.rate_to_usd, 2) AS refund_amount_usd
  FROM joined j
  LEFT JOIN `__PROJECT__.silver.silver_exchange_rates` fx
    ON DATE_TRUNC(j.return_date, MONTH) = fx.rate_month
    AND j._currency = fx.currency
)
SELECT return_id, order_item_id, return_date, quantity_returned, reason,
       refund_amount_local, refund_amount_usd, restocked
FROM fx_applied
WHERE return_id IS NOT NULL
  AND quantity_returned > 0
  AND refund_amount_usd IS NOT NULL;
