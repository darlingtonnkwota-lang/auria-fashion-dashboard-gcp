-- dim_warehouse: warehouse dimension, keyed by warehouse_id.
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_warehouse` AS
SELECT warehouse_id, warehouse_name, region, country, city
FROM `__PROJECT__.silver.silver_warehouses`;
