-- gold_channel_performance: revenue/orders/AOV by channel and customer
-- home region, by month. Completed orders only. Revenue is attributed to
-- the customer's home region, not the store's, regardless of channel --
-- one consistent rule everywhere, since Online orders have no store.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_channel_performance` AS
SELECT
  EXTRACT(YEAR FROM order_date) AS year,
  EXTRACT(MONTH FROM order_date) AS month,
  channel,
  customer_region,
  SUM(line_net_amount_usd) AS revenue_usd,
  COUNT(DISTINCT order_id) AS order_count,
  ROUND(SUM(line_net_amount_usd) / COUNT(DISTINCT order_id), 2) AS aov_usd
FROM `__PROJECT__.gold.fct_order_items`
WHERE order_status = 'Completed'
GROUP BY year, month, channel, customer_region;
