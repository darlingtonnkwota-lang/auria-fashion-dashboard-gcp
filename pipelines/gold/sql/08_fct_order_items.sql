-- fct_order_items: order-line grain sales fact (every order, Completed
-- and Cancelled), USD amounts, per-line margin, denormalized order/
-- customer context. Filter order_status = 'Completed' for revenue
-- reporting -- the raw fact keeps cancelled lines so a cancellation-rate
-- analysis never needs a trip back to Silver.
--
-- KNOWN LIMITATION (carried over from the Databricks build, on purpose):
-- line_cogs_usd uses each product's CURRENT unit_cost_usd -- Silver/
-- Bronze don't carry a cost-as-of-order-date history, so margin on an
-- order placed when a product's cost was different will be slightly
-- off. Not worth a real cost-history table for this demo dataset, where
-- costs don't change during the generated window anyway.
CREATE OR REPLACE TABLE `__PROJECT__.gold.fct_order_items` AS
SELECT
  i.order_item_id,
  i.order_id,
  i.product_id,
  i.quantity,
  i.unit_price_local,
  i.unit_price_usd,
  i.discount_pct,
  i.line_net_amount_local,
  i.line_net_amount_usd,
  o.order_date,
  o.customer_id,
  o.channel,
  o.store_id,
  o.fulfilling_warehouse_id,
  o.currency,
  o.promotion_id,
  o.order_status,
  o.payment_method,
  c.region AS customer_region,
  c.country AS customer_country,
  ROUND(i.quantity * p.unit_cost_usd, 2) AS line_cogs_usd,
  ROUND(i.line_net_amount_usd - ROUND(i.quantity * p.unit_cost_usd, 2), 2) AS line_margin_usd
FROM `__PROJECT__.silver.silver_order_items` i
LEFT JOIN `__PROJECT__.silver.silver_orders` o ON i.order_id = o.order_id
LEFT JOIN `__PROJECT__.silver.silver_customers` c ON o.customer_id = c.customer_id
LEFT JOIN `__PROJECT__.silver.silver_products` p ON i.product_id = p.product_id;
