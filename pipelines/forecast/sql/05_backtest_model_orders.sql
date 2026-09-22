-- Phase 6 -- backtest-only model for order_count. See
-- 04_backtest_model_revenue.sql's header comment.

CREATE OR REPLACE MODEL `__PROJECT__.gold.model_forecast_orders_backtest`
OPTIONS(
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = 'month_date',
  time_series_data_col = 'value',
  auto_arima = TRUE,
  data_frequency = 'MONTHLY'
) AS
SELECT
  DATE(year, month, 1) AS month_date,
  CAST(order_count AS FLOAT64) AS value
FROM `__PROJECT__.gold.gold_monthly_kpis`
WHERE DATE(year, month, 1) < DATE('__HOLDOUT_CUTOFF__');
