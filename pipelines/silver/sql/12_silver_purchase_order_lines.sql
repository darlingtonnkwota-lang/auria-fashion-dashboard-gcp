-- silver_purchase_order_lines: typed, deduped PO lines, FK-checked
-- against purchase_orders/products (cost already in USD, no FX needed)
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_purchase_order_lines` AS
WITH typed AS (
  SELECT
    po_line_id,
    po_id,
    product_id,
    SAFE_CAST(quantity AS INT64) AS quantity,
    SAFE_CAST(unit_cost_usd AS NUMERIC) AS unit_cost_usd,
    _ingested_at
  FROM `__PROJECT__.bronze.bronze_purchase_order_lines`
),
deduped AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT typed.*, ROW_NUMBER() OVER (
      PARTITION BY po_line_id ORDER BY _ingested_at DESC
    ) AS rn
    FROM typed
  )
  WHERE rn = 1
)
SELECT d.po_line_id, d.po_id, d.product_id, d.quantity, d.unit_cost_usd
FROM deduped d
INNER JOIN `__PROJECT__.silver.silver_purchase_orders` po ON d.po_id = po.po_id
INNER JOIN `__PROJECT__.silver.silver_products` p ON d.product_id = p.product_id
WHERE d.po_line_id IS NOT NULL
  AND d.quantity > 0;
