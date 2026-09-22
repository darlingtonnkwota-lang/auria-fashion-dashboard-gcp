-- Phase 6 -- gold_sales_forecast: history + a 6-month-ahead forecast for
-- revenue_usd and order_count, one row per metric x month. The direct
-- port of the Databricks build's gold_sales_forecast table (see that
-- repo's docs/phase7_predictive_analytics_setup.md), built from
-- ML.FORECAST against the two ARIMA_PLUS models in 01/02 instead of a
-- Prophet notebook -- same table shape, so the context layer/metric
-- specs ported over without changing the downstream contract:
--   metric        -- 'revenue_usd' or 'order_count'
--   month_date    -- first of the month
--   value         -- actual (history) or forecast_value (forecast)
--   lower_bound / upper_bound -- NULL on history rows; a 90% prediction
--                    interval on forecast rows
--   is_forecast   -- FALSE for history, TRUE for forecast
--   generated_at  -- when this table was last rebuilt
--
-- History rows exclude the current in-progress calendar month (the same
-- exclusion the two models train on) -- gold_monthly_kpis stays the
-- fresher, authoritative source for that partial month; this table's
-- job is forward-looking, not a second copy of already-known actuals.
-- See context/metric_specs.yaml's revenue_forecast_usd/order_count_forecast
-- notes for the same rule stated to the SQL agent.

CREATE OR REPLACE TABLE `__PROJECT__.gold.gold_sales_forecast` AS
WITH history AS (
  SELECT
    'revenue_usd' AS metric,
    DATE(year, month, 1) AS month_date,
    revenue_usd AS value,
    CAST(NULL AS FLOAT64) AS lower_bound,
    CAST(NULL AS FLOAT64) AS upper_bound,
    FALSE AS is_forecast
  FROM `__PROJECT__.gold.gold_monthly_kpis`
  WHERE NOT (
    year = EXTRACT(YEAR FROM CURRENT_DATE())
    AND month = EXTRACT(MONTH FROM CURRENT_DATE())
  )
  UNION ALL
  SELECT
    'order_count' AS metric,
    DATE(year, month, 1) AS month_date,
    CAST(order_count AS FLOAT64) AS value,
    CAST(NULL AS FLOAT64) AS lower_bound,
    CAST(NULL AS FLOAT64) AS upper_bound,
    FALSE AS is_forecast
  FROM `__PROJECT__.gold.gold_monthly_kpis`
  WHERE NOT (
    year = EXTRACT(YEAR FROM CURRENT_DATE())
    AND month = EXTRACT(MONTH FROM CURRENT_DATE())
  )
),
forecast_revenue AS (
  SELECT
    'revenue_usd' AS metric,
    DATE(forecast_timestamp) AS month_date,
    forecast_value AS value,
    prediction_interval_lower_bound AS lower_bound,
    prediction_interval_upper_bound AS upper_bound,
    TRUE AS is_forecast
  FROM ML.FORECAST(
    MODEL `__PROJECT__.gold.model_forecast_revenue`,
    STRUCT(6 AS horizon, 0.9 AS confidence_level)
  )
),
forecast_orders AS (
  SELECT
    'order_count' AS metric,
    DATE(forecast_timestamp) AS month_date,
    forecast_value AS value,
    prediction_interval_lower_bound AS lower_bound,
    prediction_interval_upper_bound AS upper_bound,
    TRUE AS is_forecast
  FROM ML.FORECAST(
    MODEL `__PROJECT__.gold.model_forecast_orders`,
    STRUCT(6 AS horizon, 0.9 AS confidence_level)
  )
)
SELECT metric, month_date, value, lower_bound, upper_bound, is_forecast, CURRENT_TIMESTAMP() AS generated_at FROM history
UNION ALL
SELECT metric, month_date, value, lower_bound, upper_bound, is_forecast, CURRENT_TIMESTAMP() AS generated_at FROM forecast_revenue
UNION ALL
SELECT metric, month_date, value, lower_bound, upper_bound, is_forecast, CURRENT_TIMESTAMP() AS generated_at FROM forecast_orders
ORDER BY metric, month_date;
