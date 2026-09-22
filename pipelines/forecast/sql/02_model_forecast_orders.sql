-- Phase 6 -- BigQuery ML model for the order-volume forecast. Same
-- shape and same excluded-current-month reasoning as
-- 01_model_forecast_revenue.sql -- see that file's header comment.

CREATE OR REPLACE MODEL `__PROJECT__.gold.model_forecast_orders`
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
WHERE NOT (
  year = EXTRACT(YEAR FROM CURRENT_DATE())
  AND month = EXTRACT(MONTH FROM CURRENT_DATE())
);
