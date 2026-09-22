-- fct_purchase_order_lines: PO-line grain supply chain fact, with PO
-- header context and computed actual_lead_time_days / is_late.
CREATE OR REPLACE TABLE `__PROJECT__.gold.fct_purchase_order_lines` AS
SELECT
  l.po_line_id,
  l.po_id,
  l.product_id,
  l.quantity,
  l.unit_cost_usd,
  po.supplier_id,
  po.warehouse_id,
  po.order_date,
  po.expected_date,
  po.received_date,
  po.status,
  CASE WHEN po.received_date IS NOT NULL
       THEN DATE_DIFF(po.received_date, po.order_date, DAY)
       ELSE NULL END AS actual_lead_time_days,
  po.status = 'Received (Late)' AS is_late
FROM `__PROJECT__.silver.silver_purchase_order_lines` l
LEFT JOIN `__PROJECT__.silver.silver_purchase_orders` po ON l.po_id = po.po_id;
