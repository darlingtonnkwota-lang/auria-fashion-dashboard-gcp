-- gold_ytd_by_year: each year's total through the same day-of-year
-- cutoff (the latest day-of-year actually present in the MOST RECENT
-- year -- not a dataset-wide max, which would just pick up Dec 31 from
-- any complete prior year), so a partial current year compares fairly
-- against prior full years. Completed orders only.
CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_ytd_by_year` AS
WITH items AS (
  SELECT
    order_id,
    line_net_amount_usd,
    line_margin_usd,
    EXTRACT(YEAR FROM order_date) AS yr,
    EXTRACT(DAYOFYEAR FROM order_date) AS doy
  FROM `__PROJECT__.gold.fct_order_items`
  WHERE order_status = 'Completed'
),
with_latest_year AS (
  SELECT *, MAX(yr) OVER () AS latest_year
  FROM items
),
with_cutoff AS (
  SELECT *, MAX(IF(yr = latest_year, doy, NULL)) OVER () AS cutoff_doy
  FROM with_latest_year
),
ytd AS (
  SELECT * FROM with_cutoff WHERE doy <= cutoff_doy
)
SELECT
  yr AS year,
  cutoff_doy,
  SUM(line_net_amount_usd) AS revenue_usd,
  COUNT(DISTINCT order_id) AS order_count,
  ROUND(SUM(line_net_amount_usd) / COUNT(DISTINCT order_id), 2) AS aov_usd,
  SUM(line_margin_usd) AS margin_usd
FROM ytd
GROUP BY yr, cutoff_doy
ORDER BY year;
