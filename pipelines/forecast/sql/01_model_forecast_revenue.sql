-- Phase 6 -- BigQuery ML model for the revenue forecast.
--
-- ARIMA_PLUS is the primary approach chosen in gcp_strategy.md section 6
-- as the closer BigQuery analogue to what the Databricks build's
-- ml/forecast_training.py notebook does by hand with Prophet: a trained,
-- evaluable model fit directly on the monthly revenue history in
-- gold_monthly_kpis, not a zero-shot call. (AI.FORECAST/TimesFM is the
-- documented zero-shot alternative -- see the setup doc for this phase.)
--
-- The current in-progress calendar month is excluded from training -- a
-- partial month looks like a demand cliff to a forecasting model, the
-- same instinct behind gold_ytd_by_year's day-of-year cutoff (applied
-- there to a YTD comparison instead). Excluding it here just means the
-- model's first forecast month IS that same in-progress month, which is
-- exactly what "project revenue over the next 6 months" should show.

CREATE OR REPLACE MODEL `__PROJECT__.gold.model_forecast_revenue`
OPTIONS(
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = 'month_date',
  time_series_data_col = 'value',
  auto_arima = TRUE,
  data_frequency = 'MONTHLY'
) AS
SELECT
  DATE(year, month, 1) AS month_date,
  revenue_usd AS value
FROM `__PROJECT__.gold.gold_monthly_kpis`
WHERE NOT (
  year = EXTRACT(YEAR FROM CURRENT_DATE())
  AND month = EXTRACT(MONTH FROM CURRENT_DATE())
);
