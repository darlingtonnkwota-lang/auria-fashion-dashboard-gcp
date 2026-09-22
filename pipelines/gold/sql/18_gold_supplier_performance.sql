-- gold_supplier_performance: actual PO lead time and on-time rate per
-- supplier, vs. the supplier's stated profile (dim_supplier). Dedupes to
-- one row per PO first -- a multi-line PO would otherwise get counted
-- once per line in the on-time/late rate, not once per PO.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_supplier_performance` AS
WITH pos AS (
  SELECT DISTINCT po_id, supplier_id, actual_lead_time_days, is_late
  FROM `__PROJECT__.gold.fct_purchase_order_lines`
),
agg AS (
  SELECT
    supplier_id,
    COUNT(*) AS po_count,
    ROUND(AVG(actual_lead_time_days), 1) AS avg_actual_lead_time_days,
    ROUND(AVG(CAST(is_late AS INT64)) * 100, 1) AS pct_late
  FROM pos
  GROUP BY supplier_id
)
SELECT
  a.supplier_id,
  a.po_count,
  a.avg_actual_lead_time_days,
  a.pct_late,
  s.supplier_name,
  s.avg_lead_time_days AS stated_avg_lead_time_days,
  s.reliability_score
FROM agg a
LEFT JOIN `__PROJECT__.silver.silver_suppliers` s ON a.supplier_id = s.supplier_id;
