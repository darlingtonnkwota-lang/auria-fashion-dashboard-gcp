-- Phase 6 -- backtest-only model, trained on history through
-- __HOLDOUT_CUTOFF__ (exclusive), holding out the last 6 known complete
-- months as a genuine test set -- the BigQuery equivalent of the
-- Databricks build's Prophet rolling-origin cross_validation, simplified
-- to a single holdout window rather than multiple rolling cutoffs (named
-- as a deliberate limitation in the setup doc for this phase, the same
-- "read the number in context" spirit as the Databricks backtest).
-- run_forecast.py fills in __HOLDOUT_CUTOFF__ before running this --
-- never run it with that placeholder still literal.

CREATE OR REPLACE MODEL `__PROJECT__.gold.model_forecast_revenue_backtest`
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
WHERE DATE(year, month, 1) < DATE('__HOLDOUT_CUTOFF__');
