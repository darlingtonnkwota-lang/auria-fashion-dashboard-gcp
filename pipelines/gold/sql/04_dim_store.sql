-- dim_store: store dimension, keyed by store_id.
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_store` AS
SELECT store_id, store_name, region, country, city, currency, store_type,
       opened_date, home_warehouse_id
FROM `__PROJECT__.silver.silver_stores`;
