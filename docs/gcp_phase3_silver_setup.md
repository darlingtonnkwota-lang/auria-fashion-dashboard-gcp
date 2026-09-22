# GCP Phase 3 — Silver Transform Setup Guide

Goal: turn the 14 `bronze_*` tables (all-STRING, raw-as-ingested) into
typed, deduped, FK-checked, USD-normalized `silver_*` tables, and prove
Silver ties back to Bronze row-for-row (accounting for every legitimate
drop) — the same job the Databricks build's Lakeflow Declarative Pipeline
does, ported to plain BigQuery SQL since BigQuery has no DLT-style
pipeline framework.

**Status: ready to run.** All 15 SQL scripts (14 `silver_*` tables +
`silver_dq_summary`) and the Python runner are committed to `dev`.

## What's different from the Databricks version, and what isn't

Every rule is carried over identically — same dedup logic, same required
vs. nullable FK checks, same FX normalization approach, same reconciliation
table shape. What changes is only the mechanism:

| Databricks | BigQuery (this phase) |
|---|---|
| A Lakeflow Declarative Pipeline, one Python file, `@dlt.table` decorators | 15 plain `.sql` scripts in `pipelines/silver/sql/`, run in order by `run_silver.py` |
| `@dlt.expect_or_drop("name", "condition")` — named, shows in a Data Quality tab | The same condition as a `WHERE` filter in that table's script — no separate dashboard, but the effect (drop the row) is identical |
| `_validate_fk` / `_validate_nullable_fk` as a `left_semi` join | `INNER JOIN` (required FK) or `LEFT JOIN` + `WHERE fk IS NULL OR match IS NOT NULL` (nullable FK) |
| Dedup via a `ROW_NUMBER()` window function (PySpark) | The identical `ROW_NUMBER()` window function (BigQuery SQL) |
| Streaming-capable via `dlt.read_stream()` (not used — batch on purpose) | Not applicable — every script is a batch `CREATE OR REPLACE TABLE ... AS SELECT` |

## Decisions this phase locks in (same as the Databricks build)

- **Reporting currency: USD.** Every local-currency amount (`*_local`) gets
  a sibling `*_usd` column; the original is kept, nothing is overwritten.
- **A row that fails a data quality check is dropped and logged, never
  silently kept.** "Logged" here means `silver_dq_summary`'s
  `dropped_row_count` column — the fast top-level check.
- **Silver is batch and fully recomputed each run** — no incremental
  logic, matching the Databricks build's own choice at this data volume
  (~230K rows total; a full recompute is a few seconds, not worth the
  complexity of tracking incremental state).

## Run it — Cloud Shell

From the same clone used for Phase 1/2 (pull first if it's been a
while):

```bash
cd ~/auria-fashion-dashboard-gcp
git pull origin dev
source .venv/bin/activate   # if not already active
python pipelines/silver/run_silver.py --project clientgcpkraftheinzadpoc
```

It prints `OK  <script name>` as each of the 15 scripts runs, in
dependency order (dimensions first — customers, products, suppliers,
warehouses, stores, promotions, exchange rates — then facts that depend
on them: orders, order_items, returns, purchase_orders,
purchase_order_lines, inventory_movements, inventory_snapshots — then the
reconciliation table last).

## Verify

```bash
bq query --use_legacy_sql=false \
  'SELECT * FROM `clientgcpkraftheinzadpoc.silver.silver_dq_summary` ORDER BY source_table'
```

Expect `dropped_row_count = 0` for every table — this dataset was already
validated end-to-end at generation time (16 integrity checks passing per
`data_dictionary.md`), so nothing here should actually trip a Silver-level
rule. If a table shows a nonzero drop, that's the signal to open that
table's own script in `pipelines/silver/sql/` and check its `WHERE`
filters and FK joins one at a time — there's no separate per-rule
dashboard the way a Lakeflow pipeline's Data Quality tab gives you, so the
script itself is the source of truth for which rule caught which rows.

Also spot-check a currency normalization landed correctly:

```bash
bq query --use_legacy_sql=false \
  'SELECT order_item_id, unit_price_local, unit_price_usd, line_net_amount_local, line_net_amount_usd
   FROM `clientgcpkraftheinzadpoc.silver.silver_order_items` LIMIT 20'
```

For a USD-currency order, `unit_price_local` and `unit_price_usd` should
be identical (rate = 1.0 exactly, by design). For any other currency,
`unit_price_usd` should be a plausible USD figure, not a wildly-off number
(a common sign of a currency/rate mismatch).

## Report back

Paste (or describe) the `silver_dq_summary` output. If every
`dropped_row_count` is 0, Phase 3 is done and we move to Phase 4 (Gold:
star schema, reporting aggregates, YTD-vs-prior-year logic).
