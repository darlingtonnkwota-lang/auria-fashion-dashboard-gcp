-- dim_date: calendar dimension, 2022-01-01 through 2026-12-31.
-- day_of_year is what makes YTD-vs-prior-year comparisons apples-to-apples
-- -- see gold_ytd_by_year.
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_date` AS
SELECT
  date_key,
  EXTRACT(YEAR FROM date_key) AS year,
  EXTRACT(QUARTER FROM date_key) AS quarter,
  EXTRACT(MONTH FROM date_key) AS month,
  FORMAT_DATE('%B', date_key) AS month_name,
  EXTRACT(DAY FROM date_key) AS day_of_month,
  EXTRACT(DAYOFYEAR FROM date_key) AS day_of_year,
  EXTRACT(DAYOFWEEK FROM date_key) AS day_of_week,
  FORMAT_DATE('%A', date_key) AS day_name,
  EXTRACT(DAYOFWEEK FROM date_key) IN (1, 7) AS is_weekend,
  EXTRACT(ISOWEEK FROM date_key) AS week_of_year
FROM UNNEST(GENERATE_DATE_ARRAY('2022-01-01', '2026-12-31', INTERVAL 1 DAY)) AS date_key;
