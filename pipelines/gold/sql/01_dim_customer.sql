-- dim_customer: customer dimension, keyed by customer_id (natural key,
-- no surrogate key -- this dataset is fully recomputed each run, no SCD
-- history to version).
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_customer` AS
SELECT customer_id, first_name, last_name, email, region, country, city,
       home_currency, acquisition_channel, signup_date, is_active
FROM `__PROJECT__.silver.silver_customers`;
