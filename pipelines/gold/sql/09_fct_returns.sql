-- fct_returns: return-grain fact, USD amounts, denormalized order_id/
-- product_id context. Kept as its own fact, never netted into
-- fct_order_items -- a sale and a later partial return are different
-- events; net-of-returns numbers come from joining the two facts.
CREATE OR REPLACE TABLE `__PROJECT__.gold.fct_returns` AS
SELECT
  r.return_id,
  r.order_item_id,
  r.return_date,
  r.quantity_returned,
  r.reason,
  r.refund_amount_local,
  r.refund_amount_usd,
  r.restocked,
  i.order_id,
  i.product_id
FROM `__PROJECT__.silver.silver_returns` r
LEFT JOIN `__PROJECT__.silver.silver_order_items` i ON r.order_item_id = i.order_item_id;
