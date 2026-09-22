-- gold_monthly_kpis: revenue, orders, AOV, units, margin, and returns by
-- calendar month. Completed orders only. The one table a "how's the
-- business doing" dashboard tile should query first.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_monthly_kpis` AS
WITH monthly AS (
  SELECT
    EXTRACT(YEAR FROM order_date) AS year,
    EXTRACT(MONTH FROM order_date) AS month,
    SUM(line_net_amount_usd) AS revenue_usd,
    COUNT(DISTINCT order_id) AS order_count,
    SUM(quantity) AS units_sold,
    SUM(line_margin_usd) AS margin_usd
  FROM `__PROJECT__.gold.fct_order_items`
  WHERE order_status = 'Completed'
  GROUP BY year, month
),
returns AS (
  SELECT
    EXTRACT(YEAR FROM return_date) AS year,
    EXTRACT(MONTH FROM return_date) AS month,
    SUM(refund_amount_usd) AS returns_usd,
    COUNT(*) AS return_count
  FROM `__PROJECT__.gold.fct_returns`
  GROUP BY year, month
)
SELECT
  m.year,
  m.month,
  m.revenue_usd,
  m.order_count,
  ROUND(m.revenue_usd / m.order_count, 2) AS aov_usd,
  m.units_sold,
  m.margin_usd,
  ROUND(m.margin_usd / m.revenue_usd * 100, 2) AS margin_pct,
  IFNULL(r.returns_usd, 0.0) AS returns_usd,
  IFNULL(r.return_count, 0) AS return_count,
  ROUND(IFNULL(r.returns_usd, 0.0) / m.revenue_usd * 100, 2) AS return_rate_pct
FROM monthly m
LEFT JOIN returns r ON m.year = r.year AND m.month = r.month
ORDER BY year, month;
