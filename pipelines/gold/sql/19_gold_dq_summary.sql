-- gold_dq_summary: Silver-to-Gold row-count reconciliation for the fact
-- tables. Every join used to build a fact is a required, already-FK-
-- checked Silver relationship on a unique key, so row_count_diff should
-- always be 0 -- a nonzero value means a join fanned out or dropped rows
-- and is worth investigating before trusting anything built on that fact.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_dq_summary` AS
WITH silver_counts AS (
  SELECT 'fct_order_items' AS fact_table, COUNT(*) AS silver_row_count FROM `__PROJECT__.silver.silver_order_items`
  UNION ALL SELECT 'fct_returns', COUNT(*) FROM `__PROJECT__.silver.silver_returns`
  UNION ALL SELECT 'fct_purchase_order_lines', COUNT(*) FROM `__PROJECT__.silver.silver_purchase_order_lines`
  UNION ALL SELECT 'fct_inventory_snapshots', COUNT(*) FROM `__PROJECT__.silver.silver_inventory_snapshots`
),
gold_counts AS (
  SELECT 'fct_order_items' AS fact_table, COUNT(*) AS gold_row_count FROM `__PROJECT__.gold.fct_order_items`
  UNION ALL SELECT 'fct_returns', COUNT(*) FROM `__PROJECT__.gold.fct_returns`
  UNION ALL SELECT 'fct_purchase_order_lines', COUNT(*) FROM `__PROJECT__.gold.fct_purchase_order_lines`
  UNION ALL SELECT 'fct_inventory_snapshots', COUNT(*) FROM `__PROJECT__.gold.fct_inventory_snapshots`
)
SELECT
  s.fact_table,
  s.silver_row_count,
  g.gold_row_count,
  g.gold_row_count - s.silver_row_count AS row_count_diff
FROM silver_counts s
JOIN gold_counts g USING (fact_table)
ORDER BY fact_table;
