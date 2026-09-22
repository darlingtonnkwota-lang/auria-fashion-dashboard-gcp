-- silver_dq_summary: Bronze-to-Silver row-count reconciliation, one row
-- per source table. The fast top-level check -- does anything not tie out.
-- Per-rule detail (which WHERE filter caught which rows) isn't split into
-- a separate dashboard the way a Lakeflow pipeline's Data Quality tab
-- does; if a table's dropped_row_count is unexpectedly nonzero, check
-- that table's own script in this folder for which filter is catching rows.
CREATE OR REPLACE TABLE `__PROJECT__.silver.silver_dq_summary` AS
WITH bronze_counts AS (
  SELECT 'customers' AS source_table, COUNT(*) AS bronze_row_count FROM `__PROJECT__.bronze.bronze_customers`
  UNION ALL SELECT 'products', COUNT(*) FROM `__PROJECT__.bronze.bronze_products`
  UNION ALL SELECT 'suppliers', COUNT(*) FROM `__PROJECT__.bronze.bronze_suppliers`
  UNION ALL SELECT 'stores', COUNT(*) FROM `__PROJECT__.bronze.bronze_stores`
  UNION ALL SELECT 'warehouses', COUNT(*) FROM `__PROJECT__.bronze.bronze_warehouses`
  UNION ALL SELECT 'orders', COUNT(*) FROM `__PROJECT__.bronze.bronze_orders`
  UNION ALL SELECT 'order_items', COUNT(*) FROM `__PROJECT__.bronze.bronze_order_items`
  UNION ALL SELECT 'returns', COUNT(*) FROM `__PROJECT__.bronze.bronze_returns`
  UNION ALL SELECT 'purchase_orders', COUNT(*) FROM `__PROJECT__.bronze.bronze_purchase_orders`
  UNION ALL SELECT 'purchase_order_lines', COUNT(*) FROM `__PROJECT__.bronze.bronze_purchase_order_lines`
  UNION ALL SELECT 'inventory_movements', COUNT(*) FROM `__PROJECT__.bronze.bronze_inventory_movements`
  UNION ALL SELECT 'inventory_snapshots', COUNT(*) FROM `__PROJECT__.bronze.bronze_inventory_snapshots`
  UNION ALL SELECT 'exchange_rates', COUNT(*) FROM `__PROJECT__.bronze.bronze_exchange_rates`
  UNION ALL SELECT 'promotions', COUNT(*) FROM `__PROJECT__.bronze.bronze_promotions`
),
silver_counts AS (
  SELECT 'customers' AS source_table, COUNT(*) AS silver_row_count FROM `__PROJECT__.silver.silver_customers`
  UNION ALL SELECT 'products', COUNT(*) FROM `__PROJECT__.silver.silver_products`
  UNION ALL SELECT 'suppliers', COUNT(*) FROM `__PROJECT__.silver.silver_suppliers`
  UNION ALL SELECT 'stores', COUNT(*) FROM `__PROJECT__.silver.silver_stores`
  UNION ALL SELECT 'warehouses', COUNT(*) FROM `__PROJECT__.silver.silver_warehouses`
  UNION ALL SELECT 'orders', COUNT(*) FROM `__PROJECT__.silver.silver_orders`
  UNION ALL SELECT 'order_items', COUNT(*) FROM `__PROJECT__.silver.silver_order_items`
  UNION ALL SELECT 'returns', COUNT(*) FROM `__PROJECT__.silver.silver_returns`
  UNION ALL SELECT 'purchase_orders', COUNT(*) FROM `__PROJECT__.silver.silver_purchase_orders`
  UNION ALL SELECT 'purchase_order_lines', COUNT(*) FROM `__PROJECT__.silver.silver_purchase_order_lines`
  UNION ALL SELECT 'inventory_movements', COUNT(*) FROM `__PROJECT__.silver.silver_inventory_movements`
  UNION ALL SELECT 'inventory_snapshots', COUNT(*) FROM `__PROJECT__.silver.silver_inventory_snapshots`
  UNION ALL SELECT 'exchange_rates', COUNT(*) FROM `__PROJECT__.silver.silver_exchange_rates`
  UNION ALL SELECT 'promotions', COUNT(*) FROM `__PROJECT__.silver.silver_promotions`
)
SELECT
  b.source_table,
  b.bronze_row_count,
  s.silver_row_count,
  b.bronze_row_count - s.silver_row_count AS dropped_row_count
FROM bronze_counts b
JOIN silver_counts s USING (source_table)
ORDER BY source_table;
