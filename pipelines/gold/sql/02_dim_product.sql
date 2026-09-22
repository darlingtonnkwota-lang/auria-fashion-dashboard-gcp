-- dim_product: product dimension, keyed by product_id, with an
-- is_discontinued flag derived from discontinued_date.
CREATE OR REPLACE TABLE `__PROJECT__.gold.dim_product` AS
SELECT product_id, product_name, category, sub_category, gender, supplier_id,
       season_affinity, size_range, unit_cost_usd, unit_price_usd,
       launch_date, discontinued_date,
       discontinued_date IS NOT NULL AS is_discontinued
FROM `__PROJECT__.silver.silver_products`;
