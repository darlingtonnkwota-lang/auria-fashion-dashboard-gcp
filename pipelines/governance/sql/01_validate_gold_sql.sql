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

    -- Governance demo addition: dim_customer.email is a real column on
    -- the underlying gold table (customer PII), and this function's
    -- upstream checks never looked at column names at all -- only
    -- dataset/table names and DDL/DML keywords. That meant a drafted
    -- query that explicitly selected `email` would have sailed through
    -- validation and actually returned real addresses. This dataset
    -- has no SIN/SSN/phone/address/date-of-birth column anywhere (a
    -- request for one of those fails for a different reason, before
    -- this function is even called -- see agents/guardrails.py's
    -- check_restricted_topic), but email genuinely exists, so it needs
    -- an explicit, enforced block here, not just a prompt instruction
    -- the SQL agent could ignore or hallucinate around.
    WHEN REGEXP_CONTAINS(sql_text, r'(?i)\bemail\b') THEN
      'REJECTED: email is a personal identifier and is not an exposed field -- this assistant only exposes customer name, region, lifetime spend, and order history, never contact/identity details'

    -- Closes the same hole for `SELECT * FROM dim_customer` (or a CTE/
    -- subquery over it), which would return the same email column
    -- without the literal word "email" ever appearing in the query
    -- text, so the check above alone would miss it.
    WHEN REGEXP_CONTAINS(sql_text, r'(?i)select\s+\*\s+from\s+(`?[a-zA-Z0-9_.-]*\.)?`?dim_customer`?\b') THEN
      'REJECTED: dim_customer must be queried with explicit columns, not SELECT * -- personal identifiers are not exposed'

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
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT email FROM dim_customer');                                -- REJECTED (personal identifier)
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT * FROM dim_customer');                                     -- REJECTED (dim_customer needs explicit columns)
-- SELECT `__PROJECT__.gold.validate_gold_sql`('SELECT first_name, last_name FROM dim_customer');                 -- OK
