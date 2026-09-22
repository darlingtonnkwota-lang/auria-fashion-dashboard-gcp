-- Phase 5 -- Validation/Execution agent's governed BigQuery SQL function.
--
-- This is the BigQuery port of the Databricks build's
-- sql/gold_validate_function.sql (a Unity Catalog SQL function there).
-- BigQuery's equivalent governed object is a persistent SQL function --
-- it lives IN BigQuery, shows up as a routine in the dataset, has its own
-- IAM grants, and every call is auditable in job history the same way any
-- other governed query is -- so the check is real and inspectable outside
-- the agent code, not just a Python `if` statement someone could bypass
-- by calling the BigQuery client directly instead of going through
-- agents/guardrails.py.
--
-- Known limitation, documented on purpose (matches the Databricks build's
-- own documented limitation in agents/guardrails.py's module docstring):
-- this uses regex checks, not a real SQL parser, and it validates SHAPE
-- (single SELECT, no DDL/DML keywords, no bronze/silver references, no
-- gold_dq_summary) -- it does not by itself enforce row limits or
-- timeouts. Those are applied in agents/guardrails.py's execute(), by
-- wrapping the query and running it with a job timeout. This POC also
-- runs queries under your own gcloud identity rather than a dedicated
-- read-only service account scoped to SELECT-only grants on `authorized` --
-- same simplification the Databricks build made, named here rather than
-- presented as more airtight than it is.

CREATE OR REPLACE FUNCTION `__PROJECT__.gold.validate_gold_sql`(sql_text STRING)
RETURNS STRING AS (
  CASE
    WHEN sql_text IS NULL OR TRIM(sql_text) = '' THEN
      'REJECTED: empty query'

    WHEN (
      SELECT COUNT(*) FROM UNNEST(SPLIT(sql_text, ';')) AS stmt WHERE TRIM(stmt) <> ''
    ) > 1 THEN
      'REJECTED: multiple statements are not allowed'

    WHEN NOT REGEXP_CONTAINS(TRIM(sql_text), r'(?i)^(SELECT|WITH)\s') THEN
      'REJECTED: only a single SELECT (or WITH ... SELECT) statement is allowed'

    WHEN REGEXP_CONTAINS(
      sql_text,
      r'(?i)\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|CALL|EXPORT|LOAD)\b'
    ) THEN
      'REJECTED: DDL/DML keyword found -- read-only SELECT only'

    WHEN REGEXP_CONTAINS(sql_text, r'(?i)\b(bronze|silver)\.')
      OR REGEXP_CONTAINS(sql_text, r'(?i)\b(bronze_|silver_)[a-zA-Z_]+') THEN
      'REJECTED: only gold/authorized objects may be queried'

    WHEN REGEXP_CONTAINS(sql_text, r'(?i)\bgold_dq_summary\b') THEN
      'REJECTED: gold_dq_summary is an internal reconciliation table, not a reporting object'

    ELSE 'OK'
  END
);

-- Quick sanity check once created (run these as separate statements, not
-- part of the CREATE above):
--
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT 1');                                                    -- OK
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT * FROM fct_order_items; DROP TABLE x');                 -- REJECTED (multiple statements)
-- SELECT `__PROJECT__.gold.validate_gold_sql`('DELETE FROM fct_order_items');                                 -- REJECTED (DDL/DML keyword)
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT * FROM `__PROJECT__.bronze.bronze_customers`');          -- REJECTED (bronze)
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT * FROM gold_dq_summary');                                -- REJECTED (internal table)
