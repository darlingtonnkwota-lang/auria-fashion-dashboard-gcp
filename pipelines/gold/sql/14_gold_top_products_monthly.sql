-- gold_top_products_monthly: revenue/units/margin by product by month,
-- Completed orders only. Keyed by product_id -- join to dim_product for
-- name/category.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_top_products_monthly` AS
SELECT
  EXTRACT(YEAR FROM order_date) AS year,
  EXTRACT(MONTH FROM order_date) AS month,
  product_id,
  SUM(line_net_amount_usd) AS revenue_usd,
  SUM(quantity) AS units_sold,
  SUM(line_margin_usd) AS margin_usd
FROM `__PROJECT__.gold.fct_order_items`
WHERE order_status = 'Completed'
GROUP BY year, month, product_id;
