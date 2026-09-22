-- dim_supplier: supplier dimension, keyed by supplier_id.
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_supplier` AS
SELECT supplier_id, supplier_name, country, region, category_focus,
       avg_lead_time_days, lead_time_stddev_days, reliability_score
FROM `__PROJECT__.silver.silver_suppliers`;
