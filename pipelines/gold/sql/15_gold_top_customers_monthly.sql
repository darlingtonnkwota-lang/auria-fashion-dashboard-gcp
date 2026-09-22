-- gold_top_customers_monthly: revenue/order-count by customer by month,
-- Completed orders only. Keyed by customer_id -- join to dim_customer
-- for name/region.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_top_customers_monthly` AS
SELECT
  EXTRACT(YEAR FROM order_date) AS year,
  EXTRACT(MONTH FROM order_date) AS month,
  customer_id,
  SUM(line_net_amount_usd) AS revenue_usd,
  COUNT(DISTINCT order_id) AS order_count
FROM `__PROJECT__.gold.fct_order_items`
WHERE order_status = 'Completed'
GROUP BY year, month, customer_id;
