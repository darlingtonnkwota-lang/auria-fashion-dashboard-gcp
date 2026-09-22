-- Phase 5 -- authorized views, BigQuery's closest analogue to the
-- Databricks build's Unity Catalog grants pattern: a view in its own
-- dataset (`authorized`) that queries `gold` directly, so the agent's
-- identity can be scoped to SELECT on `authorized` only and never needs
-- direct access to the `gold` dataset itself -- the same "governed
-- surface, not raw tables" instinct as the Databricks build's authorized
-- views over Unity Catalog grants.
--
-- 18 objects (7 dim_*, 4 fct_*, 7 curated gold_*) -- gold_dq_summary is
-- deliberately excluded, same as the Databricks allow-list. A 19th object,
-- gold_sales_forecast, will be added here once GCP Phase 6 (forecasting)
-- lands -- it doesn't exist yet, so it isn't wrapped or referenced by the
-- context layer/guardrails allow-list until then.
--
-- To actually make this dataset the ENFORCED boundary (not just a SQL
-- convenience), BigQuery's "authorized view" feature needs one more
-- console/gcloud step this script doesn't do: sharing the `authorized`
-- dataset's views as authorized views on `gold` (bq update
-- --view_authorization, or Console -> gold dataset -> Sharing -> Authorized
-- views), then granting a dedicated service account roles/bigquery.dataViewer
-- on `authorized` ONLY (not on `gold`). See docs/gcp_phase5_governance_agents_setup.md
-- -- this POC runs under your own gcloud identity, which already has
-- access to `gold` directly, so the views alone don't add enforcement
-- yet; they set up the pattern and the SQL agent's queries always target
-- them, ready for the day this project gets promoted with a real scoped
-- service account.

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_customer` AS
SELECT * FROM `__PROJECT__.gold.dim_customer`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_product` AS
SELECT * FROM `__PROJECT__.gold.dim_product`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_supplier` AS
SELECT * FROM `__PROJECT__.gold.dim_supplier`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_store` AS
SELECT * FROM `__PROJECT__.gold.dim_store`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_warehouse` AS
SELECT * FROM `__PROJECT__.gold.dim_warehouse`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_promotion` AS
SELECT * FROM `__PROJECT__.gold.dim_promotion`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.dim_date` AS
SELECT * FROM `__PROJECT__.gold.dim_date`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.fct_order_items` AS
SELECT * FROM `__PROJECT__.gold.fct_order_items`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.fct_returns` AS
SELECT * FROM `__PROJECT__.gold.fct_returns`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.fct_purchase_order_lines` AS
SELECT * FROM `__PROJECT__.gold.fct_purchase_order_lines`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.fct_inventory_snapshots` AS
SELECT * FROM `__PROJECT__.gold.fct_inventory_snapshots`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_monthly_kpis` AS
SELECT * FROM `__PROJECT__.gold.gold_monthly_kpis`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_ytd_by_year` AS
SELECT * FROM `__PROJECT__.gold.gold_ytd_by_year`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_top_products_monthly` AS
SELECT * FROM `__PROJECT__.gold.gold_top_products_monthly`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_top_customers_monthly` AS
SELECT * FROM `__PROJECT__.gold.gold_top_customers_monthly`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_returns_by_product_monthly` AS
SELECT * FROM `__PROJECT__.gold.gold_returns_by_product_monthly`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_channel_performance` AS
SELECT * FROM `__PROJECT__.gold.gold_channel_performance`;

CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_supplier_performance` AS
SELECT * FROM `__PROJECT__.gold.gold_supplier_performance`;

-- Phase 6: gold_sales_forecast is the 19th governed object.
CREATE OR REPLACE VIEW `__PROJECT__.authorized.gold_sales_forecast` AS
SELECT * FROM `__PROJECT__.gold.gold_sales_forecast`;
