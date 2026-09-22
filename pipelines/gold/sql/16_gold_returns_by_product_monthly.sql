-- gold_returns_by_product_monthly: return rate by product by month --
-- return_count / lines_sold that month. Keyed by product_id -- join to
-- dim_product for name/category.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_returns_by_product_monthly` AS
WITH sales AS (
  SELECT
    EXTRACT(YEAR FROM order_date) AS year,
    EXTRACT(MONTH FROM order_date) AS month,
    product_id,
    COUNT(*) AS lines_sold
  FROM `__PROJECT__.gold.fct_order_items`
  WHERE order_status = 'Completed'
  GROUP BY year, month, product_id
),
rets AS (
  SELECT
    EXTRACT(YEAR FROM return_date) AS year,
    EXTRACT(MONTH FROM return_date) AS month,
    product_id,
    COUNT(*) AS return_count,
    SUM(refund_amount_usd) AS return_amount_usd
  FROM `__PROJECT__.gold.fct_returns`
  GROUP BY year, month, product_id
)
SELECT
  s.year,
  s.month,
  s.product_id,
  s.lines_sold,
  IFNULL(r.return_count, 0) AS return_count,
  IFNULL(r.return_amount_usd, 0.0) AS return_amount_usd,
  ROUND(IFNULL(r.return_count, 0) / s.lines_sold * 100, 2) AS return_rate_pct
FROM sales s
LEFT JOIN rets r
  ON s.year = r.year AND s.month = r.month AND s.product_id = r.product_id;
