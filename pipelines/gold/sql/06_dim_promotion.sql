-- dim_promotion: promotion dimension, keyed by promotion_id.
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_promotion` AS
SELECT promotion_id, promotion_name, start_date, end_date, discount_pct, scope_region
FROM `__PROJECT__.silver.silver_promotions`;
