-- Phase 6 -- backtest accuracy report: forecasts the 6 held-out months
-- from each backtest-only model (04/05) and compares them against the
-- actuals gold_monthly_kpis already has for that same window, computing
-- MAPE/RMSE/MAE by hand in SQL -- a real, inspectable number, not a
-- trusted claim. run_forecast.py prints this query's rows directly.
-- __HOLDOUT_CUTOFF__ is filled in by run_forecast.py, same as 04/05.

WITH actual AS (
  SELECT
    DATE(year, month, 1) AS month_date,
    'revenue_usd' AS metric,
    revenue_usd AS actual_value
  FROM `__PROJECT__.gold.gold_monthly_kpis`
  WHERE DATE(year, month, 1) >= DATE('__HOLDOUT_CUTOFF__')
    AND NOT (year = EXTRACT(YEAR FROM CURRENT_DATE()) AND month = EXTRACT(MONTH FROM CURRENT_DATE()))
  UNION ALL
  SELECT
    DATE(year, month, 1) AS month_date,
    'order_count' AS metric,
    CAST(order_count AS FLOAT64) AS actual_value
  FROM `__PROJECT__.gold.gold_monthly_kpis`
  WHERE DATE(year, month, 1) >= DATE('__HOLDOUT_CUTOFF__')
    AND NOT (year = EXTRACT(YEAR FROM CURRENT_DATE()) AND month = EXTRACT(MONTH FROM CURRENT_DATE()))
),
predicted AS (
  SELECT
    DATE(forecast_timestamp) AS month_date,
    'revenue_usd' AS metric,
    forecast_value AS predicted_value
  FROM ML.FORECAST(
    MODEL `__PROJECT__.gold.model_forecast_revenue_backtest`,
    STRUCT(6 AS horizon, 0.9 AS confidence_level)
  )
  UNION ALL
  SELECT
    DATE(forecast_timestamp) AS month_date,
    'order_count' AS metric,
    forecast_value AS predicted_value
  FROM ML.FORECAST(
    MODEL `__PROJECT__.gold.model_forecast_orders_backtest`,
    STRUCT(6 AS horizon, 0.9 AS confidence_level)
  )
)
SELECT
  a.metric,
  COUNT(*) AS holdout_months,
  ROUND(AVG(ABS(a.actual_value - p.predicted_value) / a.actual_value) * 100, 2) AS mape_pct,
  ROUND(SQRT(AVG(POW(a.actual_value - p.predicted_value, 2))), 2) AS rmse,
  ROUND(AVG(ABS(a.actual_value - p.predicted_value)), 2) AS mae
FROM actual a
JOIN predicted p USING (month_date, metric)
GROUP BY a.metric
ORDER BY a.metric;
